"""Слой данных модуля «Водители»: сущность Driver из словаря данных."""

from django.db import models


class Driver(models.Model):
    """Водитель с автомобилем и текущей позицией."""

    name = models.CharField("Имя", max_length=100)
    car = models.CharField("Автомобиль", max_length=60)
    plate = models.CharField("Госномер", max_length=10, unique=True)
    lat = models.FloatField("Широта")
    lon = models.FloatField("Долгота")
    is_free = models.BooleanField("Свободен", default=True)

    class Meta:
        verbose_name = "водитель"
        verbose_name_plural = "водители"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} · {self.car} · {self.plate}"
