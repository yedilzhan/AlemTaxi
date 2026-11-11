"""Проверка формата ввода (слой представления). Бизнес-правил здесь нет."""

from django import forms


class SearchForm(forms.Form):
    """Э-02 и GET /api/drivers/search/."""

    lat = forms.FloatField(label="Широта")
    lon = forms.FloatField(label="Долгота")
