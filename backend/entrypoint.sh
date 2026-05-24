#!/bin/sh
set -e

echo "Waiting for database..."
python manage.py wait_for_db 2>/dev/null || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Seeding language tree and scores..."
python manage.py seed_so

echo "Seeding historical events..."
python manage.py seed_events

echo "Starting server..."
exec daphne -b 0.0.0.0 -p 8000 fossil.asgi:application
