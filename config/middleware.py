"""Ленивое истечение заявок (БП-05): перед каждым запросом."""

from rides import services


class ExpireRidesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        services.expire_rides()
        return self.get_response(request)