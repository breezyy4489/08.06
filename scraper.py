"""
scraper.py — Модуль скрапинга новостей.
Получает новости из RSS-лент и HTML-страниц трёх источников:
  1. Lenta.ru     (RSS)
  2. RBC.ru       (RSS)
  3. Habr.com     (RSS — технологии)

Использует feedparser для RSS и BeautifulSoup для HTML-парсинга.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging

logging.basicConfig(level=logging.INFO, format="[SCRAPER] %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Конфигурация источников
# ──────────────────────────────────────────────
SOURCES = [
    {
        "name": "Lenta.ru",
        "rss": "https://lenta.ru/rss/news",
        "type": "rss",
    },
    {
        "name": "RBC",
        "rss": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        "type": "rss",
    },
    {
        "name": "Habr",
        "rss": "https://habr.com/ru/rss/articles/",
        "type": "rss",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def clean_html(text: str) -> str:
    """
    Очищает текст от HTML-тегов и лишних пробелов.

    Args:
        text: Исходный текст с возможными HTML-тегами
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text().split())


def parse_date(entry) -> str:
    """
    Извлекает дату публикации из feedparser entry.
    Возвращает строку ISO-формата или текущую дату если дата отсутствует.
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6])
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def scrape_rss(source: dict) -> list[dict]:
    """
    Парсит RSS-ленту источника через feedparser.

    Args:
        source: Словарь с полями name и rss
    Returns:
        Список статей в формате {title, url, description, published, source}
    """
    articles = []
    logger.info(f"Скрапинг RSS: {source['name']} ({source['rss']})")

    try:
        feed = feedparser.parse(source["rss"])
        if feed.bozo:
            logger.warning(f"RSS предупреждение для {source['name']}: {feed.bozo_exception}")

        for entry in feed.entries:
            title = clean_html(getattr(entry, "title", ""))
            url = getattr(entry, "link", "")
            description = clean_html(
                getattr(entry, "summary", "") or
                getattr(entry, "description", "")
            )
            published = parse_date(entry)

            if title and url:
                articles.append({
                    "title": title,
                    "url": url,
                    "description": description[:500],  # Ограничиваем длину
                    "published": published,
                    "source": source["name"],
                })

        logger.info(f"  → Получено {len(articles)} статей из {source['name']}")

    except Exception as e:
        logger.error(f"Ошибка при скрапинге {source['name']}: {e}")

    return articles


def scrape_html_fallback(url: str, source_name: str) -> list[dict]:
    """
    Резервный HTML-парсинг страницы через BeautifulSoup если RSS недоступен.

    Args:
        url:         URL страницы для парсинга
        source_name: Название источника
    Returns:
        Список найденных статей
    """
    articles = []
    logger.info(f"HTML-парсинг: {source_name} ({url})")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем заголовки новостей — стандартные HTML-паттерны
        for tag in soup.find_all(["h2", "h3"], limit=30):
            link_tag = tag.find("a", href=True)
            if link_tag:
                title = clean_html(link_tag.get_text())
                href = link_tag["href"]
                if not href.startswith("http"):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                if title and len(title) > 10:
                    articles.append({
                        "title": title,
                        "url": href,
                        "description": "",
                        "published": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source": source_name,
                    })

        logger.info(f"  → HTML fallback: {len(articles)} статей из {source_name}")

    except Exception as e:
        logger.error(f"Ошибка HTML-парсинга {source_name}: {e}")

    return articles


def scrape_all() -> list[dict]:
    """
    Главная функция скрапинга: обходит все источники из SOURCES.

    Returns:
        Объединённый список всех статей со всех источников
    """
    all_articles = []

    for source in SOURCES:
        try:
            if source["type"] == "rss":
                articles = scrape_rss(source)
                # Если RSS не дал результатов — пробуем HTML fallback
                if not articles and "fallback_url" in source:
                    articles = scrape_html_fallback(
                        source["fallback_url"], source["name"]
                    )
            else:
                articles = scrape_html_fallback(source["rss"], source["name"])

            all_articles.extend(articles)
            time.sleep(1)  # Пауза между запросами — вежливый скрапинг

        except Exception as e:
            logger.error(f"Критическая ошибка при обработке {source['name']}: {e}")

    logger.info(f"Итого собрано статей: {len(all_articles)}")
    return all_articles


def scrape_and_save() -> int:
    """
    Полный цикл: скрапинг всех источников + сохранение в БД.
    Возвращает количество новых (уникальных) сохранённых статей.
    """
    from database import insert_article
    from classifier import classify_article, get_sentiment

    articles = scrape_all()
    new_count = 0

    for article in articles:
        # ML-классификация перед сохранением
        text = f"{article['title']} {article['description']}"
        category = classify_article(text)
        sentiment = get_sentiment(text)

        saved = insert_article(
            title=article["title"],
            url=article["url"],
            description=article["description"],
            published=article["published"],
            source=article["source"],
            category=category,
            sentiment=sentiment,
        )
        if saved:
            new_count += 1

    logger.info(f"Сохранено новых статей: {new_count} из {len(articles)}")
    return new_count


if __name__ == "__main__":
    # Тестовый запуск скрапера
    from database import init_db
    init_db()
    count = scrape_and_save()
    print(f"\nГотово! Добавлено новых статей: {count}")
