#!/bin/bash

# Couchbase Analytics Performance Tester
# This script manages the complete lifecycle of the performance test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CBDINOCLUSTER_PATH="${CBDINOCLUSTER_PATH:-${SCRIPT_DIR}/cbdinocluster}"
RESULTS_DIR="${SCRIPT_DIR}/results"
CONFIG_FILE="${SCRIPT_DIR}/cluster-config.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if cbdinocluster exists
    if [ ! -f "$CBDINOCLUSTER_PATH" ]; then
        log_error "cbdinocluster binary not found at $CBDINOCLUSTER_PATH"
        log_error "Please download cbdinocluster and place it in the project root"
        exit 1
    fi
    
    # Make cbdinocluster executable
    chmod +x "$CBDINOCLUSTER_PATH"
    
    # Check if cluster config exists
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Cluster config file not found at $CONFIG_FILE"
        exit 1
    fi
    
    # Check if Maven is available
    if ! command -v mvn &> /dev/null; then
        log_error "Maven is required but not installed"
        exit 1
    fi
    
    # Check if Java is available
    if ! command -v java &> /dev/null; then
        log_error "Java is required but not installed"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

setup_results_directory() {
    log_info "Setting up results directory..."
    mkdir -p "$RESULTS_DIR"
    
    # Archive old results if they exist
    if [ -f "$RESULTS_DIR/individual_results.jsonl" ]; then
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        ARCHIVE_DIR="$RESULTS_DIR/archive_$TIMESTAMP"
        mkdir -p "$ARCHIVE_DIR"
        mv "$RESULTS_DIR"/*.jsonl "$ARCHIVE_DIR/" 2>/dev/null || true
        log_info "Archived previous results to $ARCHIVE_DIR"
    fi
}

cleanup_clusters() {
    log_info "Cleaning up any existing clusters..."
    
    # List and remove any existing clusters
    CLUSTER_IDS=$($CBDINOCLUSTER_PATH ps --json 2>/dev/null | grep -o '[a-f0-9]\{8\}-[a-f0-9]\{4\}-[a-f0-9]\{4\}-[a-f0-9]\{4\}-[a-f0-9]\{12\}' || true)
    
    if [ -n "$CLUSTER_IDS" ]; then
        log_warn "Found existing clusters, cleaning up..."
        for cluster_id in $CLUSTER_IDS; do
            log_info "Removing cluster: $cluster_id"
            $CBDINOCLUSTER_PATH rm "$cluster_id" || log_warn "Failed to remove cluster $cluster_id"
        done
    else
        log_info "No existing clusters found"
    fi
}

build_application() {
    log_info "Building Java application..."
    cd "$SCRIPT_DIR"
    mvn clean compile -q
    log_info "Build completed successfully"
}

run_test() {
    log_info "Starting performance test..."
    cd "$SCRIPT_DIR"
    
    # Run the test with proper error handling
    if mvn exec:java -Dexec.mainClass="com.couchbase.perf.AnalyticsPerformanceTester" -Dcbdinocluster.path="$CBDINOCLUSTER_PATH" -q; then
        log_info "Performance test completed successfully"
        
        # Show results summary
        if [ -f "$RESULTS_DIR/individual_results.jsonl" ]; then
            RESULT_COUNT=$(wc -l < "$RESULTS_DIR/individual_results.jsonl")
            log_info "Results written: $RESULT_COUNT records"
            log_info "Results file: $RESULTS_DIR/individual_results.jsonl"
        fi
    else
        log_error "Performance test failed"
        exit 1
    fi
}

show_help() {
    cat << EOF
Couchbase Analytics Performance Tester

Usage: $0 [COMMAND]

Commands:
    run         Run the complete performance test (default)
    clean       Clean up any existing clusters
    build       Build the Java application only
    help        Show this help message

Examples:
    $0                 # Run the complete test
    $0 run             # Run the complete test
    $0 clean           # Clean up existing clusters
    $0 build           # Build application only

EOF
}

main() {
    case "${1:-run}" in
        "run")
            check_prerequisites
            setup_results_directory
            cleanup_clusters
            build_application
            run_test
            ;;
        "clean")
            check_prerequisites
            cleanup_clusters
            ;;
        "build")
            check_prerequisites
            build_application
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'log_warn "Interrupted! Cleaning up..."; cleanup_clusters; exit 130' INT

main "$@" 