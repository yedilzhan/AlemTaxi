"""Тесты «белого ящика»: ветви create_ride(), которые трудно вызвать через данные."""

from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from drivers.models import Driver
from tariffs.models import Tariff

from . import services
from .models import Ride

PICKUP = (51.10, 71.40)
DROPOFF = (51.15, 71.45)
PHONE = "+77011234567"


class CreateRideBranchTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tariff = Tariff.objects.create(
            name="Эконом", base_price=500, rate_per_km=120
        )
        cls.driver = Driver.objects.create(
            name="Ерлан", car="Toyota Camry", plate="123ABC01", lat=51.10, lon=71.40
        )

    def test_integrity_error_becomes_active_ride_error(self):
        """Путь П5: гонка двух заказов — IntegrityError → ActiveRideError, откат."""
        with patch.object(Ride.objects, "create", side_effect=IntegrityError):
            with self.assertRaises(services.ActiveRideError):
                services.create_ride(self.tariff, PHONE, *PICKUP, *DROPOFF)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.is_free)  # занятие водителя откатилось

    def test_next_driver_taken_when_first_one_is_grabbed(self):
        """Цикл occupy_nearest_driver(): первого водителя перехватил другой заказ."""
        second = Driver.objects.create(
            name="Данияр", car="Hyundai Sonata", plate="456DEF01", lat=51.12, lon=71.42
        )
        with patch("rides.services.driver_services.occupy", side_effect=[False, True]):
            ride = services.create_ride(self.tariff, PHONE, *PICKUP, *DROPOFF)
        self.assertEqual(ride.driver, second)
