from celery import Celery
from app.config.settings import REDIS_URL, ENV

celery_app = Celery(
    "ai_receptionist",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Basic Celery configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="ai_receptionist_default",
    task_routes={
        "app.tasks.*": {"queue": "ai_receptionist_default"},
    },
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Ensure all task modules inside app.tasks are imported so workers register them
celery_app.autodiscover_tasks(['app'])

# Explicit import to guarantee registration when autodiscover fails in some environments.
import app.tasks.scrape_tasks  # noqa: F401

# Helpful for local dev
if ENV == "development":
    celery_app.conf.update(task_always_eager=False)
