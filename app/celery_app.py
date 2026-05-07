from celery import Celery
from .config import settings

celery_app = Celery(
    "worker", # name of the worker system
    broker= settings.celery_broker, # (redis) where tasks are queued 
    backend= settings.celery_backend # (redis) where results are stored
)

# it is very important without this line celery will not be able to find the tasks and will not work
# Automatically discover and register tasks to avoid circular imports
celery_app.autodiscover_tasks(["app.celery_tasks"])

# command to run celery worker : celery -A app.celery_app.celery_app worker --loglevel=info
