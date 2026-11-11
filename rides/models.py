"""Слой данных модуля «Поездки»: сущность Ride."""

from django.db import models

from drivers.models import Driver
from tariffs.models import Tariff


class Ride(models.Model):
    """Заявка на поездку (заказ такси)."""

    class Status(models.TextChoices):
        SEARCHING = "searching", "Поиск"
        PAID = "paid", "Оплачено"
        CANCELLED = "cancelled", "Отменена"
        EXPIRED = "expired", "Сессия истекла"

    ACTIVE = [Status.SEARCHING, Status.PAID]  # статусы активной поездки

    phone = models.CharField("Телефон клиента", max_length=12)
    tariff = models.ForeignKey(
        Tariff, on_delete=models.PROTECT, related_name="rides", verbose_name="Тариф"
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.PROTECT, related_name="rides", verbose_name="Водитель"
    )
    pickup_lat = models.FloatField("Подача: широта")
    pickup_lon = models.FloatField("Подача: долгота")
    dropoff_lat = models.FloatField("Назначение: широта")
    dropoff_lon = models.FloatField("Назначение: долгота")
    status = models.CharField(
        "Статус", max_length=10, choices=Status, default=Status.SEARCHING
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    expires_at = models.DateTimeField("Оплатить до", null=True, blank=True)

    class Meta:
        verbose_name = "поездка"
        verbose_name_plural = "поездки"
        ordering = ["-created_at"]
        constraints = [
            # БП-04: у клиента не больше одной активной поездки (на уровне СУБД)
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(status__in=["searching", "paid"]),
                name="one_active_ride_per_client",
            )
        ]

    def __str__(self):
        return f"Поездка №{self.pk} · {self.phone} · {self.get_status_display()}"
