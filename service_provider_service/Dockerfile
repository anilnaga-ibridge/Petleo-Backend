# -------------------------------
# 🐍 Service Provider Dockerfile
# -------------------------------
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn psycopg2-binary kafka-python

COPY . /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8002

CMD ["sh", "-c", "python manage.py migrate && gunicorn service_provider_service.wsgi:application --bind 0.0.0.0:8002 --workers 3"]
