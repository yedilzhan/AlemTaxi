from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from drivers.models import Driver
from drivers.services import InvalidCoordinatesError
from tariffs.models import Tariff

from . import services
from .models import Ride

PICKUP = (51.10, 71.40)
DROPOFF = (51.15, 71.45)
PHONE = "+77011234567"
OTHER_PHONE = "+77019999999"


def make_driver(plate="222BBB01"):
    return Driver.objects.create(
        name="Данияр", car="Hyundai Sonata", plate=plate, lat=51.11, lon=71.41
    )


def make_ride(tariff, driver, phone):
    return Ride.objects.create(
        phone=phone,
        tariff=tariff,
        driver=driver,
        pickup_lat=PICKUP[0],
        pickup_lon=PICKUP[1],
        dropoff_lat=DROPOFF[0],
        dropoff_lon=DROPOFF[1],
    )


class RideTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tariff = Tariff.objects.create(
            name="Эконом", base_price=500, rate_per_km=120
        )
        cls.driver = Driver.objects.create(
            name="Ерлан", car="Toyota Camry", plate="123ABC01", lat=51.10, lon=71.40
        )


class CreateRideTest(RideTestCase):
    """Автономное тестирование слоя логики: правила UC-01 без браузера."""

    def order(self, phone=PHONE, pickup=PICKUP):
        return services.create_ride(self.tariff, phone, *pickup, *DROPOFF)

    def test_main_flow_occupies_driver_for_10_minutes(self):
        """Основной поток, БП-05: заявка создана, водитель занят, срок 10 минут."""
        ride = self.order()
        self.assertEqual(ride.status, Ride.Status.SEARCHING)
        self.assertEqual(ride.driver, self.driver)
        self.driver.refresh_from_db()
        self.assertFalse(self.driver.is_free)
        left = ride.expires_at - timezone.now()
        self.assertAlmostEqual(
            left.total_seconds(), services.SESSION_MINUTES * 60, delta=5
        )

    def test_no_free_drivers(self):
        """Исключение 5а: свободных машин нет → NoFreeDriversError."""
        Driver.objects.update(is_free=False)
        with self.assertRaises(services.NoFreeDriversError):
            self.order()

    def test_second_active_ride_forbidden(self):
        """БП-04, исключение 5б: вторая активная поездка → ActiveRideError."""
        make_driver()
        self.order()
        with self.assertRaises(services.ActiveRideError):
            self.order()

    def test_db_blocks_second_active_ride_of_client(self):
        """БП-04: ограничение СУБД — страховка от гонки двух заказов."""
        make_ride(self.tariff, self.driver, PHONE)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_ride(self.tariff, self.driver, PHONE)

    def test_expired_ride_frees_driver(self):
        """БП-05: через 10 минут без оплаты водитель снова свободен."""
        old = self.order()
        Ride.objects.filter(pk=old.pk).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.order(phone=OTHER_PHONE)  # единственный водитель освободился
        old.refresh_from_db()
        self.assertEqual(old.status, Ride.Status.EXPIRED)

    def test_pickup_outside_area_creates_nothing(self):
        """БП-01: точка подачи вне зоны → InvalidCoordinatesError, заказа нет."""
        with self.assertRaises(InvalidCoordinatesError):
            self.order(pickup=(10.0, 10.0))
        self.assertEqual(Ride.objects.count(), 0)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.is_free)


class RideViewsTest(RideTestCase):
    """HTTP: исключения UC-01 превращаются в коды ответа API и тексты на экране."""

    def post_api(self, phone=PHONE, **extra):
        data = {
            "tariff_id": self.tariff.pk,
            "pickup_lat": PICKUP[0],
            "pickup_lon": PICKUP[1],
            "dropoff_lat": DROPOFF[0],
            "dropoff_lon": DROPOFF[1],
            "phone": phone,
            **extra,
        }
        return self.client.post(
            "/api/rides/", data, content_type="application/json"
        )

    def test_api_create_ride_201(self):
        response = self.post_api()
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "Поиск")
        self.assertIn("ride_id", body)

    def test_api_no_free_cars_409(self):
        """5а → 409."""
        self.assertEqual(self.post_api().status_code, 201)
        response = self.post_api(phone=OTHER_PHONE)
        self.assertEqual(response.status_code, 409)
        self.assertIn("машин нет", response.json()["error"])

    def test_api_second_active_ride_422(self):
        """БП-04 → 422."""
        make_driver()
        self.post_api()
        self.assertEqual(self.post_api().status_code, 422)

    def test_api_bad_coordinates_400(self):
        """БП-01 → 400."""
        self.assertEqual(self.post_api(pickup_lat=10).status_code, 400)

    def test_api_bad_phone_400(self):
        """Формат телефона проверяет форма → 400."""
        self.assertEqual(self.post_api(phone="8701").status_code, 400)

    def test_screen_creates_ride_and_opens_detail(self):
        """Э-03 → Э-04: после заказа открывается страница поездки."""
        response = self.client.post(
            "/order/",
            {
                "tariff": self.tariff.pk,
                "pickup_lat": PICKUP[0],
                "pickup_lon": PICKUP[1],
                "dropoff_lat": DROPOFF[0],
                "dropoff_lon": DROPOFF[1],
                "phone": PHONE,
            },
            follow=True,
        )
        self.assertContains(response, "Поиск")
        self.assertContains(response, "Ерлан")

    def test_screen_shows_exception_text(self):
        """Особое состояние Э-03: текст исключения 5а."""
        Driver.objects.update(is_free=False)
        response = self.client.post(
            "/order/",
            {
                "tariff": self.tariff.pk,
                "pickup_lat": PICKUP[0],
                "pickup_lon": PICKUP[1],
                "dropoff_lat": DROPOFF[0],
                "dropoff_lon": DROPOFF[1],
                "phone": PHONE,
            },
        )
        self.assertContains(response, "Свободных машин нет")
