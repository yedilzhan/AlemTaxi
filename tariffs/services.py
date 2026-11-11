"""Слой бизнес-логики модуля «Тарифы».

Правила БП живут здесь, а не в представлении.
"""

from .models import Tariff

# Длина поездки для примера расчёта на экране Э-01, км.
EXAMPLE_DISTANCE_KM = 5


def list_tariffs():
    """Операция 1 контракта API: GET /api/tariffs/.

    Возвращает доступные тарифы в формате {id, name, base_price, rate_per_km}.
    """
    return [
        {
            "id": t.id,
            "name": t.name,
            "base_price": t.base_price,
            "rate_per_km": t.rate_per_km,
        }
        for t in Tariff.objects.filter(is_active=True)
    ]


def estimate_price(tariff, distance_km):
    """БП-03: стоимость поездки = подача + цена за км * расстояние.

    Результат округляется до целых тенге.
    """
    if distance_km < 0:
        raise ValueError("Расстояние не может быть отрицательным")
    return round(tariff["base_price"] + tariff["rate_per_km"] * distance_km)


def list_tariffs_with_example(distance_km=EXAMPLE_DISTANCE_KM):
    """Данные для экрана Э-01: тарифы и примерная стоимость поездки."""
    return [
        {**tariff, "example_price": estimate_price(tariff, distance_km)}
        for tariff in list_tariffs()
    ]
