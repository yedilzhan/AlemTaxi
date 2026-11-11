"""Слой представления: принимает запрос, вызывает сервис, отдаёт ответ."""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from config.http import json_response

from . import services


@require_GET
def tariffs_page(request):
    """Э-01 «Тарифы»."""
    return render(
        request,
        "tariffs/tariffs.html",
        {
            "tariffs": services.list_tariffs_with_example(),
            "distance_km": services.EXAMPLE_DISTANCE_KM,
        },
    )


@require_GET
def api_tariffs(request):
    """GET /api/tariffs/ — список тарифов в формате JSON."""
    return json_response(services.list_tariffs())
