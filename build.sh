#!/usr/bin/env bash
# Render build script — runs on every deploy
set -o errexit

echo ">>> Python: $(python --version)"
echo ">>> DATABASE_URL set: ${DATABASE_URL:+YES}"

echo ">>> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Creating directories..."
mkdir -p staticfiles
mkdir -p media

echo ">>> Collecting static files..."
python manage.py collectstatic --no-input

echo ">>> Running migrations..."
python manage.py migrate --no-input
echo ">>> Migrations complete."

echo ">>> Creating superuser (if not exists)..."
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input \
    --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@lostandfound.dev}" \
    2>/dev/null || echo "Superuser already exists. Skipping."
else
  echo "No DJANGO_SUPERUSER_PASSWORD set. Skipping."
fi

echo ">>> Build complete!"
