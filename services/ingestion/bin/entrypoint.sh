#!/bin/bash
set -e

# Function to wait for a service to become available
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"

    echo "[INFO] Waiting for $service at $host:$port..."
    while ! nc -z "$host" "$port"; do
        echo "[INFO] Still waiting for $service..."
        sleep 5
    done
    echo "[INFO] $service is ready!"
}

# Wait for Kafka to be ready
wait_for_service "kafka1" "19092" "Kafka"

# Start FastAPI app with uvicorn
echo "[INFO] Launching FastAPI app..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000