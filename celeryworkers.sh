#!/bin/bash
for ((i=1; i<=$CELERY_MULTI_WORKERS; i++))
do
  COMMAND="celery worker -n celeryworker${i} --loglevel=info --config=celeryconfig --events --concurrency=$CELERY_CONCURRENCY"
  echo $COMMAND
  $COMMAND&
done
trap "kill 0" SIGINT SIGTERM EXIT
wait
