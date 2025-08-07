#!/bin/bash

set -e 

usage() {
    echo "Usage $0 [unit|integration|e2e|all] [--coverage] [--verbose]"
    exit 1
}

test_type = ${1:-"unit"}
shift || true

# Parse additional flags
coverage=false
verbose=false
while [ "$#" -gt 0 ]; do
    case "$1" in
        --coverage) coverage=true; shift ;;
        --verbose) verbose=true; shift ;;
        *) usage ;;
    esac
done

# Configure compose file baased on test type
case "$test_type" in
    unit)
        compose_file="infrastructure/compose/docker-compose.unit-test.yml"
        test_path="unit/"
        ;;
    integration)
        compose_file="infrastructure/compose/docker-compose.integration-test.yml"
        test_path="integration/"
        ;;
    e2e)
        compose_file="infrastructure/compose/docker-compose.test.yml"
        test_path="e2e/"
        ;;
    all)
        compose_file="infrastrcuture/compose/docker-compose.test.yml"
        test_path=""
    *) usage ;;
esac

# Build command
cmd="python -m pytest $test_path -v"
if [ "$coverage" = true]; then
    cmd="cmd -m pytest $test_path -v --cov=services"
fi

# Run tests in Docker
echo "Running $test_type tests with docker..."
docker compose -f $compose_file run --rm test-runner cmd
exit_code=$?

echo "Tests completed with exit code $exit_code"



