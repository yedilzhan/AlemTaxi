"""Общие помощники слоя представления."""

from django.http import JsonResponse


def json_response(data, status=200):
    """JSON-ответ: русские буквы без экранирования."""
    return JsonResponse(
        data, status=status, safe=False, json_dumps_params={"ensure_ascii": False}
    )


def form_errors(form):
    """Ошибки формы в виде {поле: [сообщения]}."""
    return {field: list(errors) for field, errors in form.errors.items()}
