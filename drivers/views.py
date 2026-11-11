"""Слой представления модуля «Водители»: экран Э-02 и API поиска."""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from config.errors import TaxiError
from config.http import form_errors, json_response

from . import services
from .forms import SearchForm


@require_GET
def search_page(request):
    """Э-02 «Водители рядом»."""
    form = SearchForm(request.GET or None)
    found = []
    if form.is_valid():
        try:
            found = services.search_drivers(**form.cleaned_data)
        except TaxiError as e:
            form.add_error(None, str(e))  # особое состояние экрана
    return render(request, "drivers/search.html", {"form": form, "drivers": found})


@require_GET
def api_search(request):
    """GET /api/drivers/search/?lat=51.1&lon=71.4"""
    form = SearchForm(request.GET)
    if not form.is_valid():
        return json_response({"errors": form_errors(form)}, 400)
    try:
        found = services.search_drivers(**form.cleaned_data)
    except TaxiError as e:
        return json_response({"error": str(e)}, e.http_status)
    return json_response(found)
