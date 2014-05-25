web: gunicorn totalimpact:app -b 0.0.0.0:$PORT -w 3
celery: celery worker --concurrency=$CELERY_CONCURRENCY --loglevel=info --config=celeryconfig --events
