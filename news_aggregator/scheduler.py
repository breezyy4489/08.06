"""
scheduler.py — Модуль автоматического обновления новостей через APScheduler.

Запускает scrape_and_save() каждый час в фоновом потоке.
Совместим с Flask (запускается при старте приложения).
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Глобальный экземпляр планировщика
scheduler = BackgroundScheduler()


def scheduled_scrape() -> None:
    """
    Задача планировщика: запускает полный цикл скрапинга.
    Вызывается автоматически по расписанию.
    """
    logger.info("[SCHEDULER] Запуск автоматического обновления новостей...")
    try:
        from scraper import scrape_and_save
        new_count = scrape_and_save()
        logger.info(f"[SCHEDULER] Обновление завершено. Новых статей: {new_count}")
    except Exception as e:
        logger.error(f"[SCHEDULER] Ошибка при обновлении: {e}")


def start_scheduler(interval_hours: int = 1) -> None:
    """
    Запускает фоновый планировщик.

    Args:
        interval_hours: Интервал обновления в часах (по умолчанию 1 час)
    """
    if scheduler.running:
        logger.info("[SCHEDULER] Планировщик уже запущен.")
        return

    scheduler.add_job(
        func=scheduled_scrape,
        trigger=IntervalTrigger(hours=interval_hours),
        id="news_scrape",
        name="Автообновление новостей",
        replace_existing=True,
        max_instances=1,        # Не запускать параллельно
        coalesce=True,          # Пропускать пропущенные запуски
    )

    scheduler.start()
    logger.info(
        f"[SCHEDULER] Запущен. Обновление каждые {interval_hours} ч. "
        f"Следующий запуск: {scheduler.get_job('news_scrape').next_run_time}"
    )


def stop_scheduler() -> None:
    """Останавливает планировщик (вызывается при завершении Flask)."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[SCHEDULER] Остановлен.")


def get_next_run() -> str:
    """Возвращает время следующего запуска в читаемом формате."""
    try:
        job = scheduler.get_job("news_scrape")
        if job and job.next_run_time:
            return job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return "не запланировано"
