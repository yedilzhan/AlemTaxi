"""Слой бизнес-логики модуля «Поездки»: шаги UC-01, правила БП-01, БП-02, БП-04, БП-05."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from config.errors import TaxiError
from drivers import services as driver_services

from . import gateway
from .models import Ride

SESSION_MINUTES = 10  # БП-05: заявка ждёт оплаты 10 минут

# Разрешённые переходы статусов поездки. Из «Оплачено» выхода нет: водитель уже
# в пути (БП-02); завершение поездки — следующая итерация.
TRANSITIONS = {
    Ride.Status.SEARCHING: {
        Ride.Status.PAID,
        Ride.Status.CANCELLED,
        Ride.Status.EXPIRED,
    },
}


class NoFreeDriversError(TaxiError):
    """Исключение 5а: свободных машин нет."""

    http_status = 409
    message = "Свободных машин нет. Попробуйте позже."


class ActiveRideError(TaxiError):
    """Исключение 5б, БП-04: у клиента уже есть активная поездка."""

    http_status = 422
    message = "У вас уже есть активная поездка."


class InvalidStatusError(TaxiError):
    """Действие недоступно в текущем статусе поездки."""

    http_status = 409
    message = "Это действие недоступно для поездки в текущем статусе."


class CancelNotAllowedError(TaxiError):
    """БП-02: после оплаты водитель уже в пути, отмена невозможна."""

    http_status = 409
    message = "Поездку уже нельзя отменить: водитель в пути."


class SessionExpiredError(TaxiError):
    """БП-05: время на оплату вышло."""

    http_status = 410
    message = "Время сессии истекло. Закажите поездку заново."


class PaymentDeclinedError(TaxiError):
    """Исключение 7а: банк отклонил карту."""

    http_status = 402
    message = "Банк отклонил карту. Попробуйте другую."


def expire_rides():
    """БП-05: неоплаченные заявки через 10 минут истекают, водитель освобождается."""
    stale = list(
        Ride.objects.filter(
            status=Ride.Status.SEARCHING, expires_at__lt=timezone.now()
        ).values_list("pk", "driver_id")
    )
    if stale:
        Ride.objects.filter(pk__in=[pk for pk, _ in stale]).update(
            status=Ride.Status.EXPIRED
        )
        driver_services.release([driver_id for _, driver_id in stale])


def occupy_nearest_driver(lat, lon):
    """Закрепить ближайшего свободного водителя; иначе — исключение 5а."""
    for driver, _km in driver_services.nearest_free_drivers(lat, lon):
        if driver_services.occupy(driver):
            return driver
    raise NoFreeDriversError()


def create_ride(tariff, phone, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon):
    """Шаг 3 UC-01: создать заявку и закрепить ближайшего водителя."""
    driver_services.check_coordinates(pickup_lat, pickup_lon)  # БП-01
    driver_services.check_coordinates(dropoff_lat, dropoff_lon)  # БП-01
    try:
        with transaction.atomic():
            expire_rides()  # БП-05
            if Ride.objects.filter(phone=phone, status__in=Ride.ACTIVE).exists():
                raise ActiveRideError()  # БП-04
            driver = occupy_nearest_driver(pickup_lat, pickup_lon)  # 5а
            return Ride.objects.create(
                phone=phone,
                tariff=tariff,
                driver=driver,
                pickup_lat=pickup_lat,
                pickup_lon=pickup_lon,
                dropoff_lat=dropoff_lat,
                dropoff_lon=dropoff_lon,
                expires_at=timezone.now() + timedelta(minutes=SESSION_MINUTES),
            )
    except IntegrityError:  # гонка: сработало ограничение СУБД (БП-04)
        raise ActiveRideError() from None


def _can_move(ride, new_status):
    """Разрешён ли переход из текущего статуса поездки в new_status."""
    return new_status in TRANSITIONS.get(ride.status, set())


def _move(ride, new_status):
    """Перевести поездку в новый статус, если переход разрешён."""
    if not _can_move(ride, new_status):
        raise InvalidStatusError()
    ride.status = new_status
    ride.save(update_fields=["status"])


def pay(ride, payment_token):
    """Шаг 7 UC-01 (операция 4 контракта API): оплата поездки."""
    expire_rides()
    ride.refresh_from_db()
    if ride.status == Ride.Status.EXPIRED:
        raise SessionExpiredError()  # БП-05
    if not _can_move(ride, Ride.Status.PAID):
        raise InvalidStatusError()  # проверка до списания денег
    if not gateway.charge(payment_token):
        raise PaymentDeclinedError()  # исключение 7а
    _move(ride, Ride.Status.PAID)
    return ride


def cancel(ride):
    """Операция 5 контракта API: отмена поездки, водитель освобождается."""
    expire_rides()
    ride.refresh_from_db()
    if ride.status == Ride.Status.PAID:
        raise CancelNotAllowedError()  # БП-02: водитель уже в пути
    with transaction.atomic():
        _move(ride, Ride.Status.CANCELLED)
        driver_services.release([ride.driver_id])
    return ride
