#!/bin/sh
set -e

echo "--- Running migrations ---"
python manage.py migrate --noinput

echo "--- Loading fixtures ---"
python manage.py loaddata fixtures/users.json || echo "Fixtures already loaded or skipped."

echo "--- Starting Gunicorn ---"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
