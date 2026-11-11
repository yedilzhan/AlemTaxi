from django.contrib import admin

from .models import Tariff


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = ["name", "base_price", "rate_per_km", "is_active"]
