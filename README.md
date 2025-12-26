
# EnergyUA Schedule (Полтава) — HACS інтеграція (альтернативний парсер)

Цей билд використовує **DOM-поля таймера** зі сторінки (`ch_timer_text`, `ch_timer_time`) замість
блоку `periods_items`. Логіка:
- Беремо текст із `<div class="ch_timer_text">`.
- Беремо години/хвилини/секунди з `<div class="ch_timer_time">` (`#hours`, `#minutes`, `#seconds`).
- Якщо таймер відсутній, парсимо H/M/S із загального тексту (регекс).
- Якщо й це порожньо, парсимо інтервали `З HH:MM до HH:MM` (регекс) і рахуємо час до наступної зміни.

## Встановлення через HACS
1. Покладіть вміст архіву у ваш Git-репозиторій (рекомендований slug: `energy-ua-poltava`).
2. У HA: HACS → Integrations → `⋮` → **Custom repositories** → додайте URL (**Type: Integration**).
3. Установіть **EnergyUA Schedule** у HACS.
4. Додайте інтеграцію в HA: **Settings → Devices & Services → Add Integration** → **EnergyUA Schedule**.

## Налаштування (UI)
- **Group**: наприклад `3-1` (буде підставлено в базовий URL `https://energy-ua.info/cherga/`).
- **Scan interval (seconds)**: період опитування (за замовчуванням 60 секунд).

## Створювані сутності
- `sensor.energyua_minutes_until_next_change` — хвилини до зміни (з таймера/регексів).
  - атрибути: `countdown_hm`, `next_change_type`, `source_url`.
- `sensor.energyua_countdown_hm` — строка `HH:MM`.
- `binary_sensor.energyua_power_state_now` — стан світла зараз (`on`/`off`).
- `binary_sensor.energyua_pretrigger` — `on`, коли рівно за N хвилин (із Options) до зміни.
- Додатково (як у старому файлі):
  - `sensor.energy_ua_ch_timer_time` — секунди до зміни.
  - `sensor.energy_ua_ch_status` — `ON` / `OFF` (за текстом сайту).
  - `sensor.energy_ua_ch_timer` — сек + атрибути (`text`, `status`, `group`, `source`).

## Сумісність
- Перевірено на **Home Assistant 2022.5.x** — є фолбек до старого API `async_forward_entry_setup`.
