#!/bin/bash

set -e

function print_usage() {
    echo "Usage: $0 [OPTIONS] [TEST_TYPE]"
    echo "Run tests for the real-time analytics pipeline"
    echo ""
    echo "Options:"
    echo "  --coverage          Generate coverage report"
    echo "  --no-cache          Rebuild Docker images"
    echo "  -v, --verbose       Verbose output"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Test types:"
    echo "  unit                Run unit tests (default)"
    echo "  integration         Run integration tests"
    echo "  e2e                 Run end-to-end tests"
    echo "  performance         Run performance tests"
    echo "  all                 Run all tests"
    echo ""
    echo "Examples:"
    echo "  $0 unit             # Run unit tests"
    echo "  $0 --coverage all   # Run all tests with coverage"
}

# Default values
TEST_TYPE="unit"
COVERAGE=false
VERBOSE=false
BUILD_FLAGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        unit|integration|e2e|performance|all)
            TEST_TYPE=$1
            ;;
        --coverage)
            COVERAGE=true
            ;;
        --no-cache)
            BUILD_FLAGS="--no-cache"
            ;;
        -v|--verbose)
            VERBOSE=true
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
    shift
done

# Configure test command based on test type and options
PYTEST_ARGS=""
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=services --cov-report=xml:/app/coverage-reports/coverage.xml --cov-report=html:/app/coverage-reports/html"
fi

case $TEST_TYPE in
    unit)
        echo "Running unit tests..."
        TEST_CMD="cd /app/services/ingestion && PYTHONPATH=/app/services/ingestion/src:/app/services/processing/src:/app/services/storage/src python -m pytest tests/unit $PYTEST_ARGS"
        ;;
    integration)
        echo "Running integration tests..."
        TEST_CMD="cd /tests && PYTHONPATH=/app/services/ingestion/src:/app/services/processing/src:/app/services/storage/src:/tests python -m pytest integration $PYTEST_ARGS"
        ;;
    e2e)
        echo "Running end-to-end tests..."
        TEST_CMD="cd /tests && PYTHONPATH=/app/services/ingestion/src:/app/services/processing/src:/app/services/storage/src:/tests python -m pytest e2e $PYTEST_ARGS"
        ;;
    performance)
        echo "Running performance tests..."
        TEST_CMD="cd /tests && PYTHONPATH=/app/services/ingestion/src:/app/services/processing/src:/app/services/storage/src:/tests python -m pytest performance $PYTEST_ARGS"
        ;;
    all)
        echo "Running all tests..."
        TEST_CMD="cd /app/services/ingestion && PYTHONPATH=/app/services/ingestion/src:/app/services/processing/src:/app/services/storage/src python -m pytest tests/unit $PYTEST_ARGS && cd /tests && PYTHONPATH=/app/services/ingestion/src:/app/services/processing/src:/app/services/storage/src:/tests python -m pytest integration e2e $PYTEST_ARGS"
        ;;
esac

# Create coverage-reports directory if it doesn't exist
mkdir -p coverage-reports

# Run tests in Docker
echo "Starting test environment..."
docker compose \
    -f infrastructure/compose/docker-compose.yml \
    -f infrastructure/compose/docker-compose.test.yml \
    --env-file infrastructure/compose/.env.test \
    build $BUILD_FLAGS test-runner

docker compose \
    -f infrastructure/compose/docker-compose.yml \
    -f infrastructure/compose/docker-compose.test.yml \
    --env-file infrastructure/compose/.env.test \
    run --rm test-runner bash -c "$TEST_CMD"

EXIT_CODE=$?
echo "Tests completed with exit code $EXIT_CODE"
docker compose \
    -f infrastructure/compose/docker-compose.yml \
    -f infrastructure/compose/docker-compose.test.yml \
    --env-file infrastructure/compose/.env.test \
    down -v
exit $EXIT_CODE