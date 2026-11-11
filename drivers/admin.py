from django.contrib import admin

from .models import Driver


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["name", "car", "plate", "is_free"]
    list_filter = ["is_free"]
