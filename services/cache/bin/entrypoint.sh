#!/usr/bin/env bash
set -euo pipefail

KAFKA_HOST="${KAFKA_HOST:-kafka1}"
KAFKA_PORT="${KAFKA_PORT:-19092}"

wait_for_service() {
	local host="$1"
	local port="$2"
	local name="$3"
	echo "[INFO] Waiting for $name at $host:$port..."
	while ! nc -z "$host" "$port"; do
		sleep 3
	done
	echo "[INFO] $name is ready!"
}

wait_for_service "$KAFKA_HOST" "$KAFKA_PORT" "Kafka"

echo "[INFO] Launching cache FastAPI service..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8080
