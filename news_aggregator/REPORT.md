# Отчёт по практической работе
## «Комплексный новостной агрегатор NewsRadar»

**Технологии:** Flask · SQLite · BeautifulSoup · Machine Learning · APScheduler  
**Команда:** 3 участника (Backend Developer, ML Engineer, Fullstack Developer)

---

## Шаг 0: Концепция и распределение ролей

### Название и тематика

**NewsRadar** — автоматический агрегатор русскоязычных новостей. Собирает публикации из трёх крупных источников, классифицирует по темам через ML и предоставляет удобный веб-интерфейс с поиском и фильтрацией.

### Источники новостей

| № | Источник | URL | Охват |
|---|----------|-----|-------|
| 1 | Lenta.ru | `https://lenta.ru/rss/news` | Общие новости России |
| 2 | RBC | `https://rssexport.rbc.ru/rbcnews/news/30/full.rss` | Бизнес, политика, экономика |
| 3 | Habr | `https://habr.com/ru/rss/articles/` | ИТ и технологии |

### Категории классификации

`технологии` · `политика` · `спорт` · `экономика` · `наука` · `gaming` · `общество` · `развлечения`

### Распределение ролей

| Роль | Участник | Файлы | Ветка |
|------|----------|-------|-------|
| Backend Developer | Участник 1 | `scraper.py`, `database.py` | `feature/scraper` |
| ML Engineer | Участник 2 | `classifier.py` | `feature/classifier` |
| Fullstack Developer | Участник 3 | `app.py`, `templates/`, `scheduler.py` | `feature/flask-ui` |

### Схема архитектуры

```
                    ┌─────────────┐
                    │  Источники  │
                    │ Lenta · RBC │
                    │    Habr     │
                    └──────┬──────┘
                           │ RSS/HTML
                    ┌──────▼──────┐
                    │  scraper.py │  ← feedparser, BeautifulSoup
                    │  Очистка    │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │      classifier.py      │
              │  TF-IDF → MultinomialNB │
              │  Sentiment анализ       │
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │ database.py │  ← SQLite, UNIQUE url
                    │  news.db    │
                    └──────┬──────┘
                           │
          ┌────────────────▼────────────────┐
          │            app.py               │
          │         Flask routes            │
          │   /  /api/articles  /api/stats  │
          └────────────────┬────────────────┘
                           │
                    ┌──────▼──────┐
                    │  index.html │  ← Cyberpunk UI
                    │  Поиск/Фильтр│
                    └─────────────┘

          scheduler.py → каждый час → scraper.py
```

---

## Часть 1: Сбор новостей и база данных

### 1.1 Скрапер (`scraper.py`)

Модуль реализует три уровня получения данных:

1. **feedparser** — основной метод для RSS-лент. Надёжно обрабатывает различные форматы RSS/Atom, автоматически парсит даты.
2. **BeautifulSoup** — резервный метод HTML-парсинга при недоступности RSS. Извлекает заголовки из тегов `<h2>`, `<h3>` с вложенными ссылками.
3. **clean_html()** — очистка текста от HTML-тегов через BeautifulSoup + нормализация пробелов.

Ключевые решения:
- `time.sleep(1)` между источниками — вежливый скрапинг, не перегружает серверы
- Обрезка description до 500 символов — экономия места в БД
- Проверка `if title and url` — фильтрация невалидных записей

### 1.2 База данных (`database.py`)

Схема таблицы `articles`:

```sql
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    url         TEXT    NOT NULL UNIQUE,  -- защита от дублей
    description TEXT,
    published   TEXT,
    source      TEXT,
    category    TEXT    DEFAULT 'общее',
    sentiment   TEXT    DEFAULT 'нейтральный',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**UNIQUE constraint на `url`** — главный механизм предотвращения дублирования. При попытке вставить уже существующую статью SQLite бросает `IntegrityError`, который мы перехватываем и возвращаем `False`.

### Логические выводы — Часть 1

**Качество источников:**
- Lenta.ru — наиболее стабильный RSS. Даёт 30–50 новостей за запрос, включает описание.
- RBC — богатый RSS с полными текстами, но иногда содержит HTML в description.
- Habr — технический контент высокого качества, небольшой объём (~20 статей).

**Проблемы HTML-парсинга:**
- Некоторые RSS-ленты содержат HTML в полях `summary`/`description` — решено через `clean_html()`.
- Даты в разных форматах — feedparser унифицирует через `published_parsed`.
- Относительные URLs в HTML fallback — решено через `urljoin()`.

**Вывод:** RSS значительно надёжнее HTML-парсинга, менее зависит от структуры страницы. UNIQUE constraint эффективно устраняет дубли при повторных запусках.

---

## Часть 2: Machine Learning классификация

### 2.1 ML Pipeline (`classifier.py`)

```
Текст (заголовок + описание)
        ↓
    preprocess()
    lower → re.sub спецсимволы → re.sub цифры → strip
        ↓
    TfidfVectorizer
    ngram_range=(1,2), max_features=5000, sublinear_tf=True
        ↓
    MultinomialNB(alpha=0.1)
        ↓
    model.predict([text]) → категория
```

**Выбор модели:** MultinomialNB (наивный байес) — стандартный выбор для текстовой классификации:
- Быстрое обучение (< 1 сек на датасете)
- Хорошо работает с TF-IDF признаками
- Не требует много памяти
- `alpha=0.1` — сглаживание Лапласа

**TF-IDF параметры:**
- `ngram_range=(1,2)` — учитываем биграммы ("машинное обучение", "искусственный интеллект")
- `sublinear_tf=True` — логарифмирование TF, снижает влияние частых слов
- `max_features=5000` — ограничение размерности

### 2.2 Sentiment Analysis

Словарный подход на русском языке:
- 22 позитивных слова: победа, успех, рост, прорыв, ...
- 23 негативных слова: война, кризис, катастрофа, арест, ...
- Результат: сравнение числа совпадений → позитивный / негативный / нейтральный

### Логические выводы — Часть 2

**Качество классификации:**
Модель хорошо разделяет технологии (Habr), спорт (специфическая лексика), gaming. Сложнее с политикой/экономикой — пересекающаяся лексика (санкции, кризис относятся к обеим).

**Ограничения:**
- Небольшой обучающий датасет (~60 примеров) — в production нужны тысячи
- Словарный sentiment примитивен — в production лучше BERT/multilingual
- Нет лемматизации (не установлен pymystem3) — биграммы частично компенсируют

**Улучшения для production:**
- Загрузка обучающих данных из реальных размеченных новостей
- Подключение pymorphy2 для морфологической нормализации
- Использование ruBERT для sentiment вместо словарей

---

## Часть 3: Flask и автоматизация

### 3.1 Flask интерфейс (`app.py`)

Маршруты:

| Метод | URL | Функция |
|-------|-----|---------|
| GET | `/` | Главная с фильтрацией |
| GET | `/api/articles` | JSON REST API |
| GET | `/api/stats` | Статистика БД |
| POST | `/api/scrape` | Ручной скрапинг |
| GET | `/api/next-update` | Время обновления |

### 3.2 UI (`templates/index.html`)

**Cyberpunk-дизайн:** тёмная палитра (#0a0a0f), акцентный cyan (#00f5c4), фиолетовый (#7b5cfa), шрифты JetBrains Mono + Unbounded, анимированная сетка фона.

**Функциональность:**
- Поиск с debounce 600мс (live search без Enter)
- Фильтрация по категории (sidebar + мобильный скролл)
- Цветовые бейджи категорий и sentiment
- Toast-уведомления при обновлении
- REST API вызов кнопки «Обновить сейчас»
- Адаптивная верстка (мобильный/десктоп)

### 3.3 APScheduler (`scheduler.py`)

```python
scheduler.add_job(
    func=scheduled_scrape,
    trigger=IntervalTrigger(hours=1),
    max_instances=1,   # не запускать параллельно
    coalesce=True,     # пропускать пропущенные
)
```

`BackgroundScheduler` работает в отдельном потоке, не блокируя Flask. `atexit.register(stop_scheduler)` обеспечивает корректное завершение.

### Логические выводы — Часть 3

**Масштабируемость:**
- SQLite подходит до ~100k записей. Для production нужен PostgreSQL.
- BackgroundScheduler — однопоточный. В production нужен Celery + Redis.
- Flask dev-server однопоточный — для production нужен Gunicorn.

**Архитектура:**
Разделение на модули (scraper / classifier / database / scheduler / app) позволяет тестировать каждый компонент независимо. Это соответствует принципу Single Responsibility.

---

## Ответы на теоретические вопросы

**Pipeline URL → Scraper → ML → SQLite → Flask:**
feedparser получает RSS → BeautifulSoup очищает HTML → TF-IDF векторизует текст → MultinomialNB предсказывает категорию → SQLite сохраняет с UNIQUE check → Flask читает через SELECT и рендерит шаблон.

**Что делает BeautifulSoup?**
HTML/XML-парсер. Строит дерево из разметки и предоставляет API для поиска элементов по тегу, классу, атрибуту. В проекте используется для очистки HTML из RSS-полей (`soup.get_text()`) и резервного парсинга страниц.

**Как работает TF-IDF?**
TF = (кол-во вхождений слова в документ) / (общее кол-во слов). IDF = log(кол-во документов / кол-во документов со словом). TF-IDF = TF × IDF. Слова редкие в корпусе, но частые в документе → высокий вес → являются «ключевыми» для данного документа.

**Как Flask отображает данные?**
`get_articles()` возвращает список словарей из SQLite. Flask передаёт их в `render_template('index.html', articles=articles)`. Jinja2 итерирует `{% for a in articles %}` и вставляет данные в HTML.

**Почему SQLite для mini-project?**
Не требует отдельного сервера, хранится в одном `.db` файле, поддерживает SQL и ACID транзакции, нулевая настройка. Встроен в Python через `sqlite3`. Идеален для проектов до ~100k записей.

**Как scheduler автоматизирует обновления?**
APScheduler запускает Python-функцию в фоновом потоке по расписанию. `IntervalTrigger(hours=1)` — каждый час. `max_instances=1` — гарантирует что только один экземпляр работает одновременно. `coalesce=True` — если сервер был выключен и пропустил несколько запусков, выполняет только один раз.

---

## Исходный код (структура)

```
news_aggregator/
├── app.py           258 строк — Flask + маршруты
├── scraper.py       175 строк — RSS/HTML скрапинг
├── classifier.py    210 строк — ML pipeline
├── database.py      130 строк — SQLite CRUD
├── scheduler.py      65 строк — APScheduler
├── requirements.txt   8 строк
├── README.md
├── CONTRIBUTING.md
├── .gitignore
├── .github/
│   └── workflows/ci.yml
└── templates/
    └── index.html   ~350 строк — Cyberpunk UI
```

**Итого:** ~1200 строк кода, полностью задокументированных через docstring.

---

## Критерии выполнения

| Критерий | Статус | Комментарий |
|----------|--------|-------------|
| Скрапинг 3 источников | ✅ | Lenta.ru, RBC, Habr |
| SQLite без дублей | ✅ | UNIQUE constraint на url |
| ML классификация | ✅ | TF-IDF + MultinomialNB, 8 категорий |
| Flask поиск и фильтр | ✅ | Live search + sidebar категорий |
| APScheduler | ✅ | Каждый час, фоновый поток |
| Документация | ✅ | README, CONTRIBUTING, docstring |
| Креативность | ✅ | Cyberpunk UI, Sentiment, REST API, CI |
| GitHub ветки | ✅ | feature/scraper · classifier · flask-ui |
