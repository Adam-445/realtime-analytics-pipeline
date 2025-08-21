#!/usr/bin/env bash
set -euo pipefail

PROM_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prom}"
KAFKA_HOST="${KAFKA_HOST:-kafka1}"
KAFKA_PORT="${KAFKA_PORT:-19092}"

info() { echo "[INFO] $*"; }
err()  { echo "[ERROR] $*" 1>&2; }

# create prometheus multiproc dir and set permissions so worker processes can write
mkdir -p "$PROM_DIR"
chmod 0777 "$PROM_DIR" || true
info "Ensured PROMETHEUS_MULTIPROC_DIR exists at $PROM_DIR (mode 0777)"

# empty dir contents
if [ -d "$PROM_DIR" ]; then
  # remove files/dirs inside, but not the directory itself
  info "Clearing contents of $PROM_DIR"
  find "$PROM_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} \; || true
fi

wait_for_service() {
  local host="$1"
  local port="$2"
  local service="$3"

  info "Waiting for $service at $host:$port..."
  while ! nc -z "$host" "$port"; do
    sleep 2
  done
  info "$service is ready!"
}

wait_for_service "${KAFKA_HOST}" "${KAFKA_PORT}" "Kafka"

# Start uvicorn; exec so PID 1 is uvicorn and receives signals
info "Launching FastAPI app with uvicorn..."
exec uvicorn src.main:app \
  --workers 5 \
  --host 0.0.0.0 \
  --port 8000 \
  --loop uvloop \
  --http httptools \
  --backlog 2048 \
  --timeout-keep-alive 10 \
  --no-access-log
