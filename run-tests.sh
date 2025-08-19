#!/bin/bash

set -euo pipefail

# --- Configuration & Constatnts ---

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"

# Valid services (single source of truth)
readonly VALID_SERVICES=(cache ingestion processing storage)
readonly DEFAULT_SERVICES=(cache ingestion processing storage)

# Docker compose configuration
readonly COMPOSE_FILES="-f infrastructure/compose/docker-compose.yml -f infrastructure/compose/docker-compose.test.yml"
readonly ENV_FILE="--env-file infrastructure/compose/.env.test"

# Test output formatting
readonly COLOR_RED='\033[0;31m'
readonly COLOR_GREEN='\033[0;32m'
readonly COLOR_YELLOW='\033[1;33m'
readonly COLOR_BLUE='\033[0;34m'
readonly COLOR_RESET='\033[0m'

# --- Logging & Output functions ---

log_info() {
    echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $*"
}

log_success() {
    echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $*"
}

log_warning() {
    echo -e "${COLOR_YELLOW}[WARNING]${COLOR_RESET} $*"
}

log_error() {
    echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*" >&2
}

print_separator() {
    echo "================================================================================"
}

print_test_header() {
    local service="$1"
    print_separator
    log_info "Running $service service unit tests..."
}

# --- Validation functions ----
validate_service() {
    local service="$1"

    if [[ -z "$service" ]]; then
        return 0 # Empty service is valid
    fi

    for valid_service in "${VALID_SERVICES[@]}"; do
        if [[ "$service" == "$valid_service" ]]; then
            return 0
        fi
    done

    log_error "Invalid service '$service'. Valid services: ${VALID_SERVICES[*]}"
    return 1
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        return 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        return 1
    fi
    
    if [[ ! -f "infrastructure/compose/docker-compose.yml" ]]; then
        log_error "Docker compose file not found. Are you in the project root?"
        return 1
    fi
    
    log_success "Prerequisites check passed"
}

validate_environment() {
    local service="$1"
    
    validate_service "$service" || return 1
    check_prerequisites || return 1
    
    return 0
}

# --- Coverage config ---

setup_coverage_directories() {
    local services=("$@")
    
    log_info "Setting up coverage directories..."
    
    # Create base coverage directory
    mkdir -p coverage-reports
    
    # Create service-specific directories
    for service in "${services[@]}"; do
        mkdir -p "coverage-reports/$service"
        log_info "Created coverage directory for $service"
    done
}

get_coverage_args() {
    local service="$1"
    
    if [[ "$COVERAGE" != true ]]; then
        echo ""
        return
    fi
    
    local base_args="--cov=src --cov-report=term-missing"
    local html_report="--cov-report=html:coverage-reports/$service/htmlcov"
    local xml_report="--cov-report=xml:coverage-reports/$service/coverage.xml"
    
    echo "$base_args $html_report $xml_report"
}

get_volume_mounts() {
    local service="$1"
    
    if [[ "$COVERAGE" != true ]]; then
        echo ""
        return
    fi
    
    local host_path="$(pwd)/coverage-reports/$service"
    local container_path="/app/coverage-reports/$service"
    
    echo "-v $host_path:$container_path"
}

# --- Service Management ---

determine_services_to_test() {
    local service="$1"
    
    if [[ -n "$service" ]]; then
        echo "$service"
    else
        echo "${DEFAULT_SERVICES[*]}"
    fi
}

build_service_images() {
    local services=("$@")
    
    log_info "Building test images for services: ${services[*]}"
    
    if ! docker compose $COMPOSE_FILES $ENV_FILE build $BUILD_FLAGS "${services[@]}"; then
        log_error "Failed to build service images"
        return 1
    fi
    
    log_success "Service images built successfully"
}

# --- Test Execution ---

run_single_service_test() {
    local service="$1"
    local pytest_args="$2"
    
    print_test_header "$service"
    
    # Prepare Docker command components
    local volume_mounts
    volume_mounts=$(get_volume_mounts "$service")
    
    local docker_cmd="docker compose $COMPOSE_FILES $ENV_FILE run --rm"
    
    # Add volume mounts if coverage is enabled
    if [[ -n "$volume_mounts" ]]; then
        docker_cmd="$docker_cmd $volume_mounts"
    fi
    
    # Add service and test command
    docker_cmd="$docker_cmd $service python -m pytest tests/unit $pytest_args"
    
    # Execute the test
    if eval "$docker_cmd"; then
        log_success "Tests passed for $service service"
        return 0
    else
        log_error "Tests failed for $service service"
        return 1
    fi
}

run_unit_tests() {
    log_info "Starting unit test execution..."

    # Determine which services to test
    local services_string
    services_string=$(determine_services_to_test "$SERVICE")
    read -ra SERVICES <<< "$services_string"

    if [[ ${#SERVICES[@]} -eq 1 && -n "$SERVICE" ]]; then
        log_info "Running tests for service: $SERVICE"
    else
        log_info "Running tests for all service: ${SERVICES[*]}"
    fi

    # Setup coverage if enabled
    if [[ "$COVERAGE" == true ]]; then
        setup_coverage_directories "${SERVICES[@]}"
    fi

    # Build service images
    build_service_images "${SERVICES[@]}" || return 1

    # Run tests for each service
    local failed_services=()

    for service in "${SERVICES[@]}"; do
        local coverage_args
        coverage_args=$(get_coverage_args "$service")
        local pytest_args="$PYTEST_ARGS $coverage_args"

        if ! run_single_service_test "$service" "$pytest_args"; then
            failed_services+=("$service")
        fi
    done

    # Report results
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        log_error "Tests failed for services: ${failed_services[*]}"
        return 1
    fi

    log_success "All unit tests completed successfully"
    return 0
}

run_integration_tests() {
    log_info "Running integration tests..."
    
    if ! docker compose $COMPOSE_FILES $ENV_FILE build $BUILD_FLAGS test-runner; then
        log_error "Failed to build test-runner image"
        return 1
    fi
    
    if ! docker compose $COMPOSE_FILES $ENV_FILE run --rm test-runner bash -c "cd /tests && python -m pytest integration $PYTEST_ARGS"; then
        log_error "Integration tests failed"
        return 1
    fi
    
    log_success "Integration tests completed successfully!"
}

run_e2e_tests() {
    log_info "Running end-to-end tests..."
    
    if ! docker compose $COMPOSE_FILES $ENV_FILE build $BUILD_FLAGS; then
        log_error "Failed to build images for e2e tests"
        return 1
    fi
    
    if ! docker compose $COMPOSE_FILES $ENV_FILE run --rm test-runner bash -c "cd /tests && python -m pytest e2e $PYTEST_ARGS"; then
        log_error "End-to-end tests failed"
        return 1
    fi
    
    log_success "End-to-end tests completed successfully!"
}

run_performance_tests() {
    log_info "Running performance tests..."
    
    # Build all images to pick up latest code for services used in perf runs
    if ! docker compose $COMPOSE_FILES $ENV_FILE build $BUILD_FLAGS; then
        log_error "Failed to build images for performance tests"
        return 1
    fi
    
    # Determine scenario target
    local target_path="performance"
    case "${PERF_SCENARIO:-all}" in
        throughput)
            target_path="performance/test_throughput.py"
            ;;
        latency)
            target_path="performance/test_latency.py"
            ;;
        all|*)
            target_path="performance"
            ;;
    esac

    # Prepare env vars for perf config
    local perf_env=""
    [[ -n "${PERF_RATES:-}" ]] && perf_env+=" -e PERF_RATES=${PERF_RATES}"
    [[ -n "${PERF_DURATION:-}" ]] && perf_env+=" -e PERF_DURATION=${PERF_DURATION}"
    [[ -n "${PERF_WARMUP:-}" ]] && perf_env+=" -e PERF_WARMUP=${PERF_WARMUP}"
    # Ensure event type used by load generator is passed through
    [[ -n "${PERF_EVENT_TYPE:-}" ]] && perf_env+=" -e PERF_EVENT_TYPE=${PERF_EVENT_TYPE}"
    [[ -n "${PERF_LATENCY_MAX:-}" ]] && perf_env+=" -e PERF_LATENCY_MAX=${PERF_LATENCY_MAX}"
    [[ -n "${PERF_MODE:-}" ]] && perf_env+=" -e PERF_MODE=${PERF_MODE}"
    [[ -n "${PERF_STRICT:-}" ]] && perf_env+=" -e PERF_STRICT=${PERF_STRICT}"
    [[ -n "${PERF_CONCURRENCY:-}" ]] && perf_env+=" -e PERF_CONCURRENCY=${PERF_CONCURRENCY}"
    # Endpoint overrides for local/remote targets
    [[ -n "${PERF_TRACK_URL:-}" ]] && perf_env+=" -e PERF_TRACK_URL=${PERF_TRACK_URL}"
    [[ -n "${PERF_CACHE_URL:-}" ]] && perf_env+=" -e PERF_CACHE_URL=${PERF_CACHE_URL}"
    [[ -n "${PROMETHEUS_URL:-}" ]] && perf_env+=" -e PROMETHEUS_URL=${PROMETHEUS_URL}"
    # Git metadata for reporting
    local git_commit
    local git_branch
    git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    perf_env+=" -e GIT_COMMIT=${git_commit} -e GIT_BRANCH=${git_branch} -e PERF_SCENARIO=${PERF_SCENARIO:-all}"

    # Default loadgen concurrency if not provided (roughly 25 req/s per worker)
    if [[ -z "${PERF_CONCURRENCY:-}" && -n "${PERF_RATES:-}" ]]; then
        local first_rate
        first_rate=$(echo "${PERF_RATES:-}" | awk -F',' '{print $1}')
        if [[ -n "$first_rate" ]]; then
            local calc_workers
            calc_workers=$(( (first_rate + 24) / 25 ))
            if [[ "$calc_workers" -gt 400 ]]; then calc_workers=400; fi
            perf_env+=" -e PERF_CONCURRENCY=${calc_workers}"
        fi
    fi

    if ! docker compose $COMPOSE_FILES $ENV_FILE run --rm $perf_env test-runner bash -c "cd /tests && python -m pytest ${target_path} $PYTEST_ARGS"; then
        log_error "Performance tests failed"
        return 1
    fi
    
    log_success "Performance tests completed successfully!"
}

# --- Cleanup and utilites ---

cleanup() {
    log_info "Cleaning up test environment..."
    docker compose $COMPOSE_FILES $ENV_FILE down -v 2>/dev/null || true
}

print_final_summary() {
    local start_time="$1"
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo ""
    print_separator
    log_success "Tests completed successfully!"
    log_info "Test Summary:"
    log_info "   - Test Type: $TEST_TYPE"
    log_info "   - Duration: ${minutes}m ${seconds}s"
    
    if [[ -n "$SERVICE" ]]; then
        log_info "   - Service: $SERVICE"
    fi
    
    if [[ "$COVERAGE" == true ]]; then
        log_info "   - Coverage reports available in ./coverage-reports/"
        log_info "   - Open coverage-reports/[service]/htmlcov/index.html to view HTML reports"
    fi
    print_separator
}

# --- Argument parsing and help ---

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST_TYPE]
Run tests for the real-time analytics pipeline

Options:
  --service=NAME      Run tests only for specified service (${VALID_SERVICES[*]})
  --coverage          Generate coverage report with HTML and XML output
  --no-cache          Rebuild Docker images without using cache
  -v, --verbose       Verbose pytest output
    --scenario=NAME     Performance scenario: throughput|latency|all (perf only)
    --perf-rates=LIST   Comma-separated rates, e.g. 100,500,1000 (perf only)
    --perf-duration=N   Test duration seconds per rate (perf only)
    --perf-warmup=N     Warmup seconds to ignore (perf only)
  -h, --help          Show this help message

Test types:
  unit                Run unit tests (default)
  integration         Run integration tests
  e2e                 Run end-to-end tests
  performance         Run performance tests
  all                 Run all test types

Examples:
  $0 unit                              # Run unit tests for all services
  $0 --service=cache unit              # Run unit tests for cache service only
  $0 --coverage --verbose all          # Run all tests with coverage and verbose output
  $0 --service=processing --coverage   # Run processing tests with coverage
  $0 --no-cache e2e                   # Force rebuild and run e2e tests
  $0 performance --scenario=throughput --perf-rates=200,500 --perf-duration=45

Coverage Output:
  When --coverage is used, reports are generated in ./coverage-reports/
  - HTML reports: coverage-reports/[service]/htmlcov/index.html
  - XML reports: coverage-reports/[service]/coverage.xml
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --service=*)
                SERVICE="${1#*=}"
                ;;
            --service)
                SERVICE="$2"
                shift
                ;;
            unit|integration|e2e|performance|all)
                TEST_TYPE="$1"
                ;;
            --coverage)
                COVERAGE=true
                ;;
            --no-cache)
                BUILD_FLAGS="--no-cache"
                ;;
            --scenario=*)
                PERF_SCENARIO="${1#*=}"
                ;;
            --scenario)
                PERF_SCENARIO="$2"; shift
                ;;
            --perf-rates=*)
                PERF_RATES="${1#*=}"
                ;;
            --perf-rates)
                PERF_RATES="$2"; shift
                ;;
            --perf-duration=*)
                PERF_DURATION="${1#*=}"
                ;;
            --perf-duration)
                PERF_DURATION="$2"; shift
                ;;
            --perf-warmup=*)
                PERF_WARMUP="${1#*=}"
                ;;
            --perf-warmup)
                PERF_WARMUP="$2"; shift
                ;;
            -v|--verbose)
                VERBOSE=true
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo ""
                print_usage
                exit 1
                ;;
        esac
        shift
    done
}

# --- Main execution ---

main() {
    local start_time
    start_time=$(date +%s)
    
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Default values
    local TEST_TYPE="unit"
    local SERVICE=""
    local COVERAGE=false
    local VERBOSE=false
    local BUILD_FLAGS=""
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Configure pytest arguments
    local PYTEST_ARGS=""
    if [[ "$VERBOSE" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS -v"
    fi
    
    # Validate environment and arguments
    validate_environment "$SERVICE" || exit 1
    
    # Print execution info
    log_info "Starting test execution"
    log_info "Test type: $TEST_TYPE"
    if [[ -n "$SERVICE" ]]; then
        log_info "Service: $SERVICE"
    fi
    if [[ "$COVERAGE" == true ]]; then
        log_info "Coverage: enabled"
    fi
    
    # Execute tests based on type
    case "$TEST_TYPE" in
        unit)
            run_unit_tests || exit 1
            ;;
        integration)
            run_integration_tests || exit 1
            ;;
        e2e)
            run_e2e_tests || exit 1
            ;;
        performance)
            run_performance_tests || exit 1
            ;;
        all)
            run_unit_tests || exit 1
            echo ""
            run_integration_tests || exit 1
            echo ""
            run_e2e_tests || exit 1
            ;;
        *)
            log_error "Unknown test type: $TEST_TYPE"
            exit 1
            ;;
    esac
    
    # Print final summary
    print_final_summary "$start_time"
}


# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi