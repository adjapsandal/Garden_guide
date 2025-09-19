# Dockerfile (dev-focused)
FROM python:3.11-slim

# системные зависимости, полезные для psycopg2 и pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# копируем только requirements для кеширования слоёв
COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# копируем всё приложение (копирование нужно, т.к. docker-compose может затем замонтировать том сверху)
COPY . /app

# экспортируем порт Flask (по умолчанию 5000 в main.py)
EXPOSE 5000

# Для разработки — используем встроенный flask server.
# При желании заменим на gunicorn в продакшене.
ENV FLASK_APP=main.py
ENV FLASK_ENV=development
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
