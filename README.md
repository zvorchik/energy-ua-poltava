
# EnergyUA Schedule (Полтава) — HACS інтеграція (debug build)

Цей варіант має більш **надійний парсинг** та **сервіс для дампу HTML**:
- Парсить `div.periods_items > span` і забирає **перші два `<b>`** як час `start/end`.
- Якщо контейнеру немає, шукає **будь‑які `span`, що містять 2 теги `<b>`** на сторінці.
- Якщо і це порожньо — застосовує **regex `З HH:MM до HH:MM`** по всьому HTML.
- Реєструє сервіс `energy_ua_poltava.dump_html` → створює `/config/www/energyua_dump.html` з останнім HTML.

## Встановлення
1. Покладіть вміст в репозиторій (slug: `energy-ua-poltava`).
2. Додайте репозиторій у HACS (Type: Integration) і встановіть **EnergyUA Schedule**.
3. Додайте інтеграцію через UI. За замовчуванням URL: `https://energy-ua.info/cherga/3-1`.

## Як зняти дамп HTML
У Developer Tools → **Services**:
- Service: `energy_ua_poltava.dump_html`
- Data: `{}` (порожньо)
Файл буде у `/config/www/energyua_dump.html`.
