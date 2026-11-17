"""Интеграция «сверху вниз»: слой представления проверяется с заглушкой слоя логики."""

from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from config.errors import TaxiError
from drivers.models import Driver
from drivers.services import InvalidCoordinatesError
from tariffs.models import Tariff

from . import services
from .models import Ride

# Коды ответа из контракта API (ЛР №6): исключение → HTTP-код
CONTRACT_CODES = {
    InvalidCoordinatesError: 400,
    services.NoFreeDriversError: 409,
    services.ActiveRideError: 422,
    services.InvalidStatusError: 409,
    services.CancelNotAllowedError: 409,
    services.SessionExpiredError: 410,
    services.PaymentDeclinedError: 402,
}


def all_subclasses(cls):
    found = set()
    for sub in cls.__subclasses__():
        found.add(sub)
        found |= all_subclasses(sub)
    return found


class RideViewStubTest(TestCase):
    """POST /api/rides/ и /pay/ без настоящих create_ride() и pay()."""

    @classmethod
    def setUpTestData(cls):
        cls.tariff = Tariff.objects.create(
            name="Эконом", base_price=500, rate_per_km=120
        )
        driver = Driver.objects.create(
            name="Ерлан", car="Toyota Camry", plate="123ABC01", lat=51.10, lon=71.40
        )
        cls.ride = Ride.objects.create(
            phone="+77011234567",
            tariff=cls.tariff,
            driver=driver,
            pickup_lat=51.10,
            pickup_lon=71.40,
            dropoff_lat=51.15,
            dropoff_lon=71.45,
        )

    def post(self, path="/api/rides/", **extra):
        data = {
            "tariff_id": self.tariff.pk,
            "pickup_lat": 51.10,
            "pickup_lon": 71.40,
            "dropoff_lat": 51.15,
            "dropoff_lon": 71.45,
            "phone": "+77011234567",
            **extra,
        }
        return self.client.post(path, data, content_type="application/json")

    def test_every_taxi_error_becomes_its_contract_code(self):
        """Полиморфизм: каждое исключение UC-01 → свой код из контракта."""
        self.assertEqual(all_subclasses(TaxiError), set(CONTRACT_CODES))
        for error, code in CONTRACT_CODES.items():
            with self.subTest(error=error.__name__):
                with patch("rides.views.services.create_ride", side_effect=error()):
                    response = self.post()
                self.assertEqual(response.status_code, code)
                self.assertEqual(response.json()["error"], error.message)

    def test_view_passes_cleaned_data_to_service(self):
        """Представление вызывает create_ride() один раз, с объектами, а не строками."""
        fake = Mock(id=7, created_at=timezone.now())
        fake.get_status_display.return_value = "Поиск"
        with patch("rides.views.services.create_ride", return_value=fake) as stub:
            response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["ride_id"], 7)
        stub.assert_called_once()
        self.assertEqual(stub.call_args.kwargs["tariff"], self.tariff)
        self.assertEqual(stub.call_args.kwargs["phone"], "+77011234567")

    def test_bad_format_never_reaches_service(self):
        """Формат проверяет форма: при неверном вводе слой логики не вызывается."""
        with patch("rides.views.services.create_ride") as stub:
            not_json = self.client.post(
                "/api/rides/", "not json", content_type="application/json"
            )
            bad_phone = self.post(phone="8701")
        self.assertEqual(not_json.status_code, 400)
        self.assertEqual(bad_phone.status_code, 400)
        stub.assert_not_called()

    def test_pay_view_passes_token_and_maps_error(self):
        """POST /api/rides/{id}/pay/: токен доходит до pay(), ошибка → 402."""
        path = f"/api/rides/{self.ride.pk}/pay/"
        error = services.PaymentDeclinedError()
        with patch("rides.views.services.pay", side_effect=error) as stub:
            response = self.post(path, payment_token="tok_123")
        self.assertEqual(response.status_code, 402)
        stub.assert_called_once()
        self.assertEqual(stub.call_args.args[1], "tok_123")
