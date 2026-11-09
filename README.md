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

Ссылка на репозиторий: <вставьте ссылку после git push>
