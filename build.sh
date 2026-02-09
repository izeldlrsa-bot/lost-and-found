#!/usr/bin/env bash
# Render build script — runs on every deploy
set -o errexit

echo ">>> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Collecting static files..."
python manage.py collectstatic --no-input

echo ">>> Running migrations..."
python manage.py migrate --no-input

echo ">>> Creating superuser (if it doesn't exist)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@lostandfound.dev', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists, skipping.')
"

echo ">>> Build complete!"
