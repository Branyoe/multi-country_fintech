#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py loaddata fixtures/users.json || echo "[dev] Fixtures ya cargadas, continuando..."
exec python manage.py runserver 0.0.0.0:8000
