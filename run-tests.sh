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

# Configure pytest arguments
PYTEST_ARGS=""
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=term-missing"
fi

function run_unit_tests() {
    echo "Running unit tests in service containers..."
    
    # Build test images
    echo "Building test images..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile unit-tests \
        build $BUILD_FLAGS ingestion processing
    
    echo "================================================================================"
    echo "Running ingestion service unit tests..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile unit-tests \
        run --rm ingestion python -m pytest tests/unit $PYTEST_ARGS
    
    echo "================================================================================"
    echo "Running processing service unit tests..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile unit-tests \
        run --rm processing python -m pytest tests/unit $PYTEST_ARGS
}

function run_integration_tests() {
    echo "Running integration tests..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile integration-tests \
        build $BUILD_FLAGS test-runner
    
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile integration-tests \
        run --rm test-runner bash -c "cd /tests && python -m pytest integration $PYTEST_ARGS"
}

function run_e2e_tests() {
    echo "Running end-to-end tests..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile e2e-tests \
        build $BUILD_FLAGS test-runner
    
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile e2e-tests \
        run --rm test-runner bash -c "cd /tests && python -m pytest e2e $PYTEST_ARGS"
}

function run_performance_tests() {
    echo "Running performance tests..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile e2e-tests \
        build $BUILD_FLAGS test-runner
    
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        --profile e2e-tests \
        run --rm test-runner bash -c "cd /tests && python -m pytest performance $PYTEST_ARGS"
}

function cleanup() {
    echo "Cleaning up test environment..."
    docker compose \
        -f infrastructure/compose/docker-compose.yml \
        -f infrastructure/compose/docker-compose.test.yml \
        --env-file infrastructure/compose/.env.test \
        down -v 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

# Create coverage-reports directory if it doesn't exist
mkdir -p coverage-reports

# Run tests based on type
case $TEST_TYPE in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    e2e)
        run_e2e_tests
        ;;
    performance)
        run_performance_tests
        ;;
    all)
        run_unit_tests
        echo ""
        run_integration_tests
        echo ""
        run_e2e_tests
        ;;
esac

echo "Tests completed successfully!"