"""Учебная заглушка платёжного шлюза (внешняя система)."""

# Это метка для заглушки шлюза, а не секрет (ложное срабатывание bandit B105).
DECLINED_TOKEN = "tok_declined"  # nosec B105


def charge(payment_token):
    """Списать оплату: True — списано, False — банк отклонил карту."""
    return payment_token != DECLINED_TOKEN
