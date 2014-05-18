import os
import sys

sys.path.append('.')

## Broker settings.
BROKER_URL = os.getenv("CLOUDAMQP_URL", "amqp://guest@localhost//")
CELERY_RESULT_BACKEND = "amqp"

CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_ENABLE_UTC=True
CELERY_TASK_RESULT_EXPIRES = 18000  # 5 hours

# List of modules to import when celery starts.
CELERY_IMPORTS = ("tasks",)
