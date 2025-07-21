#!/bin/bash
set -e

# Configuration
NUM_RUNS=10
LANGUAGE="java"
FAILED_RUNS=0

# Setup paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SINGLE_RUN_SCRIPT="$SCRIPT_DIR/run-full-benchmark.sh"
ANALYSIS_SCRIPT="$PROJECT_ROOT/analysis/analyze_multi_run_results.py"
RESULTS_DIR="$PROJECT_ROOT/results"
RUNS_DIR="$RESULTS_DIR/runs"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Create a main directory for this multi-run execution
MULTI_RUN_TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MULTI_RUN_DIR="$RESULTS_DIR/multi-run-${LANGUAGE}-${MULTI_RUN_TIMESTAMP}"
mkdir -p "$MULTI_RUN_DIR"
log_info "Created multi-run directory: $MULTI_RUN_DIR"

# Run the benchmark N times
for i in $(seq 1 $NUM_RUNS); do
    log_step "Starting run $i of $NUM_RUNS..."
    
    # Add error handling for individual runs
    if "$SINGLE_RUN_SCRIPT" "$@"; then
        LATEST_RUN_DIR=$(ls -td -- "$RUNS_DIR"/*/ 2>/dev/null | head -n 1)
        if [ -d "$LATEST_RUN_DIR" ]; then
            mv "$LATEST_RUN_DIR" "$MULTI_RUN_DIR/run_$i"
            log_info "Moved results to $MULTI_RUN_DIR/run_$i"
        else
            log_error "Could not find latest run directory for run $i"
            ((FAILED_RUNS++))
        fi
    else
        log_error "Run $i failed with exit code $?"
        ((FAILED_RUNS++))
    fi
    
    log_info "Completed run $i of $NUM_RUNS."
    echo "--------------------------------------------------"
done

# Report final status
if [ $FAILED_RUNS -gt 0 ]; then
    log_warn "Completed with $FAILED_RUNS failed runs out of $NUM_RUNS total."
else
    log_info "All $NUM_RUNS runs completed successfully."
fi

# Analyze the results only if there are enough successful runs
SUCCESSFUL_RUNS=$((NUM_RUNS - FAILED_RUNS))
if [ $SUCCESSFUL_RUNS -gt 0 ]; then
    log_step "Analyzing results from $SUCCESSFUL_RUNS successful runs..."
    python3 "$ANALYSIS_SCRIPT" "$MULTI_RUN_DIR"
else
    log_error "No successful runs to analyze. Aborting analysis."
    exit 1
fi

log_info "✅ Multi-run benchmark and analysis complete."
log_info "Final aggregated results are in the console output above."
log_info "Individual run data is located in: $MULTI_RUN_DIR"