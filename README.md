
# EnergyUA Schedule (HACS Integration) — HA 2022.5.x совместимый

Интеграция Home Assistant (совместима с **2022.5.5**) для парсинга графика отключений с Energy-UA и вычисления:
- текущего состояния света (`on/off`),
- таймера до ближайшего изменения (формат `HH:MM`, без секунд),
- минут до ближайшего изменения,
- типа следующего изменения (`off` — отключение, `on` — включение),
- бинарного претриггера «ровно за N минут до изменения».

## Установка через HACS
1. Поместите содержимое этого архива в Git-репозиторий.
2. В HACS → Integrations → `⋮` → **Custom repositories** → добавьте URL вашего репозитория (Type: Integration).
3. Установите **EnergyUA Schedule** из HACS.
4. В Home Assistant: **Settings → Devices & Services → Add Integration** → выберите **EnergyUA Schedule** и настройте.

## Настройки (UI)
- **Queue URL**: по умолчанию `https://energy-ua.info/cherga/3-1`.
- **Update interval (minutes)**: период опроса (по умолчанию 15).
- **Pretrigger minutes**: за сколько минут до изменения выставлять претриггер (по умолчанию 10).

## Создаваемые сущности
- `sensor.energyua_minutes_until_next_change` — минуты до ближайшего изменения.
  - атрибуты: `countdown_hm` (HH:MM), `next_change_type` (`off`/`on`), `periods` (текстовые интервалы).
- `sensor.energyua_countdown_hm` — строка HH:MM.
- `binary_sensor.energyua_power_state_now` — есть свет сейчас? (`on`/`off`).
- `binary_sensor.energyua_pretrigger` — претриггер (`on`/`off`).

## Примечания
- Обработка интервалов через полночь: если `конец < начало`, конец переносится на следующий день.
- Используется локальное время HA.
- Зависимость: `beautifulsoup4`.
