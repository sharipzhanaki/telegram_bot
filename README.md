# Hotel Search Telegram Bot

Telegram-бот для поиска отелей по всему миру с многошаговым FSM-диалогом, inline-календарём для выбора дат и историей запросов. Интегрируется с Hotels4 API (RapidAPI) и умеет фильтровать результаты по цене, рейтингу гостей и расстоянию до центра города.

---

## Стек технологий

| Слой | Технология |
|---|---|
| Язык | Python 3.12 |
| Telegram API | pyTelegramBotAPI 4.29 (sync polling) |
| FSM | `StateMemoryStorage` + `StatesGroup` |
| HTTP-клиент | `requests` |
| База данных | SQLite через `peewee` ORM |
| Конфигурация | `python-dotenv` |
| Внешний API | Hotels4 (`hotels4.p.rapidapi.com`) |

---

## Ключевые фичи

### Три режима поиска
- **`/lowprice`** — самые дешёвые отели, сортировка `PRICE_LOW_TO_HIGH`
- **`/guest_rating`** — топ по оценкам гостей, сортировка `REVIEW`
- **`/bestdeal`** — фильтр по цене + максимальному расстоянию до центра, сортировка `DISTANCE`

### Inline-календарь
Выбор дат через кастомный inline-календарь (не текстовый ввод):
- Прошедшие даты отображаются как `·N` и некликабельны
- Сегодня выделен `[N]`
- Навигация по месяцам без перезагрузки сообщения (`edit_message_reply_markup`)
- Дата выезда автоматически ограничена: минимум `check_in + 1 день`

### Устойчивая фильтрация результатов
API всегда запрашивает 50 отелей (даже если пользователь просит 3–5), после чего применяется локальная фильтрация по цене/расстоянию и срез до нужного количества. Это решает проблему нехватки результатов из-за серверной фильтрации.

### История запросов
`/history` сохраняет последние 5 поисков в SQLite (параметры + найденные отели) и отображает их с форматированными карточками отелей.

### HTML-форматирование
Единый `format_hotel_card()` в `utils/misc/hotel_card.py` генерирует HTML-карточку отеля с кликабельной ссылкой «Забронировать →» для всех трёх команд и истории.

---

## Архитектурные решения

```
telegram_bot/
├── config_data/        # .env, константы, команды меню
├── database/           # peewee модели (History), init_db, save/get helpers
├── handlers/
│   ├── callback_handlers/
│   │   ├── city_choice.py      # выбор города из inline-кнопок
│   │   └── calendar_handler.py # cal:nav:* / cal:day:* callbacks
│   ├── custom_handlers/        # FSM-сценарии lowprice / guest_rating / bestdeal / history
│   └── default_handlers/       # /start, /help, echo
├── keyboards/
│   ├── calendar/
│   │   └── calendar_kb.py      # create_calendar(year, month, *, min_date)
│   ├── inline/                 # cities_keyboard
│   └── reply/                  # yes_no_keyboard, remove_keyboard
├── states/
│   └── search_states.py        # LowPriceStates, GuestRatingStates, BestDealStates
├── utils/
│   ├── api/
│   │   ├── base_client.py      # api_get / api_post с логированием
│   │   ├── locations_api.py    # /locations/v3/search → список городов
│   │   └── hotels_api.py       # _search_hotels, search_hotels_lowprice/guest_rating/bestdeal
│   ├── misc/
│   │   └── hotel_card.py       # format_hotel_card() — HTML-рендер карточки
│   └── logger.py               # диктконфиг: console + file_info + file_error
├── loader.py                   # singleton: bot, state_storage
└── main.py                     # точка входа: init_db → set_commands → polling
```

**Ключевые решения:**
- **Lazy imports в `calendar_handler`** — импорт конкретных search-функций происходит внутри callback, а не на уровне модуля, что предотвращает циклические зависимости между `handlers/callback_handlers` и `handlers/custom_handlers`.
- **`bot.get_state()` для роутинга дат** — один обработчик `cal:day:*` обслуживает все три команды, определяя контекст через строку состояния (`"LowPriceStates:start_date"`), без дублирования логики.
- **API запрашивает 50, возвращает N** — все три команды делают запрос на 50 результатов, локально фильтруют и срезают до `hotels_count`. Это устраняет ситуацию «пользователь просит 5, API после фильтрации возвращает 2».
- **SQLite + peewee** — история хранится локально без внешних зависимостей; схема создаётся автоматически при старте через `db.create_tables([History])`.

---

## Локальный запуск

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd telegram_bot
```

### 2. Создать виртуальное окружение и установить зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Создать `.env`

```env
BOT_TOKEN=your_telegram_bot_token
RAPID_API_KEY=your_rapidapi_key
DB_NAME=hotels.db
```

- `BOT_TOKEN` — получить у [@BotFather](https://t.me/BotFather)
- `RAPID_API_KEY` — получить на [RapidAPI / Hotels4](https://rapidapi.com/apidojo/api/hotels4)

### 4. Запустить

```bash
python main.py
```

База данных `hotels.db` создаётся автоматически при первом запуске.

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие |
| `/help` | Список команд |
| `/lowprice` | Поиск дешёвых отелей |
| `/guest_rating` | Поиск популярных отелей |
| `/bestdeal` | Лучшее предложение (цена + расстояние) |
| `/history` | Последние 5 поисков |
