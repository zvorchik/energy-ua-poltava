# Energy UA Poltava (HA 2022.5.5)

Кастомная интеграция для Home Assistant, которая забирает два параметра со страницы
[energy-ua.info/cherga/<group>](https://energy-ua.info/cherga/3-1):
- текст таймера (`#ch_timer_text`)
- таймер (`#ch_timer_time`) в секундах (если на странице строка вида «12 год 13 хв 22 сек», она будет распарсена).

## Установка через HACS (Custom repository)
1. Откройте **HACS → Integrations → ⋮ → Custom repositories**.
2. Укажите URL этого репозитория и Category: **Integration**.
3. Установите интеграцию.
4. Добавьте конфигурацию в `configuration.yaml` и перезагрузите HA.

## Конфигурация (YAML)
```yaml
sensor:
  - platform: energy_ua_poltava
    group: "3-1"      # можно "3-2", "1-1" и т.п.
    scan_interval: 60  # секундами
```
URL формируется как `https://energy-ua.info/cherga/<group>`.

## Сенсоры
- `sensor.energy_ua_ch_timer_text` — текст из `#ch_timer_text`
- `sensor.energy_ua_ch_timer_time` — секунды из `#ch_timer_time`

## Примечания
- DOM страницы может меняться; при изменении разметки обновите парсер.
- Интеграция сделана совместимой с **Home Assistant 2022.5.5** (платформенный YAML, DataUpdateCoordinator без новых API 2024.8+).

## Источники
- Страница данных: https://energy-ua.info/cherga/3-1
- Структура интеграций в HA: https://developers.home-assistant.io/docs/creating_integration_file_structure/
- Требования HACS к репозиторию/интеграции: https://hacs.xyz/docs/publish/start/ , https://hacs.xyz/docs/publish/integration/
