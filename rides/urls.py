from django.urls import path

from . import views

urlpatterns = [
    path("order/", views.order, name="order"),
    path("rides/<int:pk>/", views.ride_detail, name="ride-detail"),
    path("api/rides/", views.api_create_ride, name="api-rides"),
]
