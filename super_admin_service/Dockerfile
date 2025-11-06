# -------------------------------
# 🧑‍💼 Super Admin Dockerfile
# -------------------------------
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn psycopg2-binary kafka-python

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8003

CMD ["sh", "-c", "python manage.py migrate && gunicorn super_admin_service.wsgi:application --bind 0.0.0.0:8003 --workers 3"]
