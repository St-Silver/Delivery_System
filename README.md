# Система учёта заказов "Быстрая доставка"

## Установка и запуск

1. Клонируйте репозиторий:
git clone <URL>
cd delivery_system

2. Установите зависимости (только pytest для тестов):
pip install -r requirements.txt

3. Создайте папки `logs` и `data` (если не созданы) – при первом запуске они появятся автоматически.

## CLI-режим
# Отчёт за месяц
python main_cli.py report --period month

# Экспорт заказов (JSON или XML)
python main_cli.py export --file orders_backup.json
python main_cli.py export --file orders_backup.xml

# Импорт заказов
python main_cli.py import --file orders_new.json
python main_cli.py import --file orders_new.xml

# GUI-режим

python main_gui.py
Функции:
- Просмотр, фильтрация заказов
- Добавление/редактирование/удаление заказов и клиентов
- Отчёт по статусам, топ-3 клиента, выручка
- Экспорт в JSON/XML через меню

## Тестирование
Запустите: `pytest tests/`
Покрытие основных функций, включая CRUD, отчёты, экспорт/импорт.

## Логирование
Все действия пишутся в logs/app.log и дублируются в консоль.

## Структура проекта
- `database.py` – работа с SQLite
- `models.py` – модели данных
- `data_export.py` – экспорт/импорт XML/JSON
- `logger_config.py` – логирование
- `main_cli.py` – интерфейс командной строки
- `main_gui.py` – графический интерфейс
- `tests/` – модульные тесты
- `data/` – файл базы данных delivery.db
- `logs/` – логи приложения
