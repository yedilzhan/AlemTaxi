"""Учебная заглушка платёжного шлюза (внешняя система)."""

DECLINED_TOKEN = "tok_declined"  # токен, который «банк» всегда отклоняет


def charge(payment_token):
    """Списать оплату: True — списано, False — банк отклонил карту."""
    return payment_token != DECLINED_TOKEN
