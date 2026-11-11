from django.urls import path

from . import views

urlpatterns = [
    path("drivers/", views.search_page, name="drivers-search"),
    path("api/drivers/search/", views.api_search, name="api-drivers-search"),
]
