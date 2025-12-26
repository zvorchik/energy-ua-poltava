
# EnergyUA Schedule (energy-ua-poltava)

Репозиторий/slug: **energy-ua-poltava** (с дефисом).
Домейн интеграции Home Assistant: **energy_ua_poltava** (в HA домейны допускают только **буквы, цифры и подчёркивания**).

## Возможности
- Настройка **через UI** (Config Flow): URL очереди, интервал обновления, минуты претриггера.
- Вычисляет: текущее состояние света (on/off), минуты до ближайшего изменения,
  таймер HH:MM (без секунд), тип следующего события (off/on), бинарный претриггер «ровно за N минут».
- Корректная обработка интервалов через полночь. Локальное время HA.

## Установка через HACS
1. Опубликуйте содержимое репозитория под slug **energy-ua-poltava**.
2. В HA → HACS → Integrations → `⋮` → **Custom repositories** → добавьте URL (Type: Integration).
3. Установите **EnergyUA Schedule** из HACS.
4. Добавьте интеграцию: **Settings → Devices & Services → Add Integration** → **EnergyUA Schedule**.

## Создаваемые сущности
- `sensor.energyua_minutes_until_next_change` (минуты) + атрибуты `countdown_hm`, `next_change_type`, `periods`.
- `sensor.energyua_countdown_hm` — строка HH:MM.
- `binary_sensor.energyua_power_state_now` — есть свет сейчас? (on/off).
- `binary_sensor.energyua_pretrigger` — претриггер «ровно за N минут» (on/off).
