#!/bin/bash

# Cleanup script for Couchbase Analytics Performance Tester
# Ensures all resources are properly cleaned up

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CBDINOCLUSTER_PATH="${SCRIPT_DIR}/cbdinocluster"

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

cleanup_clusters() {
    if [ ! -f "$CBDINOCLUSTER_PATH" ]; then
        log_warn "cbdinocluster binary not found, skipping cluster cleanup"
        return
    fi
    
    log_info "Cleaning up all cbdinocluster clusters..."
    
    # Get list of all clusters
    CLUSTER_OUTPUT=$($CBDINOCLUSTER_PATH ps 2>/dev/null || echo "")
    
    if echo "$CLUSTER_OUTPUT" | grep -q "No clusters found"; then
        log_info "No clusters found to clean up"
        return
    fi
    
    # Extract cluster IDs
    CLUSTER_IDS=$(echo "$CLUSTER_OUTPUT" | grep -o '[a-f0-9]\{8\}-[a-f0-9]\{4\}-[a-f0-9]\{4\}-[a-f0-9]\{4\}-[a-f0-9]\{12\}' || true)
    
    if [ -n "$CLUSTER_IDS" ]; then
        log_info "Found clusters to clean up:"
        for cluster_id in $CLUSTER_IDS; do
            log_info "  - $cluster_id"
        done
        
        for cluster_id in $CLUSTER_IDS; do
            log_info "Removing cluster: $cluster_id"
            if $CBDINOCLUSTER_PATH rm "$cluster_id" 2>/dev/null; then
                log_info "Successfully removed cluster: $cluster_id"
            else
                log_warn "Failed to remove cluster: $cluster_id"
            fi
        done
    else
        log_info "No cluster IDs found"
    fi
}

cleanup_docker() {
    log_info "Cleaning up Docker containers and networks..."
    
    # Clean up containers with couchbase in the name
    CONTAINERS=$(docker ps -a --filter "name=couchbase" --format "{{.ID}}" 2>/dev/null || true)
    if [ -n "$CONTAINERS" ]; then
        log_info "Removing Couchbase containers..."
        echo "$CONTAINERS" | xargs docker rm -f || log_warn "Some containers couldn't be removed"
    fi
    
    # Clean up networks created by cbdinocluster
    NETWORKS=$(docker network ls --filter "name=cbdinocluster" --format "{{.ID}}" 2>/dev/null || true)
    if [ -n "$NETWORKS" ]; then
        log_info "Removing cbdinocluster networks..."
        echo "$NETWORKS" | xargs docker network rm || log_warn "Some networks couldn't be removed"
    fi
}

cleanup_processes() {
    log_info "Cleaning up any hanging Java processes..."
    
    # Find and kill any performance tester processes
    JAVA_PIDS=$(pgrep -f "AnalyticsPerformanceTester" || true)
    if [ -n "$JAVA_PIDS" ]; then
        log_info "Killing Java performance tester processes..."
        echo "$JAVA_PIDS" | xargs kill -9 || log_warn "Some processes couldn't be killed"
    fi
}

main() {
    log_info "Starting cleanup process..."
    
    cleanup_clusters
    cleanup_docker
    cleanup_processes
    
    log_info "Cleanup completed successfully"
}

# Handle Ctrl+C gracefully
trap 'log_warn "Cleanup interrupted!"; exit 130' INT

main "$@" 