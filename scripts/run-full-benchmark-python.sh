#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check for required tools
check_prerequisites() {
    # Check for yq
    if ! command -v yq &> /dev/null; then
        log_error "yq is required but not installed"
        log_error "Install with: brew install yq (macOS) or apt-get install yq (Ubuntu)"
        exit 1
    fi
    
    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        log_error "Install Python 3 from: https://www.python.org/downloads/"
        exit 1
    fi
    
    # Check Python version
    local python_version=$(python3 --version | awk '{print $2}' | cut -d. -f1-2)
    local required_version="3.8"
    if ! printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1 | grep -q "$required_version"; then
        log_error "Python version $required_version or higher is required, but found $python_version"
        exit 1
    fi
    
    log_info "✅ Prerequisites check passed"
}

# Parse configuration from config.yaml using yq
parse_config() {
    local config_file="$PROJECT_ROOT/config.yaml"
    
    if [ ! -f "$config_file" ]; then
        log_error "Configuration file not found: $config_file"
        exit 1
    fi
    
    log_step "Parsing configuration from $config_file..."
    
    # Test execution settings
    export BENCHMARK_DURATION_MS=$(yq '.test.duration_ms' "$config_file")
    export BENCHMARK_WARMUP_MS=$(yq '.test.warmup_ms' "$config_file")
    export BENCHMARK_THREADS=$(yq '.test.threads' "$config_file")
    export BENCHMARK_REQUEST_INTERVAL_MS=$(yq '.test.request_interval_ms' "$config_file")
    export BENCHMARK_PROGRESS_INTERVAL_MS=$(yq '.monitoring.progress_report_interval_ms' "$config_file")
    
    # SDK settings
    export BENCHMARK_ANALYTICS_TIMEOUT_S=$(yq '.sdk.analytics_timeout_s' "$config_file")
    export BENCHMARK_CONNECTION_TIMEOUT_S=$(yq '.sdk.connection_timeout_s' "$config_file")
    
    # Cluster settings
    export CLUSTER_USERNAME=$(yq '.cluster.username' "$config_file")
    export CLUSTER_PASSWORD=$(yq '.cluster.password' "$config_file")
    
    # Query settings (use first query for simplicity)
    export BENCHMARK_QUERY=$(yq '.queries[0].statement' "$config_file")
    export BENCHMARK_QUERY_NAME=$(yq '.queries[0].name' "$config_file")
    
    log_info "✅ Configuration parsed successfully"
    log_info "   Duration: ${BENCHMARK_DURATION_MS}ms"
    log_info "   Threads: ${BENCHMARK_THREADS}"
    log_info "   Query: ${BENCHMARK_QUERY_NAME}"
}

# Generate timestamp and create directories
setup_directories() {
    # Generate timestamp for this run
    RUN_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
    RESULTS_DIR="$PROJECT_ROOT/results"
    RUN_DIR="$RESULTS_DIR/runs/$RUN_TIMESTAMP"

    # Create all directories upfront
    log_step "Creating timestamped directories..."
    mkdir -p "$RUN_DIR/raw"
    mkdir -p "$RUN_DIR/reports"
    mkdir -p "$RUN_DIR/logs"
    log_info "✅ Created directories: $RUN_DIR"

    # Export paths for use by other functions
    export RUN_TIMESTAMP
    export RESULTS_DIR
    export RUN_DIR
    export BENCHMARK_RUN_TIMESTAMP="$RUN_TIMESTAMP"
}

# Handle cluster connection
setup_cluster() {
    # Check if cluster connection string is provided as argument
    if [ -n "$USE_EXISTING_CLUSTER" ]; then
        log_step "Using existing cluster connection..."
        log_info "🔗 Cluster: $USE_EXISTING_CLUSTER"
        
        # Test the connection
        local host=$(echo "$USE_EXISTING_CLUSTER" | sed 's|couchbase://||' | cut -d: -f1)
        log_info "🔍 Testing connection to cluster at $host..."
        
        if timeout 10 curl -s "http://$host:8091/pools" > /dev/null 2>&1; then
            log_info "✅ Cluster connection verified"
        else
            log_warn "⚠️  Could not verify cluster connection, but proceeding anyway..."
        fi
        
        export CLUSTER_CONNECTION_STRING="$USE_EXISTING_CLUSTER"
        export STARTED_OWN_CLUSTER="false"
        return 0
    fi
    
    # No existing cluster provided, start our own
    log_step "Starting new Couchbase cluster..."
    
    # Clean up any existing environment that might interfere
    unset CLUSTER_CONNECTION_STRING
    unset CLUSTER_ID
    rm -f "$PROJECT_ROOT/cluster-env.sh"
    
    "$PROJECT_ROOT/infrastructure/cluster-manager.sh" start
    
    # Get cluster connection info
    if [ -f "$PROJECT_ROOT/cluster-env.sh" ]; then
        source "$PROJECT_ROOT/cluster-env.sh"
        export CLUSTER_CONNECTION_STRING="$CLUSTER_CONNECTION_STRING"
        export STARTED_OWN_CLUSTER="true"
        log_info "🔗 New cluster ready at: $CLUSTER_CONNECTION_STRING"
    else
        log_error "Failed to get cluster connection info"
        exit 1
    fi
}

# Setup Python environment
setup_python_env() {
    local app_dir="$PROJECT_ROOT/apps/python-analytics-client"
    
    log_step "Setting up Python environment..."
    cd "$app_dir"
    
    # Check if virtual environment exists, create if not
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip

    # Install dependencies
    log_info "Installing dependencies..."
    pip install -r requirements.txt
    
    # Install operational SDK
    log_info "Installing operational SDK..."
    pip install couchbase
    
    # Install analytics SDK from source
    log_info "Installing analytics SDK from source..."
    ANALYTICS_SDK_PATH="${ANALYTICS_SDK_PATH:-$PROJECT_ROOT/analytics-python-client}"
    if [ ! -d "$ANALYTICS_SDK_PATH" ]; then
        log_error "Analytics SDK path '$ANALYTICS_SDK_PATH' does not exist. Please set the ANALYTICS_SDK_PATH environment variable or check your project structure."
        exit 1
    fi
    cd "$ANALYTICS_SDK_PATH"
    pip install -e .
    
    # Go back to app directory
    cd "$app_dir"
    
    log_info "✅ Python environment setup complete"
}

# Run a single SDK test with live output
run_sdk_test() {
    local sdk_type="$1"
    local output_file="$RUN_DIR/raw/${sdk_type}-python.jsonl"    # Add "-python" suffix
    local log_file="$RUN_DIR/logs/${sdk_type}-python.log"       # Add "-python" suffix
    
    log_step "Running $sdk_type SDK test (Python)..."
    
    # Set SDK-specific environment variables
    export BENCHMARK_SDK_TYPE="$sdk_type"
    export BENCHMARK_OUTPUT_FILE="$output_file"
    export BENCHMARK_LOG_FILE="$log_file"
    
    # Run the Python application with live output and log capture
    log_info "Executing $sdk_type SDK test..."
    echo "----------------------------------------"
    
    cd "$PROJECT_ROOT/apps/python-analytics-client"
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Use tee to show output AND capture to log file
    python3 main.py 2>&1 | tee "$log_file"
    
    local exit_code=${PIPESTATUS[0]}
    
    echo "----------------------------------------"
    
    # Check if the process succeeded
    if [ $exit_code -eq 0 ]; then
        # Verify output file was created
        if [ -f "$output_file" ]; then
            local line_count=$(wc -l < "$output_file")
            log_info "✅ $sdk_type SDK test completed: $line_count results written to $output_file"
        else
            log_error "❌ $sdk_type SDK test failed: no output file created"
            log_error "Check log file: $log_file"
            exit 1
        fi
    else
        log_error "❌ $sdk_type SDK test failed"
        log_error "Check log file: $log_file"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    if [ "$STARTED_OWN_CLUSTER" = "true" ]; then
        log_info "🧹 Cleaning up cluster we started..."
        "$PROJECT_ROOT/infrastructure/cluster-manager.sh" stop || true
    else
        log_info "🧹 Cleanup complete (using existing cluster, not stopping it)"
    fi
}

# Handle interrupts gracefully
trap cleanup EXIT INT TERM

main() {
    echo "🚀 Analytics Performance Tester - Python Implementation"
    echo "======================================================"
    echo
    
    # Show cluster mode based on arguments
    if [ -n "$USE_EXISTING_CLUSTER" ]; then
        log_info "🎯 Mode: Using existing cluster (provided as argument)"
        log_info "   Connection: $USE_EXISTING_CLUSTER"
    else
        log_info "🆕 Mode: Will start new cluster automatically"
    fi
    echo
    
    # Prerequisites
    check_prerequisites
    
    # Parse configuration from YAML
    parse_config
    
    # Setup directories
    setup_directories
    
    # Setup cluster (existing or new)
    setup_cluster
    
    # Setup Python environment and dependencies
    setup_python_env
    
    # Run both SDK tests with live output
    run_sdk_test "operational"
    run_sdk_test "enterprise"
    
    # Generate dashboard
    log_step "Generating analysis dashboard..."
    if ! python3 "$PROJECT_ROOT/analysis/dashboard_generator.py" --run-dir "$RUN_DIR"; then
        log_error "Dashboard generation failed. See above for details. Continuing with summary output."
    fi
    
    # Create latest symlink
    if [ -L "$RESULTS_DIR/latest" ]; then
        rm "$RESULTS_DIR/latest"
    fi
    ln -sfn "runs/$RUN_TIMESTAMP" "$RESULTS_DIR/latest"
    
    # Success summary
    echo
    echo "🎉 Python Test Suite Completed Successfully!"
    echo "==========================================="
    log_info "📋 Results Summary:"
    log_info "   📊 Dashboard: $RUN_DIR/reports/dashboard.html"
    log_info "   📄 Raw Data: $RUN_DIR/raw/*.jsonl"
    log_info "   📋 Logs: $RUN_DIR/logs/*.log"
    log_info "   🔗 Latest: $RESULTS_DIR/latest"
    echo
    
    # Open dashboard
    if command -v open >/dev/null 2>&1; then
        open "$RUN_DIR/reports/dashboard.html"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$RUN_DIR/reports/dashboard.html"
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cluster)
            USE_EXISTING_CLUSTER="$2"
            shift 2
            ;;
        --help|-h)
            echo "Analytics Performance Tester - Python Implementation"
            echo
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "OPTIONS:"
            echo "  --cluster <connection>    Use existing cluster (e.g., couchbase://host:11210)"
            echo "  --help, -h               Show this help message"
            echo
            echo "PREREQUISITES:"
            echo "=============="
            echo "  - Python 3.8+ (https://www.python.org/downloads/)"
            echo "  - yq (YAML processor): brew install yq"
            echo "  - cbdinocluster binary (for new cluster mode only)"
            echo
            echo "EXAMPLES:"
            echo "========="
            echo "# Test against local cluster"
            echo "$0 --cluster couchbase://localhost:11210"
            echo
            echo "# Auto-create cluster for testing"
            echo "$0"
            echo
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            log_error "Use --help for usage information"
            exit 1
            ;;
    esac
done

main "$@" 