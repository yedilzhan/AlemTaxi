from django.urls import path

from . import views

urlpatterns = [
    path("order/", views.order, name="order"),
    path("rides/<int:pk>/", views.ride_detail, name="ride-detail"),
    path("api/rides/", views.api_create_ride, name="api-rides"),
    path("api/rides/<int:pk>/pay/", views.api_pay, name="api-ride-pay"),
    path("api/rides/<int:pk>/cancel/", views.api_cancel, name="api-ride-cancel"),
]
