# ЛР №7 — таблицы для отчёта (UC-01 «Заказ такси»)

## Задание 1. Модели

| Сущность словаря | Модель (модуль) | Поля и типы | Связи и ограничения |
|---|---|---|---|
| Тариф | `Tariff` (tariffs) | name `CharField(50)`, base_price, rate_per_km `PositiveIntegerField`, is_active `BooleanField` | `name` unique |
| Водитель | `Driver` (drivers) | name, car `CharField`, plate `CharField(10)`, lat, lon `FloatField`, is_free `BooleanField` | `plate` unique |
| Поездка | `Ride` (rides) | phone `CharField(12)`, pickup_lat/lon, dropoff_lat/lon `FloatField`, status `choices`, created_at, expires_at `DateTimeField` | FK → `Tariff`, FK → `Driver` (PROTECT); `UniqueConstraint(phone)` для активных статусов — БП-04 |

Клиент в этой итерации определяется телефоном (как в образце); сущность `Client` и модуль accounts — со входом по SMS.

## Задание 2. Таблица трассировки

| Правило / исключение | Функция | Класс исключения | Код API | Тест |
|---|---|---|---|---|
| БП-01: точка в зоне обслуживания | `drivers.check_coordinates()` (из `search_drivers()` и `create_ride()`) | `InvalidCoordinatesError` | 400 | `test_border_allowed_outside_forbidden`, `test_pickup_outside_area_creates_nothing`, `test_api_bad_coordinates_400` |
| БП-04, исключение 5б: не больше одной активной поездки | `create_ride()` + ограничение СУБД | `ActiveRideError` | 422 | `test_second_active_ride_forbidden`, `test_db_blocks_second_active_ride_of_client`, `test_api_second_active_ride_422` |
| Исключение 5а: свободных машин нет | `create_ride()` → `occupy_nearest_driver()` | `NoFreeDriversError` | 409 | `test_no_free_drivers`, `test_api_no_free_cars_409` |
| БП-05: заявка ждёт оплаты 10 минут | `create_ride()`, `expire_rides()` | — (код 410 при оплате — в следующей итерации) | — | `test_main_flow_occupies_driver_for_10_minutes`, `test_expired_ride_frees_driver` |

Иерархия: `TaxiError` (config/errors.py, `http_status`, `message`) → `InvalidCoordinatesError`, `NoFreeDriversError`, `ActiveRideError`.

**Защита от гонки.** Ресурс, который могут занять двое, — водитель. `drivers.occupy()` проверяет и занимает его одним SQL-запросом `UPDATE ... WHERE is_free`: второй одновременный заказ получит 0 изменённых строк и перейдёт к следующему водителю или бросит `NoFreeDriversError`. Заказ целиком выполняется в `transaction.atomic()`. Двойной заказ одного клиента ловит `UniqueConstraint` (БП-04): `IntegrityError` превращается в `ActiveRideError`.

**Изменения контракта API (строка 3, `POST /api/rides/`).** Добавлены `pickup_lon`, `dropoff_lon` (без долготы точка не определена) и `phone` (клиент определяется телефоном до появления входа).

## Задание 3. Ручная проверка

| № | Действие | Ожидаемый результат | Фактический результат |
|---|---|---|---|
| 1 | Э-02 `/drivers/`: широта 51.1, долгота 71.4 | Список свободных водителей, ближайший первым, есть время подачи | |
| 2 | Э-01 → «Заказать» у «Эконом» → Э-03: подача 51.1 / 71.4, назначение 51.15 / 71.45, телефон +77011234567 | Страница поездки «Поиск», водитель закреплён, видно «оплатить до чч:мм» | |
| 3 | Э-03: те же данные с тем же телефоном | «У вас уже есть активная поездка» (БП-04) | |
| 4 | Э-02: широта 10, долгота 10 | «Координаты вне зоны обслуживания» (БП-01) | |
| 5 | В админ-панели снять «Свободен» у всех водителей; Э-03 с новым телефоном +77019999999 | «Свободных машин нет» (5а) | |
