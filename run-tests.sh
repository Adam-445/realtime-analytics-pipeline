#!/bin/bash

set -euo pipefail

# --- Configuration & Constants ---

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$SCRIPT_DIR"

# Valid services (single source of truth)
readonly VALID_SERVICES=(cache ingestion processing storage)
readonly DEFAULT_SERVICES=(cache ingestion processing storage)

# Docker compose configuration (as arrays for proper quoting)
readonly COMPOSE_BASE_CMD=(
    docker compose
    -f infrastructure/compose/docker-compose.yml
    -f infrastructure/compose/docker-compose.test.yml
    --env-file infrastructure/compose/.env.test
)

# Performance test defaults
readonly DEFAULT_PERF_RATES="50"
readonly DEFAULT_PERF_DURATION="30"
readonly DEFAULT_PERF_WARMUP="0"
readonly DEFAULT_PERF_MAX_ERROR_RATE="5.0"
readonly DEFAULT_INGESTION_URL="http://ingestion:8000"
readonly DEFAULT_CACHE_URL="http://cache:8080"

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
    
    if ! "${COMPOSE_BASE_CMD[@]}" build $BUILD_FLAGS "${services[@]}"; then
        log_error "Failed to build service images"
        log_error "Services: ${services[*]}"
        [[ -n "$BUILD_FLAGS" ]] && log_error "Build flags: $BUILD_FLAGS"
        log_error "Tip: Try with --no-cache if you suspect caching issues"
        return 1
    fi
    
    log_success "Service images built successfully"
}

# Helper to build test images (used by multiple test types)
build_test_images() {
    local -a targets=("$@")
    
    log_info "Building test images..."
    
    if ! "${COMPOSE_BASE_CMD[@]}" build $BUILD_FLAGS "${targets[@]}"; then
        log_error "Failed to build test images"
        [[ ${#targets[@]} -gt 0 ]] && log_error "Targets: ${targets[*]}"
        [[ -n "$BUILD_FLAGS" ]] && log_error "Build flags: $BUILD_FLAGS"
        return 1
    fi
    
    log_success "Test images built successfully"
}

# --- Test Execution ---

run_single_service_test() {
    local service="$1"
    local pytest_args="$2"
    
    print_test_header "$service"
    
    # Build docker command as array for proper quoting
    local -a docker_cmd=("${COMPOSE_BASE_CMD[@]}" run --rm)
    
    # Add volume mounts if coverage is enabled
    if [[ "$COVERAGE" == true ]]; then
        local host_path="$(pwd)/coverage-reports/$service"
        local container_path="/app/coverage-reports/$service"
        docker_cmd+=(-v "$host_path:$container_path")
    fi
    
    # Add service and test command
    docker_cmd+=("$service" python -m pytest tests/unit $pytest_args)
    
    # Execute the test
    if "${docker_cmd[@]}"; then
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
    
    # Build test-runner image
    if ! build_test_images test-runner; then
        return 1
    fi
    
    # Run integration tests
    if ! "${COMPOSE_BASE_CMD[@]}" run --rm test-runner bash -c "cd /tests && python -m pytest integration $PYTEST_ARGS"; then
        log_error "Integration tests failed"
        return 1
    fi
    
    log_success "Integration tests completed successfully!"
}

run_e2e_tests() {
    log_info "Running end-to-end tests..."
    
    # Build all images for e2e
    if ! build_test_images; then
        return 1
    fi
    
    # Run e2e tests
    if ! "${COMPOSE_BASE_CMD[@]}" run --rm test-runner bash -c "cd /tests && python -m pytest e2e $PYTEST_ARGS"; then
        log_error "End-to-end tests failed"
        return 1
    fi
    
    log_success "End-to-end tests completed successfully!"
}

# Helper: Add performance test environment variables to docker command array
add_performance_env_vars() {
    local -n cmd_array=$1  # Pass array by reference
    
    # Required config with defaults
    cmd_array+=(-e "PERF_RATES=${PERF_RATES:-$DEFAULT_PERF_RATES}")
    cmd_array+=(-e "PERF_DURATION=${PERF_DURATION:-$DEFAULT_PERF_DURATION}")
    
    # Optional performance config (only add if explicitly set)
    [[ -n "${PERF_WARMUP:-}" ]] && cmd_array+=(-e "PERF_WARMUP=$PERF_WARMUP")
    [[ -n "${PERF_STRICT:-}" ]] && cmd_array+=(-e "PERF_STRICT=$PERF_STRICT")
    [[ -n "${PERF_MAX_ERROR_RATE:-}" ]] && cmd_array+=(-e "PERF_MAX_ERROR_RATE=$PERF_MAX_ERROR_RATE")
    
    # Service endpoints with defaults
    cmd_array+=(-e "INGESTION_URL=${INGESTION_URL:-$DEFAULT_INGESTION_URL}")
    cmd_array+=(-e "CACHE_URL=${CACHE_URL:-$DEFAULT_CACHE_URL}")
    
    # Optional endpoints
    [[ -n "${PROMETHEUS_URL:-}" ]] && cmd_array+=(-e "PROMETHEUS_URL=$PROMETHEUS_URL")
    
    # Git metadata for test reporting
    local git_commit git_branch
    git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    git_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    cmd_array+=(-e "GIT_COMMIT=$git_commit")
    cmd_array+=(-e "GIT_BRANCH=$git_branch")
    cmd_array+=(-e "PERF_SCENARIO=throughput")
    
    # User-provided environment variables (from --env flag)
    for env_var in "${CLI_ENV_VARS[@]}"; do
        cmd_array+=(-e "$env_var")
    done
}

run_performance_tests() {
    log_info "Running performance tests..."
    
    # Build all images (services + test-runner)
    if ! build_test_images; then
        return 1
    fi
    
    # Construct docker command as array (no string concatenation!)
    local -a docker_cmd=("${COMPOSE_BASE_CMD[@]}" run --rm)
    
    # Add performance test environment variables
    add_performance_env_vars docker_cmd
    
    # Add test-runner service and pytest command
    docker_cmd+=(
        test-runner
        bash -c "cd /tests && python -m pytest performance/test_throughput.py $PYTEST_ARGS"
    )
    
    # Execute performance tests
    if ! "${docker_cmd[@]}"; then
        log_error "Performance tests failed"
        log_error "Rates: ${PERF_RATES:-$DEFAULT_PERF_RATES}"
        log_error "Duration: ${PERF_DURATION:-$DEFAULT_PERF_DURATION}s"
        return 1
    fi
    
    log_success "Performance tests completed successfully!"
}

# --- Cleanup and utilites ---

cleanup() {
    log_info "Cleaning up test environment..."
    "${COMPOSE_BASE_CMD[@]}" down -v 2>/dev/null || true
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
  --service=NAME        Run tests only for specified service (${VALID_SERVICES[*]})
  --coverage            Generate coverage report with HTML and XML output
  --no-cache            Rebuild Docker images without using cache
  -v, --verbose         Verbose pytest output
  -s, --show-output     Show test output (pytest -s flag)
  --env=KEY=VALUE       Pass custom environment variable to tests
  --perf-rates=LIST     Comma-separated rates, e.g. 100,500,1000 (perf only)
  --perf-duration=N     Test duration seconds per rate (perf only)
  --perf-warmup=N       Warmup seconds to ignore (perf only)
  --perf-strict         Enable strict performance assertions (perf only)
  -h, --help            Show this help message

Test types:
  unit                  Run unit tests (default)
  integration           Run integration tests
  e2e                   Run end-to-end tests
  performance           Run performance tests
  all                   Run all test types

Examples:
  $0 unit                                    # Run unit tests for all services
  $0 --service=cache unit                    # Run unit tests for cache service only
  $0 --coverage --verbose all                # Run all tests with coverage and verbose output
  $0 --service=processing --coverage         # Run processing tests with coverage
  $0 --no-cache e2e                          # Force rebuild and run e2e tests
  $0 --perf-rates=200,500 --perf-duration=45 performance
  $0 -s -v performance                       # Run perf tests with output visible
  $0 --env=DEBUG=1 --env=LOG_LEVEL=debug performance

Coverage Output:
  When --coverage is used, reports are generated in ./coverage-reports/
  - HTML reports: coverage-reports/[service]/htmlcov/index.html
  - XML reports: coverage-reports/[service]/coverage.xml

Performance Test Configuration:
  Default rates: $DEFAULT_PERF_RATES RPS
  Default duration: $DEFAULT_PERF_DURATION seconds
  Default endpoints: ingestion:8000, cache:8080
  Override with: INGESTION_URL, CACHE_URL environment variables
EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            # Service selection
            --service=*)
                SERVICE="${1#*=}"
                ;;
            
            # Test configuration flags
            --coverage)
                COVERAGE=true
                ;;
            --no-cache)
                BUILD_FLAGS="--no-cache"
                ;;
            -v|--verbose)
                VERBOSE=true
                ;;
            -s|--show-output)
                SHOW_OUTPUT=true
                ;;
            
            # Environment variable pass-through
            --env=*)
                CLI_ENV_VARS+=("${1#*=}")
                ;;
            
            # Performance test configuration
            --perf-rates=*)
                PERF_RATES="${1#*=}"
                ;;
            --perf-duration=*)
                PERF_DURATION="${1#*=}"
                ;;
            --perf-warmup=*)
                PERF_WARMUP="${1#*=}"
                ;;
            --perf-strict)
                PERF_STRICT="true"
                ;;
            
            # Test type (positional argument)
            unit|integration|e2e|performance|all)
                TEST_TYPE="$1"
                ;;
            
            # Help
            -h|--help)
                print_usage
                exit 0
                ;;
            
            # Unknown option
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
    local SHOW_OUTPUT=false
    local BUILD_FLAGS=""
    local -a CLI_ENV_VARS=()  # Array for user-provided env vars
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Configure pytest arguments
    local PYTEST_ARGS=""
    [[ "$VERBOSE" == true ]] && PYTEST_ARGS="$PYTEST_ARGS -v"
    [[ "$SHOW_OUTPUT" == true ]] && PYTEST_ARGS="$PYTEST_ARGS -s"
    
    # Validate environment and arguments
    validate_environment "$SERVICE" || exit 1
    
    # Print execution info
    log_info "Starting test execution"
    log_info "Test type: $TEST_TYPE"
    [[ -n "$SERVICE" ]] && log_info "Service: $SERVICE"
    [[ "$COVERAGE" == true ]] && log_info "Coverage: enabled"
    [[ "$SHOW_OUTPUT" == true ]] && log_info "Output capture: disabled"
    [[ ${#CLI_ENV_VARS[@]} -gt 0 ]] && log_info "Custom env vars: ${#CLI_ENV_VARS[@]}"
    
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