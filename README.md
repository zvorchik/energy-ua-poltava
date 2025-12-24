
# Energy UA Poltava (Home Assistant 2022.5.5)

**Energy UA Poltava** — кастомна інтеграція для Home Assistant, що отримує два параметри зі сторінки  
`https://energy-ua.info/cherga/<group>` (наприклад, `3-1`, `3-2`):

- `#ch_timer_text` — текстовий індикатор (напр., «До увімкнення залишилось…»).
- `#ch_timer_time` — таймер у **секундах**. Якщо на сторінці замість чисел показано рядок на кшталт «12 год 13 хв 22 сек», інтеграція розбирає його та конвертує у секунди.

> Сумісно з **Home Assistant 2022.5.5**. Інтеграція може працювати як **UI‑інтеграція (config flow)** або як **YAML‑платформа**.

---

## Можливості

- Вибір **черги/підгрупи** (`group`: `3-1`, `3-2`, тощо).
- **Сенсори**:
  - `sensor.energy_ua_ch_timer_text` — текст з `#ch_timer_text`.
  - `sensor.energy_ua_ch_timer_time` — секунди з `#ch_timer_time` (або обчислені з рядка «год/хв/сек»).
  - *(у версії v0.4+)* **`sensor.energy_ua_ch_timer`** — об’єднаний сенсор (секунди) з атрибутами:
    - `text` — поточний текст,
    - `group` — обрана черга,
    - `source` — URL сторінки.

---

## Вимоги

- Home Assistant **2022.5.5**.
- Доступ до Інтернету з інстансу HA.
- Залежність **BeautifulSoup** (встановлюється автоматично через `requirements` в `manifest.json`).

---

## Установка через HACS (рекомендовано)

1. **HACS → Integrations → ⋮ → Custom repositories**.
2. Додай URL репозиторію:  
   `https://github.com/zvorchik/energy-ua-poltava`  
   і вибери **Category: Integration**.
3. Встанови інтеграцію з HACS — файли з’являться у `config/custom_components/energy_ua_poltava`.

### Налаштування (два варіанти)

#### Варіант А — через інтерфейс (config flow)
1. **Settings → Devices & Services → Add Integration → Energy UA Poltava**.
2. Заповни:
   - **`group`** — напр., `3-1`, `3-2`, `1-1`…
   - **`scan_interval`** — інтервал опитування у секундах (типово `60`).

Після додавання інтеграція з’явиться у списку, а сенсори — у **Developer Tools → States**.

#### Варіант Б — через YAML (без плитки в Devices & Services)
> У YAML‑режимі інтеграція **не відображається** як плитка в Devices & Services; сенсори будуть у списку Entities.

```yaml
sensor:
  - platform: energy_ua_poltava
    group: "3-1"      # можна "3-2", "1-1" і т.д.
    scan_interval: 60 # секунди
