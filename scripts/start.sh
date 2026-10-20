#!/bin/sh
# Production entrypoint: collect static files, apply migrations, start gunicorn.
# Used by Dockerfile, Procfile and platform start commands.
set -eu

: "${DJANGO_SETTINGS_MODULE:=crelume.settings.prod}"
: "${PORT:=8000}"
: "${WEB_CONCURRENCY:=3}"
export DJANGO_SETTINGS_MODULE

python manage.py collectstatic --noinput
python manage.py migrate --noinput

exec gunicorn crelume.wsgi:application \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
