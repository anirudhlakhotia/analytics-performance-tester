#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Flexible cbdinocluster path detection
detect_cbdinocluster() {
    # Priority order:
    # 1. Environment variable CBDINOCLUSTER_PATH
    # 2. Project root binary
    # 3. PATH lookup
    # 4. Common installation locations
    
    if [ -n "$CBDINOCLUSTER_PATH" ] && [ -x "$CBDINOCLUSTER_PATH" ]; then
        echo "$CBDINOCLUSTER_PATH"
        return 0
    fi
    
    # Check project root
    if [ -x "$PROJECT_ROOT/cbdinocluster" ]; then
        echo "$PROJECT_ROOT/cbdinocluster"
        return 0
    fi
    
    # Check PATH
    if command -v cbdinocluster &> /dev/null; then
        echo "cbdinocluster"
        return 0
    fi
    
    # Check common locations
    local common_paths=(
        "/usr/local/bin/cbdinocluster"
        "$HOME/bin/cbdinocluster"
        "$HOME/.local/bin/cbdinocluster"
    )
    
    for path in "${common_paths[@]}"; do
        if [ -x "$path" ]; then
            echo "$path"
            return 0
        fi
    done
    
    return 1
}

CBDINOCLUSTER_PATH=$(detect_cbdinocluster)
CONFIG_FILE="${SCRIPT_DIR}/cluster-config.yaml"
CLUSTER_ID_FILE="${PROJECT_ROOT}/results/.cluster_id"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions (safe to source)
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

log_header() {
    echo -e "${YELLOW}================================================${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}================================================${NC}"
}

log_step() {
    echo ""
    echo -e "${YELLOW}[STEP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

show_installation_help() {
    log_error "cbdinocluster not found!"
    echo
    echo -e "${YELLOW}Installation Options:${NC}"
    echo
    echo -e "${BLUE}Option 1: Download to project root (recommended)${NC}"
    echo "  # For macOS (Apple Silicon)"
    echo "  curl -L -o cbdinocluster https://github.com/couchbaselabs/cbdinocluster/releases/download/v0.0.75/cbdinocluster-darwin-arm64"
    echo "  chmod +x cbdinocluster"
    echo
    echo "  # For macOS (Intel)"
    echo "  curl -L -o cbdinocluster https://github.com/couchbaselabs/cbdinocluster/releases/download/v0.0.75/cbdinocluster-darwin-amd64"
    echo "  chmod +x cbdinocluster"
    echo
    echo "  # For Linux"
    echo "  curl -L -o cbdinocluster https://github.com/couchbaselabs/cbdinocluster/releases/download/v0.0.75/cbdinocluster-linux-amd64"
    echo "  chmod +x cbdinocluster"
    echo
    echo -e "${BLUE}Option 2: Install to PATH${NC}"
    echo "  # Download to /usr/local/bin"
    echo "  sudo curl -L -o /usr/local/bin/cbdinocluster https://github.com/couchbaselabs/cbdinocluster/releases/download/v0.0.75/cbdinocluster-darwin-amd64"
    echo "  sudo chmod +x /usr/local/bin/cbdinocluster"
    echo
    echo -e "${BLUE}Option 3: Set custom path${NC}"
    echo "  export CBDINOCLUSTER_PATH=/path/to/your/cbdinocluster"
    echo
    echo -e "${BLUE}After installation:${NC}"
    echo "  cbdinocluster init  # Run once to configure"
    echo
}

check_cbdinocluster() {
    if [ -z "$CBDINOCLUSTER_PATH" ]; then
        show_installation_help
        exit 1
    fi
    
    log_debug "Using cbdinocluster: $CBDINOCLUSTER_PATH"
    
    # Test if cbdinocluster works
    if ! "$CBDINOCLUSTER_PATH" version &> /dev/null; then
        log_error "cbdinocluster binary found but not working: $CBDINOCLUSTER_PATH"
        log_error "You may need to run: $CBDINOCLUSTER_PATH init"
        exit 1
    fi
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Cluster config file not found: $CONFIG_FILE"
        log_error "Make sure cluster-config.yaml exists in the project root"
        exit 1
    fi
    
    log_debug "Configuration file: $CONFIG_FILE"
}

start_cluster() {
    log_info "Starting analytics cluster..."
    
    check_cbdinocluster
    
    # Check if cluster already exists
    log_debug "Checking for existing clusters..."
    EXISTING_CLUSTERS=$("$CBDINOCLUSTER_PATH" ps --json 2>/dev/null | jq -r '.[].id' 2>/dev/null || echo "")
    
    if [ -n "$EXISTING_CLUSTERS" ]; then
        log_warn "Existing clusters found:"
        echo "$EXISTING_CLUSTERS" | while read -r cluster_id; do
            log_warn "  - $cluster_id"
        done
        log_warn "Cleaning up existing clusters first..."
        stop_cluster
    fi
    
    # Start cluster
    log_info "Allocating new cluster with config: $(basename "$CONFIG_FILE")"
    CLUSTER_ID=$("$CBDINOCLUSTER_PATH" allocate --def-file "$CONFIG_FILE" 2>&1)
    
    if [ -z "$CLUSTER_ID" ] || [[ "$CLUSTER_ID" == *"error"* ]] || [[ "$CLUSTER_ID" == *"failed"* ]]; then
        log_error "Failed to allocate cluster:"
        log_error "$CLUSTER_ID"
        exit 1
    fi
    
    # Extract just the cluster ID (remove any extra output)
    CLUSTER_ID=$(echo "$CLUSTER_ID" | tail -n1 | tr -d '\r\n')
    
    log_info "Cluster allocated with ID: $CLUSTER_ID"
    
    # Wait for cluster to be ready
    log_info "Waiting for cluster to be ready..."
    local wait_time=0
    local max_wait=120  # 2 minutes
    
    while [ $wait_time -lt $max_wait ]; do
        if CONNECTION_STRING=$("$CBDINOCLUSTER_PATH" connstr "$CLUSTER_ID" 2>/dev/null); then
            if [ -n "$CONNECTION_STRING" ] && [[ "$CONNECTION_STRING" != *"error"* ]]; then
                break
            fi
        fi
        
        echo -n "."
        sleep 5
        wait_time=$((wait_time + 5))
    done
    echo
    
    if [ $wait_time -ge $max_wait ]; then
        log_error "Cluster did not become ready within $max_wait seconds"
        log_error "Cluster ID: $CLUSTER_ID"
        exit 1
    fi
    
    # Get final connection string
    CONNECTION_STRING=$("$CBDINOCLUSTER_PATH" connstr "$CLUSTER_ID" 2>/dev/null)
    
    if [ -z "$CONNECTION_STRING" ]; then
        log_error "Failed to get connection string for cluster: $CLUSTER_ID"
        exit 1
    fi
    
    log_info "Cluster ready at: $CONNECTION_STRING"
    
    # Export for test apps and save to file
    export CLUSTER_CONNECTION_STRING="$CONNECTION_STRING"
    export CLUSTER_ID="$CLUSTER_ID"
    
    # Save environment variables to files for other scripts
    cat > "$PROJECT_ROOT/cluster-env.sh" << EOF
# Auto-generated cluster environment
# Generated: $(date)
export CLUSTER_CONNECTION_STRING="$CONNECTION_STRING"
export CLUSTER_ID="$CLUSTER_ID"
export CBDINOCLUSTER_PATH="$CBDINOCLUSTER_PATH"
EOF
    
    # Also save to temp location for backward compatibility
    echo "CLUSTER_CONNECTION_STRING=$CONNECTION_STRING" > /tmp/cluster-env
    echo "CLUSTER_ID=$CLUSTER_ID" >> /tmp/cluster-env
    
    log_info "Environment saved to: $PROJECT_ROOT/cluster-env.sh"
    log_info "✅ Cluster is ready for testing!"
}

stop_cluster() {
    log_info "Stopping analytics cluster..."
    
    check_cbdinocluster
    
    # Get all cluster IDs and remove them
    log_debug "Getting list of clusters..."
    CLUSTER_IDS=$("$CBDINOCLUSTER_PATH" ps --json 2>/dev/null | jq -r '.[].id' 2>/dev/null || echo "")
    
    if [ -n "$CLUSTER_IDS" ]; then
        echo "$CLUSTER_IDS" | while read -r cluster_id; do
            if [ -n "$cluster_id" ]; then
                log_info "Removing cluster: $cluster_id"
                "$CBDINOCLUSTER_PATH" rm "$cluster_id" || log_warn "Failed to remove cluster $cluster_id"
            fi
        done
    else
        log_info "No clusters found to remove"
    fi
    
    # Clean up environment files
    rm -f "$PROJECT_ROOT/cluster-env.sh"
    rm -f /tmp/cluster-env
    
    log_info "✅ Cluster cleanup completed"
}

get_connection_string() {
    if [ -f "$PROJECT_ROOT/cluster-env.sh" ]; then
        source "$PROJECT_ROOT/cluster-env.sh"
        echo "$CLUSTER_CONNECTION_STRING"
    else
        log_error "No cluster environment found. Start cluster first with: $0 start"
        exit 1
    fi
}

show_status() {
    check_cbdinocluster
    
    if [ -f "$PROJECT_ROOT/cluster-env.sh" ]; then
        source "$PROJECT_ROOT/cluster-env.sh"
        log_info "Cluster Status:"
        log_info "  ID: $CLUSTER_ID"
        log_info "  Connection: $CLUSTER_CONNECTION_STRING"
        log_info "  Binary: $CBDINOCLUSTER_PATH"
        
        # Try to get live status
        if LIVE_STATUS=$("$CBDINOCLUSTER_PATH" ps --json 2>/dev/null); then
            if echo "$LIVE_STATUS" | jq -e ".[] | select(.id == \"$CLUSTER_ID\")" > /dev/null 2>&1; then
                log_info "  Status: ✅ Running"
            else
                log_warn "  Status: ⚠️  Not found in live clusters"
            fi
        fi
    else
        log_info "No active cluster found"
        log_info "Start a cluster with: $0 start"
    fi
}

usage() {
    echo "Analytics Performance Tester - Cluster Manager"
    echo
    echo "Usage: $0 {start|stop|restart|connstr|status|check}"
    echo
    echo "Commands:"
    echo "  start    - Start analytics cluster"
    echo "  stop     - Stop all clusters"
    echo "  restart  - Stop and start cluster"
    echo "  connstr  - Get connection string"
    echo "  status   - Show cluster status"
    echo "  check    - Verify cbdinocluster setup"
    echo
    echo "Environment Variables:"
    echo "  CBDINOCLUSTER_PATH - Custom path to cbdinocluster binary"
    echo
    if [ -z "$CBDINOCLUSTER_PATH" ]; then
        show_installation_help
    fi
}

# --- Main Execution Logic ---
# This block will only run when the script is executed directly, not when sourced.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    case "${1:-help}" in
        "start")
            start_cluster
            ;;
        "stop")
            stop_cluster
            ;;
        "restart")
            stop_cluster
            start_cluster
            ;;
        "connstr")
            get_connection_string
            ;;
        "status")
            show_status
            ;;
        "check")
            check_cbdinocluster
            log_info "✅ cbdinocluster is properly configured"
            log_info "Binary: $CBDINOCLUSTER_PATH"
            log_info "Config: $CONFIG_FILE"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
fi