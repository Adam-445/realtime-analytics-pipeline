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
wait_for_service jobmanager 8081 "JobManager"

# Additional buffer for JobManager initialization
sleep 5

echo "[INFO] Submitting Flink job..."
flink run \
    --jobmanager jobmanager:8081 \
    --python /app/src/main.py