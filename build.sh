#!/bin/bash
set -o errexit

cd backend
pip install -r requirements.txt
python manage.py migrate --run-syncdb
python manage.py collectstatic --no-input
