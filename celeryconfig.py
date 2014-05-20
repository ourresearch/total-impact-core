import os
import sys

sys.path.append('.')

## Broker settings.
BROKER_URL = os.getenv("CLOUDAMQP_URL", "amqp://guest@localhost//")
CELERY_RESULT_BACKEND = "amqp"

CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_ENABLE_UTC=True
CELERY_TASK_RESULT_EXPIRES = 60*60  # 1 hour

# List of modules to import when celery starts.
CELERY_IMPORTS = ("tasks",)

CELERY_ANNOTATIONS = {
    'celery.chord_unlock': {'soft_time_limit': 60*5},  # five minutes
}