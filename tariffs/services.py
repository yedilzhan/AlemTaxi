"""Слой бизнес-логики модуля «Тарифы».

Правила БП живут здесь, а не в представлении.
"""

# Заглушка вместо базы данных. В ЛР №7 заменим на запрос к модели Tariff.
TARIFFS = [
    {"id": 1, "name": "Эконом", "base_price": 500, "rate_per_km": 120},
    {"id": 2, "name": "Комфорт", "base_price": 700, "rate_per_km": 160},
    {"id": 3, "name": "Бизнес", "base_price": 1200, "rate_per_km": 250},
]

# Длина поездки для примера расчёта на экране Э-01, км.
EXAMPLE_DISTANCE_KM = 5


def list_tariffs():
    """Операция 1 контракта API: GET /api/tariffs/.

    Возвращает список тарифов в формате {id, name, base_price, rate_per_km}.
    """
    return [dict(tariff) for tariff in TARIFFS]


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
