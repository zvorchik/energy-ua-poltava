

# EnergyUA Schedule (Полтава) — HACS інтеграція

Графік відключень з `https://energy-ua.info/cherga/<group>`: таймер до наступної зміни, стан світла за графіком і претригер.

## Як працює парсер
1. Основне джерело — дані, які сторінка передає своєму JS-графіку: `const periods = [...]` (сьогодні) і `tomorrowPeriods` (завтра).
   Час там в unix-секундах, тому дата, перехід через північ і переведення годинника враховані.
   Статуси `red` (немає світла) і `yellow` (можливе відключення) рахуються як відключення.
2. Якщо JS-даних немає — блоки `div.periods_items` («З HH:MM до HH:MM»), окремо для «сьогодні» і «завтра».
3. Сусідні періоди (22:00–24:00 + 00:00–02:00) зливаються в одне відключення.
4. Якщо сайт недоступний або віддав заглушку Cloudflare — лишається попередній графік, наступна спроба за звичайним інтервалом або кнопкою.

Сторінка опитується при старті, далі раз на **scan interval** (якщо увімкнено автооновлення) або кнопкою **EnergyUA Fetch Schedule**. Таймер перераховується локально рівно о :00 кожної хвилини.

## Встановлення через HACS
1. HACS → Integrations → `⋮` → **Custom repositories** → URL цього репозиторію (Type: **Integration**).
2. Встановіть **EnergyUA Schedule** із HACS і перезапустіть Home Assistant.
3. **Settings → Devices & Services → Add Integration** → **EnergyUA Schedule**.

## Налаштування
- **Group** — черга, наприклад `3-1`.
- **Оновлювати автоматично** — якщо вимкнено, сайт питається лише при старті та кнопкою.
- **Scan interval (minutes)** — як часто тягнути графік з сайту, від 30 хв.
- **Pretrigger minutes** — за скільки хвилин до зміни вмикати претригер.

Інтервал і претригер можна змінити пізніше: інтеграція → **Налаштувати**.

## Сутності
- `sensor.energyua_minutes_until_next_change` — хвилини до найближчої зміни; `unknown`, якщо на сьогодні й завтра відключень більше немає.
  - атрибути: `countdown_hm`, `next_change_type` (`off` — світло зникне, `on` — з'явиться), `next_change`, `periods`, `last_success`, `source_url`.
- `sensor.energyua_countdown` — рядок `HH:MM` або «Відключень немає».
- `sensor.energyua_next_change` — момент наступної зміни (timestamp); підходить для `trigger: time` з `offset`.
- `binary_sensor.energyua_power_state_now` — чи є світло за графіком.
- `binary_sensor.energyua_pretrigger` — `on` за N хвилин до **будь-якої** зміни; напрямок в атрибуті `next_change_type`.
- `button.energyua_fetch_schedule` — один запит до сайту зараз.
- `button.reload_energyua_poltava` — перезавантажити інтеграцію.

## Сумісність
Перевірено на Home Assistant 2025.11. Лишились фолбеки на старе API (`async_forward_entry_setup`).
