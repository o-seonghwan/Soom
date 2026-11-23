FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/backend/requirements.txt /app/app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/app/backend/requirements.txt

COPY app/backend/ /app/app/backend/
COPY app/frontend/public/gangnam_boundary.geojson /app/app/frontend/public/gangnam_boundary.geojson

RUN mkdir -p /app/data/processed/walking_network

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn serve:app --app-dir app/backend --host 0.0.0.0 --port ${PORT:-8000}"]
