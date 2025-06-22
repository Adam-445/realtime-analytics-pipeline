#!/bin/bash
set -e

wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    
    echo "[INFO] Waiting for $service to be ready..."
    while ! nc -z $host $port; do
        sleep 5
    done
    echo "[INFO] $service is ready!"
}

wait_for_service kafka1 19092 "Kafka"
wait_for_service jobmanager 8081 "JobManager"

# Additional buffer for JobManager initialization
sleep 10

echo "[INFO] Submitting Flink job..."
flink run \
    --jobmanager jobmanager:8081 \
    --python /app/src/jobs/metric_aggregator.py