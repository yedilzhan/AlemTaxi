"""Тесты «чёрного ящика» для UC-01: построены по требованиям (БП, контракт API)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase

from drivers.models import Driver
from drivers.services import InvalidCoordinatesError
from tariffs.models import Tariff

from . import services
from .models import Ride

# «Сейчас» для всех тестов: вторник 10.11.2026, 12:30 (UTC)
NOW = datetime(2026, 11, 10, 12, 30, tzinfo=UTC)
PICKUP = (51.10, 71.40)
DROPOFF = (51.15, 71.45)
PHONE = "+77011234567"


def make_ride(tariff, driver, status, phone=PHONE):
    return Ride.objects.create(
        phone=phone,
        tariff=tariff,
        driver=driver,
        pickup_lat=PICKUP[0],
        pickup_lon=PICKUP[1],
        dropoff_lat=DROPOFF[0],
        dropoff_lon=DROPOFF[1],
        status=status,
    )


class FrozenTimeTestCase(TestCase):
    """Базовый класс: подменяет текущее время заглушкой, данные — общие."""

    @classmethod
    def setUpTestData(cls):
        cls.tariff = Tariff.objects.create(
            name="Эконом", base_price=500, rate_per_km=120
        )
        cls.driver = Driver.objects.create(
            name="Ерлан", car="Toyota Camry", plate="123ABC01", lat=51.10, lon=71.40
        )

    def setUp(self):
        patcher = self.clock(NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def clock(self, moment):
        """Заглушка часов: timezone.now() вернёт moment."""
        return patch("django.utils.timezone.now", return_value=moment)

    def order(self, phone=PHONE, pickup=PICKUP, dropoff=DROPOFF):
        return services.create_ride(self.tariff, phone, *pickup, *dropoff)

    def reset(self):
        """Очистить поездки и освободить водителей между подтестами."""
        Ride.objects.all().delete()
        Driver.objects.update(is_free=True)


class ZoneRuleTest(FrozenTimeTestCase):
    """БП-01: зона обслуживания — широта 50.9…51.4, долгота 71.1…71.8."""

    def test_zone_borders_allowed(self):
        """Допустимый класс: углы зоны и центр, границы включены."""
        for lat, lon in [(50.9, 71.1), (51.4, 71.8), (51.1, 71.4)]:
            with self.subTest(lat=lat, lon=lon):
                self.reset()
                ride = self.order(pickup=(lat, lon))
                self.assertEqual(ride.status, Ride.Status.SEARCHING)

    def test_outside_zone_forbidden_on_each_border(self):
        """Недопустимые классы: шаг за каждую из четырёх границ (части условия)."""
        for lat, lon in [(51.41, 71.4), (50.89, 71.4), (51.1, 71.81), (51.1, 71.09)]:
            with (
                self.subTest(lat=lat, lon=lon),
                self.assertRaises(InvalidCoordinatesError),
            ):
                self.order(pickup=(lat, lon))

    def test_dropoff_outside_zone_forbidden(self):
        """БП-01: точка назначения проверяется так же, как точка подачи."""
        with self.assertRaises(InvalidCoordinatesError):
            self.order(dropoff=(51.41, 71.4))


class ActiveRideLimitTest(FrozenTimeTestCase):
    """БП-04: не больше одной активной поездки у клиента."""

    def test_cancelled_and_expired_do_not_count(self):
        """Неактивные статусы не считаются: отменена, истекла."""
        for status in (Ride.Status.CANCELLED, Ride.Status.EXPIRED):
            with self.subTest(status=status):
                self.reset()
                make_ride(self.tariff, self.driver, status)
                self.assertEqual(self.order().status, Ride.Status.SEARCHING)

    def test_paid_ride_counts_as_active(self):
        """Активные статусы: оплаченная поездка тоже блокирует новый заказ."""
        make_ride(self.tariff, self.driver, Ride.Status.PAID)
        with self.assertRaises(services.ActiveRideError):
            self.order()


class DecisionTableTest(FrozenTimeTestCase):
    """Таблица решений create_ride(): порядок проверок задаёт код ответа."""

    def test_r5_active_ride_checked_before_free_drivers(self):
        """R5: есть активная поездка и нет водителей → 422 (БП-04), а не 409."""
        self.order()  # единственный водитель занят, у клиента активная поездка
        with self.assertRaises(services.ActiveRideError):
            self.order()

    def test_r6_zone_checked_before_active_ride(self):
        """R6: точка вне зоны и активная поездка → 400 (БП-01), а не 422."""
        self.order()
        with self.assertRaises(InvalidCoordinatesError):
            self.order(pickup=(10.0, 10.0))


class PaymentTest(FrozenTimeTestCase):
    """Оплата: БП-05 (время сессии) и исключение 7а (банк отклонил)."""

    def test_pay_success_keeps_driver_busy(self):
        """Переход searching → paid."""
        ride = services.pay(self.order(), "tok_123")
        self.assertEqual(ride.status, Ride.Status.PAID)
        self.driver.refresh_from_db()
        self.assertFalse(self.driver.is_free)

    def test_declined_card_keeps_ride_searching(self):
        """Исключение 7а: отказ банка не меняет статус."""
        ride = self.order()
        with self.assertRaises(services.PaymentDeclinedError):
            services.pay(ride, "tok_declined")
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.SEARCHING)

    def test_pay_exactly_at_session_end_allowed(self):
        """БП-05, граница: ровно через 10 минут оплатить ещё можно."""
        ride = self.order()
        with self.clock(NOW + timedelta(minutes=10)):
            self.assertEqual(services.pay(ride, "tok_123").status, Ride.Status.PAID)

    def test_pay_after_session_end_forbidden(self):
        """БП-05, граница: через 10 мин 1 с → 410, водитель освобождён (expired)."""
        ride = self.order()
        with (
            self.clock(NOW + timedelta(minutes=10, seconds=1)),
            self.assertRaises(services.SessionExpiredError),
        ):
            services.pay(ride, "tok_123")
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.EXPIRED)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.is_free)


class StatusTransitionTest(FrozenTimeTestCase):
    """Переходы состояний: searching → paid / cancelled / expired, остальное — запрет."""

    def test_cancel_searching_ride_frees_driver(self):
        """Переход searching → cancelled."""
        ride = services.cancel(self.order())
        self.assertEqual(ride.status, Ride.Status.CANCELLED)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.is_free)

    def test_pay_twice_forbidden(self):
        """Запрещённый переход paid → paid."""
        ride = services.pay(self.order(), "tok_123")
        with self.assertRaises(services.InvalidStatusError):
            services.pay(ride, "tok_123")

    def test_cancel_paid_ride_forbidden_bp02(self):
        """БП-02, запрещённый переход paid → cancelled: водитель в пути."""
        ride = services.pay(self.order(), "tok_123")
        with self.assertRaises(services.CancelNotAllowedError):
            services.cancel(ride)
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.Status.PAID)

    def test_cancel_twice_forbidden(self):
        """Запрещённый переход cancelled → cancelled."""
        ride = services.cancel(self.order())
        with self.assertRaises(services.InvalidStatusError):
            services.cancel(ride)

    def test_pay_after_cancel_forbidden_and_no_charge(self):
        """Запрещённый переход cancelled → paid: деньги не списываются."""
        ride = services.cancel(self.order())
        with (
            patch("rides.services.gateway.charge") as charge,
            self.assertRaises(services.InvalidStatusError),
        ):
            services.pay(ride, "tok_123")
        charge.assert_not_called()


class ApiBlackBoxTest(FrozenTimeTestCase):
    """Контракт API: коды ответов по классам и переходам."""

    def post(self, path, data):
        return self.client.post(path, data, content_type="application/json")

    def order_payload(self, **extra):
        return {
            "tariff_id": self.tariff.pk,
            "pickup_lat": PICKUP[0],
            "pickup_lon": PICKUP[1],
            "dropoff_lat": DROPOFF[0],
            "dropoff_lon": DROPOFF[1],
            "phone": PHONE,
            **extra,
        }

    def create_ride_id(self):
        return self.post("/api/rides/", self.order_payload()).json()["ride_id"]

    def test_phone_format_classes(self):
        """Формат телефона: короче, длиннее, через 8, с буквой, пустой → 400."""
        for phone in ("+7701123456", "+770112345678", "87011234567", "+7701123456a", ""):
            with self.subTest(phone=phone):
                response = self.post("/api/rides/", self.order_payload(phone=phone))
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.post("/api/rides/", self.order_payload()).status_code, 201)

    def test_pay_then_repeat_then_cancel_codes(self):
        """Контракт: 402 (отказ банка) → 200 → 409 (повторная оплата) → 409 (БП-02)."""
        pay = f"/api/rides/{self.create_ride_id()}/pay/"
        self.assertEqual(self.post(pay, {"payment_token": "tok_declined"}).status_code, 402)
        paid = self.post(pay, {"payment_token": "tok_123"})
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.json()["status"], "Оплачено")
        self.assertEqual(self.post(pay, {"payment_token": "tok_123"}).status_code, 409)
        cancel = pay.replace("/pay/", "/cancel/")
        self.assertEqual(self.post(cancel, {}).status_code, 409)

    def test_cancel_returns_status_and_zero_fee(self):
        """Операция 5: 200 {status: «Отменена», fee: 0}."""
        response = self.post(f"/api/rides/{self.create_ride_id()}/cancel/", {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "Отменена", "fee": 0})

    def test_pay_without_token_is_400(self):
        """Формат: токен оплаты обязателен."""
        response = self.post(f"/api/rides/{self.create_ride_id()}/pay/", {})
        self.assertEqual(response.status_code, 400)

    def test_pay_after_session_end_is_410(self):
        """БП-05 через HTTP: после 10 минут оплата → 410."""
        pay = f"/api/rides/{self.create_ride_id()}/pay/"
        with self.clock(NOW + timedelta(minutes=11)):
            response = self.post(pay, {"payment_token": "tok_123"})
        self.assertEqual(response.status_code, 410)

    def test_search_shows_driver_after_session_end(self):
        """Д-4, БП-05: заявка истекла → водитель снова виден в поиске."""
        self.order()
        with self.clock(NOW + timedelta(minutes=11)):
            response = self.client.get("/api/drivers/search/?lat=51.1&lon=71.4")
        self.assertEqual(len(response.json()), 1)
