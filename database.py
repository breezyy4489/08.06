"""
database.py — Модуль для работы с SQLite базой данных.
Создаёт таблицу articles, предотвращает дублирование через UNIQUE constraint.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "news.db")


def get_connection() -> sqlite3.Connection:
    """Возвращает соединение с базой данных с row_factory для dict-подобного доступа."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Инициализирует базу данных: создаёт таблицу articles если она не существует.
    UNIQUE constraint на поле url предотвращает дублирование новостей.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            url         TEXT    NOT NULL UNIQUE,
            description TEXT,
            published   TEXT,
            source      TEXT,
            category    TEXT    DEFAULT 'общее',
            sentiment   TEXT    DEFAULT 'нейтральный',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] База данных инициализирована.")


def insert_article(title: str, url: str, description: str,
                   published: str, source: str,
                   category: str = "общее", sentiment: str = "нейтральный") -> bool:
    """
    Вставляет статью в базу данных.
    Возвращает True если вставка прошла успешно, False если статья уже существует.

    Args:
        title:       Заголовок статьи
        url:         Ссылка на оригинал (уникальный ключ)
        description: Краткое описание / лид
        published:   Дата публикации
        source:      Название источника
        category:    ML-категория (спорт / политика / технологии / ...)
        sentiment:   Эмоциональная окраска (позитивный / негативный / нейтральный)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO articles (title, url, description, published, source, category, sentiment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, url, description, published, source, category, sentiment))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Статья уже существует (UNIQUE constraint на url)
        return False
    finally:
        conn.close()


def get_articles(category: str = None, search: str = None,
                 limit: int = 100) -> list:
    """
    Получает статьи из БД с опциональной фильтрацией.

    Args:
        category: Фильтр по категории (None = все категории)
        search:   Поиск по заголовку и описанию
        limit:    Максимальное количество записей
    Returns:
        Список словарей с данными статей
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if category and category != "все":
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_categories() -> list:
    """Возвращает список всех уникальных категорий из БД."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM articles ORDER BY category")
    rows = cursor.fetchall()
    conn.close()
    return [row["category"] for row in rows]


def get_stats() -> dict:
    """Возвращает статистику по базе данных."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM articles")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT source, COUNT(*) as cnt FROM articles GROUP BY source")
    by_source = {row["source"]: row["cnt"] for row in cursor.fetchall()}
    cursor.execute("SELECT category, COUNT(*) as cnt FROM articles GROUP BY category")
    by_category = {row["category"]: row["cnt"] for row in cursor.fetchall()}
    conn.close()
    return {"total": total, "by_source": by_source, "by_category": by_category}
