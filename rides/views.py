"""Слой представления модуля «Поездки»: экраны Э-03, Э-04 и API заказа."""

import json

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from config.errors import TaxiError
from config.http import form_errors, json_response

from . import services
from .forms import RideForm
from .models import Ride


def order(request):
    """Э-03 «Заказ поездки»."""
    form = RideForm(request.POST or None, initial=request.GET.dict())
    if form.is_valid():
        try:
            ride = services.create_ride(**form.cleaned_data)
            return redirect("ride-detail", pk=ride.pk)
        except TaxiError as e:
            form.add_error(None, str(e))  # особое состояние экрана
    return render(request, "rides/order.html", {"form": form})


def ride_detail(request, pk):
    """Э-04 (начало): заявка создана, оплата — в следующей итерации."""
    ride = get_object_or_404(Ride, pk=pk)
    return render(request, "rides/detail.html", {"ride": ride})


@csrf_exempt  # учебное упрощение: защиту API добавим вместе со входом (accounts)
@require_POST
def api_create_ride(request):
    """POST /api/rides/ — шаг 3 UC-01."""
    try:
        data = json.loads(request.body)
    except ValueError:
        return json_response({"error": "Тело запроса — не JSON."}, 400)
    if not isinstance(data, dict):
        return json_response({"error": "Ожидается JSON-объект."}, 400)
    data["tariff"] = data.pop("tariff_id", None)  # имя поля в контракте API
    form = RideForm(data)
    if not form.is_valid():
        return json_response({"errors": form_errors(form)}, 400)
    try:
        ride = services.create_ride(**form.cleaned_data)
    except TaxiError as e:
        return json_response({"error": str(e)}, e.http_status)
    return json_response(
        {
            "ride_id": ride.id,
            "status": ride.get_status_display(),
            "created_at": ride.created_at.isoformat(),
        },
        201,
    )
