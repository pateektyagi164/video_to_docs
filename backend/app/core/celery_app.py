from celery import Celery

# Connect to the Redis container on your laptop's local port
REDIS_URL = "redis://localhost:6379/0"

celery_app = Celery(
    "ai_extractor_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks"]
)

# Standard industry configuration for data serialization
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)