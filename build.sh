#!/usr/bin/env bash
set -o errexit

export PYTHONUNBUFFERED=1

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary uv

if [[ "${APP_ENV:-}" == "production" || "${APP_ENV:-}" == "prod" || "${APP_ENV:-}" == "live" ]]; then
  if [[ "${DEBUG:-}" != "False" ]]; then
    echo "ERROR: DEBUG must be False in production." >&2
    exit 1
  fi
  if [[ -z "${SECRET_KEY:-}" || "${SECRET_KEY:-}" == *"django-insecure"* ]]; then
    echo "ERROR: SECRET_KEY is missing or insecure for production." >&2
    exit 1
  fi
  if [[ -z "${FIELD_ENCRYPTION_KEY:-}" ]]; then
    echo "ERROR: FIELD_ENCRYPTION_KEY is required in production." >&2
    exit 1
  fi
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "ERROR: DATABASE_URL is required in production." >&2
    exit 1
  fi
  if [[ -z "${ALLOWED_HOSTS:-}" || "${ALLOWED_HOSTS:-}" == "*" ]]; then
    echo "ERROR: ALLOWED_HOSTS must be set to real production hosts only." >&2
    exit 1
  fi
  if [[ -z "${CSRF_TRUSTED_ORIGINS:-}" ]]; then
    echo "ERROR: CSRF_TRUSTED_ORIGINS is required in production." >&2
    exit 1
  fi
fi

python manage.py validate_production

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

python manage.py collectstatic --no-input
python manage.py migrate --noinput
