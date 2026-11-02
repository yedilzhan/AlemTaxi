from django.urls import path

from . import views

urlpatterns = [
    path("", views.tariffs_page, name="tariffs"),
    path("api/tariffs/", views.api_tariffs, name="api-tariffs"),
]
