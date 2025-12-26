
# EnergyUA Schedule (Полтава) — HACS інтеграція

Інтеграція Home Assistant для парсингу періодів відключень зі сторінки `https://energy-ua.info/cherga/3-1`.

## Можливості
- Парсить блок `div.periods_items > span`, бере **перші два `<b>`** всередині кожного рядка як `start` та `end` (надійно для верстки сайту).
- Визначає поточний стан: **є світло чи ні**.
- Розраховує **хвилини до найближчої зміни** та **таймер `HH:MM` без секунд**.
- Має **претригер**: `on`, коли рівно за N хвилин до зміни.

## Встановлення через HACS
1. Розмістіть вміст цього архіву у вашому репозиторії (рекомендований slug: `energy-ua-poltava`).
2. У HACS → Integrations → `⋮` → **Custom repositories** → додайте URL (Type: Integration).
3. Знайдіть **EnergyUA Schedule** та встановіть.
4. У HA: **Settings → Devices & Services → Add Integration** → **EnergyUA Schedule**.
5. Вкажіть **Queue URL** (за замовчуванням `https://energy-ua.info/cherga/3-1`), **Update interval (minutes)**, **Pretrigger minutes**.

## Створювані сутності
- `sensor.energyua_minutes_until_next_change` — хвилини до зміни.
  - атрибути: `countdown_hm` (HH:MM), `next_change_type` (`off`/`on`), `periods` (текст рядків зі сторінки).
- `sensor.energyua_countdown_hm` — строка HH:MM.
- `binary_sensor.energyua_power_state_now` — є світло зараз? (`on`/`off`).
- `binary_sensor.energyua_pretrigger` — претригер «рівно за N хвилин» (`on`/`off`).

## Сумісність
- Перевірено на **Home Assistant 2022.5.x**: є **фолбек** до старого API (`async_forward_entry_setup`).
- Працює на нових версіях (використовує `async_forward_entry_setups`, якщо доступний).

