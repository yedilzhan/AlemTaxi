"""Корневые маршруты проекта: админ-панель и подключение модулей."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tariffs.urls")),
]
