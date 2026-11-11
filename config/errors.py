"""Базовый класс исключений сценария UC-01 (слой логики)."""


class TaxiError(Exception):
    """Запланированный исход сценария.

    Наследники задают код ответа API и текст для экрана; представление
    ловит один TaxiError и берёт http_status (полиморфизм).
    """

    http_status = 400
    message = "Операция невозможна."

    def __init__(self, message=None):
        super().__init__(message or self.message)
