#!/usr/bin/env bash
# Render build script — runs on every deploy
set -o errexit

echo ">>> Python: $(python --version)"
echo ">>> DATABASE_URL set: ${DATABASE_URL:+YES}"

echo ">>> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ">>> Creating staticfiles dir..."
mkdir -p staticfiles

echo ">>> Collecting static files..."
python manage.py collectstatic --no-input

echo ">>> Running migrations..."
python manage.py migrate --no-input
echo ">>> Migrations complete."

echo ">>> Creating superuser (if not exists)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
import os
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@lostandfound.dev')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
if password and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser {username} created.')
else:
    print('Superuser already exists or no password set. Skipping.')
"

echo ">>> Build complete!"
