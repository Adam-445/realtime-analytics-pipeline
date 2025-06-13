#!/bin/bash
set -e

# Wait for Kafka to be ready
echo "[INFO] Waiting for Kafka..."
while ! nc -z kafka1 19092; do
  sleep 1
done

# Create Kafka Topic
echo "[INFO] Creating Kafka topic..."
python -m ingestion.admin

# Start FastAPI
echo "[INFO] Launching FastAPI…"
exec uvicorn ingestion.main:app \
  --host 0.0.0.0 \
  --port 8000