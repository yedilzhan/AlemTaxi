from django.test import SimpleTestCase, TestCase

from . import services
from .models import Tariff

ECONOMY = {"id": 1, "name": "Эконом", "base_price": 500, "rate_per_km": 120}


class EstimatePriceTests(SimpleTestCase):
    """Бизнес-правило БП-03: расчёт стоимости поездки."""

    def test_price_is_base_plus_rate_per_km(self):
        self.assertEqual(services.estimate_price(ECONOMY, 5), 1100)

    def test_zero_distance_costs_base_price(self):
        self.assertEqual(services.estimate_price(ECONOMY, 0), 500)

    def test_negative_distance_is_rejected(self):
        with self.assertRaises(ValueError):
            services.estimate_price(ECONOMY, -1)


class ScreenTests(TestCase):
    """Экран Э-01 и операция API GET /api/tariffs/ (данные из БД)."""

    @classmethod
    def setUpTestData(cls):
        Tariff.objects.create(name="Эконом", base_price=500, rate_per_km=120)
        Tariff.objects.create(name="Комфорт", base_price=700, rate_per_km=160)
        Tariff.objects.create(name="Бизнес", base_price=1200, rate_per_km=250)
        Tariff.objects.create(
            name="Архивный", base_price=1, rate_per_km=1, is_active=False
        )

    def test_screen_opens_and_shows_tariffs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Эконом")
        self.assertContains(response, "1100")  # пример для 5 км по тарифу «Эконом»
        self.assertNotContains(response, "Архивный")

    def test_api_returns_only_active_tariffs_from_contract(self):
        response = self.client.get("/api/tariffs/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(set(data[0]), {"id", "name", "base_price", "rate_per_km"})
