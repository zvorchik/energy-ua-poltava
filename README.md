
# Energy UA Poltava (для Home Assistant 2022.5.5)

**Energy UA Poltava** — кастомна інтеграція для Home Assistant, що отримує два параметри зі сторінки  
[`https://energy-ua.info/cherga/<group>`](https://energy-ua.info/cherga/3-1):

- **`#ch_timer_text`** — текстовий індикатор (наприклад, «До увімкнення залишилось…»).
- **`#ch_timer_time`** — таймер у **секундах**. Якщо на сторінці відображається рядок на кшталт «12 год 13 хв 22 сек», інтеграція розбирає його та конвертує у секунди.

Інтеграція сумісна з **Home Assistant 2022.5.5** і працює як:
- інтеграція з **UI‑налаштуванням (config flow)** — зручний спосіб через `Settings → Devices & Services`.
- або як **YAML-платформа** (для бажаючих конфігурувати через `configuration.yaml`).

> Дані беруться зі стороннього сайту, їхня точність може змінюватися. За офіційною інформацією звертайтесь до офіційних каналів вашого Обленерго.

---

## Можливості

- Вибір **черги/підгрупи** (наприклад, `3-1`, `3-2` тощо) з автоматичною підстановкою у URL.
- Два сенсори:
  - `sensor.energy_ua_ch_timer_text` — текст з `#ch_timer_text`.
  - `sensor.energy_ua_ch_timer_time` — таймер у секундах з `#ch_timer_time` (або обчислюється зі строкового формату «год/хв/сек»).
- Оновлення за розкладом (типово щохвилини).
- Легка установка через **HACS** як Custom Repository.

---

## Вимоги

- Home Assistant **2022.5.5** або сумісний з цією версією форматами інтеграцій.
- Доступ до Інтернету з Home Assistant.
- Залежність **BeautifulSoup** ставиться автоматично (через `requirements` в `manifest.json`).

---

## Установка через HACS (рекомендовано)

1. Відкрий **HACS → Integrations → ⋮ (угорі праворуч) → Custom repositories**.
2. Додай URL репозиторію:  
   **`https://github.com/zvorchik/energy-ua-poltava`**  
   і вибери **Category: Integration**.
3. Встанови інтеграцію з HACS — файли з’являться в `config/custom_components/energy_ua_poltava`.

### Далі — налаштування (два варіанти)

#### Варіант А: через інтерфейс (config flow)
1. Відкрий **Settings → Devices & Services**.
2. Натисни **Add Integration** → знайди **Energy UA Poltava**.
3. Заповни поля:
   - **`group`** — наприклад, `3-1`, `3-2`, `1-1`…
   - **`scan_interval`** — інтервал опитування у секундах (типово `60`).
4. Після додавання інтеграція з’явиться в списку, а сенсори — у переліку Entities.

#### Варіант Б: через YAML (без плитки в Devices & Services)
> У YAML-режимі інтеграція не відображається як плитка в Devices & Services, але сенсори будуть доступні у списку Entities.

```yaml
sensor:
  - platform: energy_ua_poltava
    group: "3-1"      # можна "3-2", "1-1" тощо
    scan_interval: 60 # секунди
