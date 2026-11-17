"""Слой представления модуля «Поездки»: экраны Э-03, Э-04 и API заказа, оплаты, отмены."""

import json

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from config.errors import TaxiError
from config.http import form_errors, json_response

from . import services
from .forms import PaymentForm, RideForm
from .models import Ride


def _json_object(request):
    """Тело запроса как JSON-объект; None, если это не JSON-объект."""
    try:
        data = json.loads(request.body)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


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
    """Э-04: страница поездки."""
    ride = get_object_or_404(Ride, pk=pk)
    return render(request, "rides/detail.html", {"ride": ride})


@csrf_exempt  # учебное упрощение: защиту API добавим вместе со входом (accounts)
@require_POST
def api_create_ride(request):
    """POST /api/rides/ — шаг 3 UC-01."""
    data = _json_object(request)
    if data is None:
        return json_response({"error": "Тело запроса должно быть JSON-объектом."}, 400)
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


@csrf_exempt
@require_POST
def api_pay(request, pk):
    """POST /api/rides/{id}/pay/ — шаг 7 UC-01."""
    ride = get_object_or_404(Ride, pk=pk)
    data = _json_object(request)
    if data is None:
        return json_response({"error": "Тело запроса должно быть JSON-объектом."}, 400)
    form = PaymentForm(data)
    if not form.is_valid():
        return json_response({"errors": form_errors(form)}, 400)
    try:
        ride = services.pay(ride, form.cleaned_data["payment_token"])
    except TaxiError as e:
        return json_response({"error": str(e)}, e.http_status)
    # receipt_url — учебная заглушка: страницы чека пока нет
    return json_response(
        {"status": ride.get_status_display(), "receipt_url": f"/receipts/{ride.pk}/"}
    )


@csrf_exempt
@require_POST
def api_cancel(request, pk):
    """POST /api/rides/{id}/cancel/ — отмена поездки."""
    ride = get_object_or_404(Ride, pk=pk)
    try:
        ride = services.cancel(ride)
    except TaxiError as e:
        return json_response({"error": str(e)}, e.http_status)
    return json_response({"status": ride.get_status_display(), "fee": 0})
