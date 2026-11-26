# Таблица трассировки UC-01 «Заказ такси»

| Правило / исключение | Функция | Класс исключения | Код API | Тест |
| --- | --- | --- | --- | --- |
| БП-01: точка в зоне обслуживания | drivers.check_coordinates() | InvalidCoordinatesError | 400 | test_border_allowed_outside_forbidden, test_zone_borders_allowed, test_outside_zone_forbidden_on_each_border, test_dropoff_outside_zone_forbidden, test_pickup_outside_area_creates_nothing, test_api_bad_coordinates_400 |
| БП-04, исключение 5б: одна активная поездка | create_ride() + ограничение СУБД | ActiveRideError | 422 | test_second_active_ride_forbidden, test_db_blocks_second_active_ride_of_client, test_paid_ride_counts_as_active, test_r5_active_ride_checked_before_free_drivers, test_integrity_error_becomes_active_ride_error, test_api_second_active_ride_422 |
| Исключение 5а: свободных машин нет | occupy_nearest_driver() | NoFreeDriversError | 409 | test_no_free_drivers, test_next_driver_taken_when_first_one_is_grabbed, test_api_no_free_cars_409 |
| БП-05: заявка ждёт оплаты 10 минут | expire_rides(), pay() | SessionExpiredError | 410 | test_expired_ride_frees_driver, test_pay_exactly_at_session_end_allowed, test_pay_after_session_end_forbidden, test_pay_after_session_end_is_410, test_search_shows_driver_after_session_end |
| БП-02: после оплаты отмена невозможна | cancel() | CancelNotAllowedError | 409 | test_cancel_paid_ride_forbidden_bp02, test_pay_then_repeat_then_cancel_codes |
| Запрещённый переход статуса | _move(), pay(), cancel() | InvalidStatusError | 409 | test_pay_twice_forbidden, test_cancel_twice_forbidden, test_pay_after_cancel_forbidden_and_no_charge |
| Исключение 7а: банк отклонил карту | pay(), gateway.charge() | PaymentDeclinedError | 402 | test_declined_card_keeps_ride_searching, test_pay_then_repeat_then_cancel_codes |
| БП-03: стоимость поездки | tariffs.estimate_price() | ValueError при отрицательном расстоянии | — | test_price_is_base_plus_rate_per_km, test_zero_distance_costs_base_price, test_negative_distance_is_rejected |

Иерархия: TaxiError (config/errors.py) → InvalidCoordinatesError, NoFreeDriversError, ActiveRideError, InvalidStatusError, CancelNotAllowedError, SessionExpiredError, PaymentDeclinedError.
Проверка таблицы: `python tools/trace_check.py docs/traceability.md drivers/services.py rides/services.py tariffs/services.py`.
