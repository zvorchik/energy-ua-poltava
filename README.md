
# EnergyUA Schedule (Полтава) — HACS інтеграція (періоди з сайту)

**Парсинг тільки з блоку "Періоди відключень на сьогодні"** на сторінці `https://energy-ua.info/cherga/<group>`.
Жодних JS-таймерів: інтеграція бере часи безпосередньо зі статичного контенту сторінки.

## Як працює парсер
1. Шукає контейнер `div.periods_items` і всередині кожного `<span>` бере **перші два `<b>`** як `start/end`.
2. Якщо контейнера немає → бере **повний текст сторінки** та шукає всі співпадіння за шаблоном:
   `З HH:MM до HH:MM` (регекс толерує пробіли/переноси рядків).
3. Коректно обробляє періоди, що переходять через північ.

## Встановлення через HACS
1. Помістіть вміст цього архіву у Git-репозиторій (рекомендований slug: `energy-ua-poltava`).
2. В HA → HACS → Integrations → `⋮` → **Custom repositories** → додайте URL вашого репозиторію (Type: **Integration**).
3. Встановіть **EnergyUA Schedule** із HACS.
4. У HA: **Settings → Devices & Services → Add Integration** → знайдіть **EnergyUA Schedule**.

## Налаштування (UI)
- **Group**: наприклад `3-1`.
- **Scan interval (minutes)**: інтервал опитування.
- **Pretrigger minutes**: хвилини для претригера.

## Сутності
- `sensor.energyua_minutes_until_next_change` — хвилини до найближчої зміни.
  - атрибути: `countdown_hm` (HH:MM), `next_change_type` (`off`/`on`), `source_url`.
- `sensor.energyua_countdown_hm` — строка HH:MM.
- `binary_sensor.energyua_power_state_now` — чи є світло зараз (`on`/`off`).
- `binary_sensor.energyua_pretrigger` — `on` рівно за N хвилин до зміни.

## Сумісність
- Перевірено на **Home Assistant 2022.5.x**: є фолбек до старого API `async_forward_entry_setup`.
