#!/bin/bash

set -e

echo "Running unit tests in Docker container..."

# Navigate to the project root
cd "$(dirname "$0")"

# Run unit tests using Docker Compose
docker compose -f infrastructure/compose/docker-compose.unit-test.yml up --build --abort-on-container-exit

# Clean up
docker compose -f infrastructure/compose/docker-compose.unit-test.yml down

echo "Unit tests completed."
