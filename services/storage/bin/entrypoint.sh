#!/bin/bash
set -e

# Function to wait for a service to become available
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"

    echo "[INFO] Waiting for $service at $host:$port..."
    while ! nc -z "$host" "$port"; do
        sleep 5
    done
    echo "[INFO] $service is ready!"
}

wait_for_service kafka1 19092 "Kafka"

python -m src.batch_processor