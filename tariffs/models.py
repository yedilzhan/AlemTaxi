"""Слой данных модуля «Тарифы»: сущность Tariff из словаря данных."""

from django.db import models


class Tariff(models.Model):
    """Тариф: цена подачи и цена за километр."""

    name = models.CharField("Название", max_length=50, unique=True)
    base_price = models.PositiveIntegerField("Подача, тг")
    rate_per_km = models.PositiveIntegerField("Цена за км, тг")
    is_active = models.BooleanField("Доступен для заказа", default=True)

    class Meta:
        verbose_name = "тариф"
        verbose_name_plural = "тарифы"
        ordering = ["id"]

    def __str__(self):
        return self.name
