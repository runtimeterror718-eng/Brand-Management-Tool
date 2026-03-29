"""
Celery Beat schedule — which scraper runs when.
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "scrape-youtube-every-6h": {
        "task": "workers.tasks.scrape_platform",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": ("youtube",),
    },
    "scrape-reddit-every-4h": {
        "task": "workers.tasks.scrape_platform",
        "schedule": crontab(minute=0, hour="*/4"),
        "args": ("reddit",),
    },
    "scrape-twitter-every-2h": {
        "task": "workers.tasks.scrape_platform",
        "schedule": crontab(minute=0, hour="*/2"),
        "args": ("twitter",),
    },
    "scrape-instagram-every-6h": {
        "task": "workers.tasks.scrape_platform",
        "schedule": crontab(minute=30, hour="*/6"),
        "args": ("instagram",),
    },
    "scrape-seo-news-every-3h": {
        "task": "workers.tasks.scrape_platform",
        "schedule": crontab(minute=0, hour="*/3"),
        "args": ("seo_news",),
    },
    "scrape-telegram-every-1h": {
        "task": "workers.tasks.scrape_platform",
        "schedule": crontab(minute=15),
        "args": ("telegram",),
    },
    "run-analysis-daily": {
        "task": "workers.tasks.run_full_analysis",
        "schedule": crontab(minute=0, hour=2),  # 2 AM daily
    },
    "check-alerts-every-30m": {
        "task": "workers.tasks.check_alerts",
        "schedule": crontab(minute="*/30"),
    },
    "weekly-email-report": {
        "task": "workers.tasks.send_weekly_report",
        "schedule": crontab(minute=0, hour=9, day_of_week=1),  # Monday 9 AM
    },
}
