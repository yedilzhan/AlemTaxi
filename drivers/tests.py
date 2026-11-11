from django.test import SimpleTestCase, TestCase

from . import services
from .models import Driver


def make_driver(plate, lat, lon, is_free=True):
    return Driver.objects.create(
        name="Тест", car="Toyota Camry", plate=plate, lat=lat, lon=lon, is_free=is_free
    )


class CoordinatesRuleTest(SimpleTestCase):
    """БП-01: зона обслуживания, граничные значения."""

    def test_border_allowed_outside_forbidden(self):
        services.check_coordinates(services.AREA_LAT_MAX, services.AREA_LON_MAX)
        services.check_coordinates(services.AREA_LAT_MIN, services.AREA_LON_MIN)
        with self.assertRaises(services.InvalidCoordinatesError):
            services.check_coordinates(
                services.AREA_LAT_MAX + 0.01, services.AREA_LON_MAX
            )
        with self.assertRaises(services.InvalidCoordinatesError):
            services.check_coordinates(
                services.AREA_LAT_MIN, services.AREA_LON_MIN - 0.01
            )


class SearchTest(TestCase):
    """Шаг 2 UC-01: поиск свободных водителей."""

    def test_nearest_driver_first(self):
        far = make_driver("111AAA01", 51.20, 71.50)
        near = make_driver("222BBB01", 51.10, 71.40)
        found = services.search_drivers(51.10, 71.40)
        self.assertEqual([d["driver_id"] for d in found], [near.id, far.id])
        self.assertEqual(found[0]["eta_min"], 1)

    def test_busy_driver_not_found(self):
        make_driver("111AAA01", 51.10, 71.40, is_free=False)
        self.assertEqual(services.search_drivers(51.10, 71.40), [])

    def test_search_outside_area_raises_bp01(self):
        with self.assertRaises(services.InvalidCoordinatesError):
            services.search_drivers(10.0, 10.0)

    def test_occupy_is_atomic_second_attempt_fails(self):
        driver = make_driver("111AAA01", 51.10, 71.40)
        self.assertTrue(services.occupy(driver))
        self.assertFalse(services.occupy(driver))


class SearchViewsTest(TestCase):
    """Экран Э-02 и API: исключения превращаются в коды ответа."""

    def test_api_returns_contract_fields(self):
        make_driver("111AAA01", 51.10, 71.40)
        response = self.client.get("/api/drivers/search/?lat=51.1&lon=71.4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()[0]), {"driver_id", "lat", "lon", "eta_min"}
        )

    def test_api_outside_area_is_400(self):
        """БП-01 → 400."""
        response = self.client.get("/api/drivers/search/?lat=10&lon=10")
        self.assertEqual(response.status_code, 400)

    def test_api_bad_format_is_400(self):
        response = self.client.get("/api/drivers/search/?lat=abc&lon=71.4")
        self.assertEqual(response.status_code, 400)

    def test_screen_shows_drivers(self):
        make_driver("111AAA01", 51.10, 71.40)
        response = self.client.get("/drivers/?lat=51.1&lon=71.4")
        self.assertContains(response, "подъедет через")

    def test_screen_shows_exception_text(self):
        """Особое состояние Э-02: текст исключения БП-01."""
        response = self.client.get("/drivers/?lat=10&lon=10")
        self.assertContains(response, "вне зоны обслуживания")
