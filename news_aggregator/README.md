# NewsRadar — Комплексный новостной агрегатор

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-3.0-green?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey?style=flat-square)
![ML](https://img.shields.io/badge/ML-scikit--learn-orange?style=flat-square)

Автоматический новостной агрегатор с ML-классификацией, собирающий новости из трёх источников (Lenta.ru, RBC, Habr), классифицирующий их по темам и отображающий через Flask-интерфейс с cyberpunk-дизайном.

---

## Архитектура проекта

```
URL → RSS/feedparser / HTML/BeautifulSoup
             ↓
       scraper.py (очистка текста)
             ↓
     classifier.py (TF-IDF → ML)
             ↓
      database.py (SQLite)
             ↓
       app.py (Flask)
             ↓
    templates/index.html (UI)
             ↓
         Пользователь

scheduler.py → запуск scraper.py каждый час (APScheduler)
```

---

## Структура файлов

```
news_aggregator/
├── app.py           — Flask-приложение, маршруты, REST API
├── scraper.py       — Скрапинг RSS/HTML трёх источников
├── classifier.py    — ML: TF-IDF + MultinomialNB, sentiment
├── database.py      — SQLite: init, insert, select, stats
├── scheduler.py     — APScheduler: автообновление каждый час
├── requirements.txt — Python зависимости
├── templates/
│   └── index.html   — Cyberpunk Flask UI
├── models/
│   └── classifier.pkl  — Сохранённая ML-модель (создаётся при первом запуске)
└── news.db          — SQLite база данных (создаётся при первом запуске)
```

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/<username>/news_aggregator.git
cd news_aggregator
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Запустить приложение

```bash
python app.py
```

Открыть в браузере: **http://127.0.0.1:5000**

---

## Источники новостей

| Источник | URL | Тип |
|----------|-----|-----|
| Lenta.ru | https://lenta.ru/rss/news | RSS |
| RBC      | https://rssexport.rbc.ru/rbcnews/news/30/full.rss | RSS |
| Habr     | https://habr.com/ru/rss/articles/ | RSS |

---

## ML-классификация

Модуль `classifier.py` реализует следующий pipeline:

1. **Предобработка** (`preprocess()`): нижний регистр, удаление спецсимволов
2. **TF-IDF** (`TfidfVectorizer`): унаграммы + биграммы, 5000 признаков
3. **Классификатор** (`MultinomialNB`): наивный байесовский классификатор
4. **Sentiment** (словарный подход): позитивный / негативный / нейтральный

### Категории

`технологии` · `политика` · `спорт` · `экономика` · `наука` · `gaming` · `общество` · `развлечения`

---

## База данных SQLite

Таблица `articles`:

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER PK | Автоинкремент |
| title | TEXT | Заголовок |
| url | TEXT UNIQUE | Ссылка (защита от дублей) |
| description | TEXT | Описание |
| published | TEXT | Дата публикации |
| source | TEXT | Источник |
| category | TEXT | ML-категория |
| sentiment | TEXT | Эмоциональная окраска |
| created_at | DATETIME | Время добавления в БД |

UNIQUE constraint на `url` предотвращает дублирование статей.

---

## REST API

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/` | Главная страница |
| GET | `/api/articles?category=&search=&limit=` | Список статей (JSON) |
| GET | `/api/stats` | Статистика БД |
| POST | `/api/scrape` | Ручной запуск скрапинга |
| GET | `/api/next-update` | Время следующего обновления |

---

## Автообновление (APScheduler)

```python
scheduler.add_job(
    func=scheduled_scrape,
    trigger=IntervalTrigger(hours=1),
    max_instances=1,
    coalesce=True,
)
```

Запускается в фоновом потоке при старте Flask. Каждый час автоматически скрапит все три источника и добавляет новые статьи в БД.

---

## Команда и роли

| Роль | Ответственность | Файл |
|------|----------------|------|
| Backend Developer | Скрапинг + SQLite | `scraper.py`, `database.py` |
| ML Engineer | Классификация + Sentiment | `classifier.py` |
| Fullstack Developer | Flask + UI + Scheduler | `app.py`, `templates/`, `scheduler.py` |

---

## Работа с Git (ветки)

```bash
# Backend Developer
git checkout -b feature/scraper
# ... работа над scraper.py и database.py ...
git add scraper.py database.py
git commit -m "feat: RSS scraper for Lenta, RBC, Habr + SQLite storage"
git push origin feature/scraper

# ML Engineer
git checkout -b feature/classifier
# ... работа над classifier.py ...
git add classifier.py
git commit -m "feat: TF-IDF + MultinomialNB classifier with sentiment analysis"
git push origin feature/classifier

# Fullstack Developer
git checkout -b feature/flask-ui
# ... работа над app.py и templates/ ...
git add app.py templates/ scheduler.py
git commit -m "feat: Flask routes, cyberpunk UI, APScheduler integration"
git push origin feature/flask-ui

# Тимлид — слияние всех веток в main
git checkout main
git merge feature/scraper
git merge feature/classifier
git merge feature/flask-ui
git push origin main
```

---

## Теоретическая справка

**Что делает BeautifulSoup?**
Парсит HTML/XML документы, предоставляя удобный API для поиска и извлечения данных по тегам, атрибутам, CSS-селекторам.

**Как работает TF-IDF?**
TF (Term Frequency) — частота слова в документе. IDF (Inverse Document Frequency) — обратная частота документов, содержащих слово. TF-IDF = TF × IDF. Слова, редкие в корпусе, но частые в документе, получают высокий вес.

**Почему SQLite для mini-project?**
SQLite — serverless, не требует отдельного процесса, хранится в одном файле, поддерживает SQL, UNIQUE constraints. Идеален для проектов до ~100k записей.

**Как scheduler автоматизирует обновления?**
APScheduler запускает Python-функцию в фоновом потоке по расписанию (IntervalTrigger). Параметр `max_instances=1` предотвращает параллельный запуск, `coalesce=True` — пропускает пропущенные задачи.
