#!/usr/bin/env bash
set -e

# --- Frontend ---
cd frontend
npm ci
npm run build
cd ..

# --- Backend ---
pip install -r backend/requirements.txt
cd backend
python manage.py collectstatic --noinput
python manage.py migrate
cd ..
