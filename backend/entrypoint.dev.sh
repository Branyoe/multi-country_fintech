#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py loaddata fixtures/users.json || echo "[dev] Users ya cargadas, continuando..."
python manage.py loaddata fixtures/countries.json || echo "[dev] Countries ya cargados, continuando..."
python manage.py loaddata fixtures/statuses.json || echo "[dev] Statuses ya cargados, continuando..."
exec python manage.py runserver 0.0.0.0:8000
