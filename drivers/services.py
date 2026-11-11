"""Слой бизнес-логики модуля «Водители»: поиск свободных машин, правило БП-01."""

from math import asin, ceil, cos, radians, sin, sqrt

from config.errors import TaxiError

from .models import Driver

# БП-01: заказ возможен только в зоне обслуживания (границы города)
AREA_LAT_MIN, AREA_LAT_MAX = 50.9, 51.4
AREA_LON_MIN, AREA_LON_MAX = 71.1, 71.8

AVG_SPEED_KMH = 30  # средняя скорость подачи, по ней считается eta_min
SEARCH_LIMIT = 5  # сколько ближайших водителей показывать
EARTH_RADIUS_KM = 6371


class InvalidCoordinatesError(TaxiError):
    """БП-01: точка вне зоны обслуживания."""

    http_status = 400
    message = "Координаты вне зоны обслуживания."


def check_coordinates(lat, lon):
    """БП-01: точка должна лежать в зоне обслуживания (границы включены)."""
    in_area = (
        AREA_LAT_MIN <= lat <= AREA_LAT_MAX and AREA_LON_MIN <= lon <= AREA_LON_MAX
    )
    if not in_area:
        raise InvalidCoordinatesError()


def distance_km(lat1, lon1, lat2, lon2):
    """Расстояние между двумя точками (формула гаверсинуса), км."""
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def nearest_free_drivers(lat, lon):
    """Свободные водители, ближайшие первыми: список пар (водитель, км)."""
    pairs = [
        (driver, distance_km(lat, lon, driver.lat, driver.lon))
        for driver in Driver.objects.filter(is_free=True)
    ]
    pairs.sort(key=lambda pair: pair[1])
    return pairs[:SEARCH_LIMIT]


def search_drivers(lat, lon):
    """Шаг 2 UC-01 (операция 2 контракта API): свободные водители рядом."""
    check_coordinates(lat, lon)
    return [
        {
            "driver_id": driver.id,
            "lat": driver.lat,
            "lon": driver.lon,
            "eta_min": max(1, ceil(km / AVG_SPEED_KMH * 60)),
        }
        for driver, km in nearest_free_drivers(lat, lon)
    ]


def occupy(driver):
    """Атомарно занять водителя; False, если его уже занял другой заказ.

    Проверка и занятие — один SQL-запрос (UPDATE ... WHERE is_free), поэтому
    два одновременных заказа не получат одного водителя.
    """
    return Driver.objects.filter(pk=driver.pk, is_free=True).update(is_free=False) == 1


def release(driver_ids):
    """Освободить водителей (заявка истекла, отменена или завершена)."""
    Driver.objects.filter(pk__in=driver_ids).update(is_free=True)
