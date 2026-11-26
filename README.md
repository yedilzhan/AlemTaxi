# Такси — онлайн-заказ поездки

Наги Едильжан · группа 25-19

Веб-сервис заказа такси: пассажир выбирает тариф, находит свободного водителя,
создаёт заявку, оплачивает и при необходимости отменяет поездку.

Ходячий скелет: экран Э-01 «Тарифы» и операция `GET /api/tariffs/`
отдают данные из заглушки (БД появится в ЛР №7).

## Стек
Python 3.12, Django 5.2 (LTS), SQLite (разработка) / PostgreSQL (эксплуатация).
Обоснование — docs/adr/ADR-001-stack.md

## Как запустить
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata demo
python manage.py runserver
```
(macOS, Linux: вместо `.venv\Scripts\activate` — `source .venv/bin/activate`)

Открыть:
- http://127.0.0.1:8000/ — экран Э-01 «Тарифы»
- http://127.0.0.1:8000/api/tariffs/ — операция API, те же данные в JSON

## Как проверить
```
python manage.py test
ruff check .
```

## Структура
- config/ — настройки проекта (settings.py, urls.py)
- tariffs/ — модуль «Тарифы» (экран Э-01)
  - services.py — бизнес-логика (правило БП-03: расчёт стоимости поездки)
  - views.py — представление (экран и JSON-API)
  - urls.py — маршруты модуля
  - models.py — данные (заполним в ЛР №7)
  - tests.py — тесты
  - templates/tariffs/tariffs.html — шаблон экрана Э-01
- docs/adr/ — архитектурные решения

## Переменные окружения
- DJANGO_DEBUG: «1» (по умолчанию) — режим разработки, «0» — рабочий режим;
- DJANGO_SECRET_KEY: обязателен при DJANGO_DEBUG=0;
- DJANGO_ALLOWED_HOSTS: хосты через запятую.

## Проверки перед слиянием в main
python manage.py test
ruff check .
bandit -r config tariffs drivers rides -x "*/migrations/*,*/test*.py"
pip-audit -r requirements.txt
python tools/trace_check.py docs/traceability.md drivers/services.py rides/services.py tariffs/services.py
python manage.py check --deploy  (с DJANGO_DEBUG=0 и DJANGO_SECRET_KEY)