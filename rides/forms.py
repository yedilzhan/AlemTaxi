"""Проверка формата ввода (слой представления). Бизнес-правил здесь нет."""

from django import forms

from tariffs.models import Tariff


class RideForm(forms.Form):
    """Э-03 и POST /api/rides/."""

    tariff = forms.ModelChoiceField(
        Tariff.objects.filter(is_active=True), label="Тариф"
    )
    pickup_lat = forms.FloatField(label="Подача: широта")
    pickup_lon = forms.FloatField(label="Подача: долгота")
    dropoff_lat = forms.FloatField(label="Назначение: широта")
    dropoff_lon = forms.FloatField(label="Назначение: долгота")
    phone = forms.RegexField(
        r"^\+7\d{10}$",
        label="Телефон",
        error_messages={"invalid": "Введите номер в формате +77011234567."},
    )
