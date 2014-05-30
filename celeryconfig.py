import os
import sys
import urlparse
from kombu import Exchange, Queue

sys.path.append('.')

redis_url = os.environ.get('REDIS_URL', "redis://localhost:6379/")
if not redis_url.endswith("/"):
    redis_url += "/"

BROKER_URL = redis_url + "1"
CELERY_RESULT_BACKEND = redis_url + "1"
REDIS_CONNECT_RETRY = True


# these options will be defaults in future as per http://celery.readthedocs.org/en/latest/getting-started/brokers/redis.html
BROKER_TRANSPORT_OPTIONS = {'fanout_prefix': True}
BROKER_TRANSPORT_OPTIONS = {'fanout_patterns': True}

CELERY_DEFAULT_QUEUE = 'core_main'
CELERY_QUEUES = [
    Queue('core_main', routing_key='core_main'),
    Queue('refresh_tiid', routing_key='refresh_tiid'),
    Queue('provider_run', routing_key='provider_run'),
]

BROKER_TRANSPORT_OPTIONS = {
    'priority_steps': [0,9],
}

CELERY_CREATE_MISSING_QUEUES = True

CELERY_ROUTES = {
    'tasks.refresh_tiid': {'queue': 'refresh_tiid'},
    'tasks.provider_run': {'queue': 'provider_run'},
}

CELERY_ACCEPT_CONTENT = ['pickle', 'json']
CELERY_ENABLE_UTC=True
CELERY_TASK_RESULT_EXPIRES = 60*60  # 1 hour
CELERYD_MAX_TASKS_PER_CHILD = 1000
CELERYD_FORCE_EXECV = True
CELERY_TRACK_STARTED = True

# List of modules to import when celery starts.
CELERY_IMPORTS = ("tasks",)

CELERY_ANNOTATIONS = {
    'celery.chord_unlock': {'soft_time_limit': 60*60*8},  # 8 hours
}
