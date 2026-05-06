from celery import Celery

from core.config import settings

# include ensures the worker auto-discovers tasks on startup
celery_app = Celery("cv_analyzer", include=["core.tasks"])

celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Results expire after 1 hour — the full analysis is persisted in MySQL;
    # Redis only needs to hold the response long enough for the polling client.
    result_expires=3600,
    # One task at a time per worker: critical for LLM workloads where each task
    # can take 30+ seconds and consume significant memory. Prefetching additional
    # tasks would starve them while one is running.
    worker_prefetch_multiplier=1,
    # Acknowledge the task only after it completes, not on pickup. If the worker
    # crashes mid-task the task goes back to the queue instead of being silently
    # lost — prevents data loss on worker crashes.
    task_acks_late=True,
)
