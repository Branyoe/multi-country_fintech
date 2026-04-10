#!/bin/sh
set -e

echo "--- Running migrations ---"
python manage.py migrate --noinput

echo "--- Loading fixtures ---"
python manage.py loaddata fixtures/users.json || echo "Fixtures already loaded or skipped."
python manage.py loaddata fixtures/countries.json || echo "Countries already loaded or skipped."
python manage.py loaddata fixtures/statuses.json || echo "Statuses already loaded or skipped."

echo "--- Collecting static files ---"
python manage.py collectstatic --noinput

echo "--- Starting Daphne (ASGI) ---"
exec daphne -b 0.0.0.0 -p 8000 config.asgi:application
