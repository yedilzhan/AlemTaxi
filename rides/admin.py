from django.contrib import admin

from .models import Ride


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ["id", "phone", "tariff", "driver", "status", "expires_at"]
    list_filter = ["status", "tariff"]
