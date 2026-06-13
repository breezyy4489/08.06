"""
app.py — Главный Flask-модуль новостного агрегатора NewsRadar.

Маршруты:
  GET  /                  — Главная страница (список новостей)
  GET  /api/articles      — REST API: получить статьи (JSON)
  GET  /api/stats         — REST API: статистика базы данных
  POST /api/scrape        — Ручной запуск скрапинга
  GET  /api/next-update   — Время следующего автообновления
"""

import logging
import atexit
from flask import Flask, render_template, request, jsonify

from database import init_db, get_articles, get_categories, get_stats
from scheduler import start_scheduler, stop_scheduler, get_next_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ──────────────────────────────────────────────
# Инициализация при старте
# ──────────────────────────────────────────────
def initialize_app() -> None:
    """Инициализирует БД, запускает первый скрапинг и планировщик."""
    logger.info("=== NewsRadar запускается ===")
    init_db()

    # Начальный скрапинг при первом запуске
    from database import get_stats as _stats
    stats = _stats()
    if stats["total"] == 0:
        logger.info("БД пуста — запуск начального скрапинга...")
        try:
            from scraper import scrape_and_save
            count = scrape_and_save()
            logger.info(f"Начальный скрапинг завершён. Загружено: {count} статей")
        except Exception as e:
            logger.error(f"Ошибка начального скрапинга: {e}")

    # Запуск планировщика (обновление каждый час)
    start_scheduler(interval_hours=1)
    atexit.register(stop_scheduler)


# ──────────────────────────────────────────────
# Маршруты
# ──────────────────────────────────────────────

@app.route("/")
def index():
    """
    Главная страница: отображает новости с фильтрацией и поиском.
    Query params:
      ?category=технологии  — фильтр по категории
      ?search=python        — поиск по тексту
    """
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    articles = get_articles(
        category=category or None,
        search=search or None,
        limit=60,
    )
    categories = get_categories()
    stats = get_stats()
    next_update = get_next_run()

    return render_template(
        "index.html",
        articles=articles,
        categories=categories,
        stats=stats,
        current_category=category,
        search_query=search,
        next_update=next_update,
    )


@app.route("/api/articles")
def api_articles():
    """
    REST API endpoint для получения статей в формате JSON.
    Query params: category, search, limit
    """
    category = request.args.get("category", "").strip() or None
    search = request.args.get("search", "").strip() or None
    limit = min(int(request.args.get("limit", 50)), 200)

    articles = get_articles(category=category, search=search, limit=limit)
    return jsonify({"articles": articles, "count": len(articles)})


@app.route("/api/stats")
def api_stats():
    """REST API endpoint: статистика базы данных."""
    return jsonify(get_stats())


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    """
    Ручной запуск скрапинга через API.
    Возвращает количество новых сохранённых статей.
    """
    try:
        from scraper import scrape_and_save
        new_count = scrape_and_save()
        return jsonify({"status": "ok", "new_articles": new_count})
    except Exception as e:
        logger.error(f"Ошибка ручного скрапинга: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/next-update")
def api_next_update():
    """Возвращает время следующего автообновления."""
    return jsonify({"next_update": get_next_run()})


# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
if __name__ == "__main__":
    initialize_app()
    app.run(debug=True, use_reloader=False, port=5000)
