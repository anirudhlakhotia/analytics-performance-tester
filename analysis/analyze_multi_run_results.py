#!/usr/bin/env python3
"""
Analytics SDK Performance Multi-Run Result Analyzer

Aggregates results from multiple benchmark runs and calculates
mean and standard deviation for key performance metrics.
"""

import argparse
import pandas as pd
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the 'analysis' directory to the Python path to import from dashboard_generator
sys.path.append(str(Path(__file__).parent.absolute()))

try:
    # Import the metric calculation function from the existing dashboard generator
    from dashboard_generator import calculate_detailed_metrics, load_data, auto_detect_result_files
except ImportError:
    logger.error("Could not import from dashboard_generator.py.")
    logger.error("Please ensure 'dashboard_generator.py' is in the same directory.")
    sys.exit(1)

def analyze_multi_run(base_dir: Path):
    """
    Analyzes all individual run directories within a base multi-run directory.
    """
    run_dirs = [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith('run_')]
    
    if not run_dirs:
        logger.error(f"No run directories found in {base_dir}")
        return

    logger.info(f"Found {len(run_dirs)} runs to analyze.")

    all_metrics = {'operational': [], 'enterprise': []}
    
    # Process each run
    for run_dir in sorted(run_dirs, key=lambda p: int(p.name.split('_')[1])):
        logger.info(f"Processing {run_dir.name}...")
        
        # Use auto_detect to find result files (e.g., operational-go.jsonl)
        data_files, language = auto_detect_result_files(run_dir)

        if not data_files:
            logger.warning(f"  No result files found in {run_dir}, skipping.")
            continue
            
        for sdk_type, file_info in data_files.items():
            df = load_data(file_info['path'])
            if not df.empty:
                metrics = calculate_detailed_metrics(df, language)
                if metrics:
                    all_metrics[sdk_type].append(metrics)

    # Convert lists of metrics to DataFrames for analysis
    op_df = pd.DataFrame(all_metrics['operational'])
    ent_df = pd.DataFrame(all_metrics['enterprise'])

    print_summary(op_df, ent_df, len(run_dirs))


def print_summary(op_df: pd.DataFrame, ent_df: pd.DataFrame, num_runs: int):
    """Prints a formatted summary of the aggregated results."""
    
    if op_df.empty and ent_df.empty:
        logger.warning("No data available to generate a summary.")
        return

    metrics_to_report = {
        'throughput': {'name': 'Throughput (req/s)', 'unit': 'req/s'},
        'avg_latency': {'name': 'Avg Latency (ms)', 'unit': 'ms'},
        'p95_latency': {'name': 'P95 Latency (ms)', 'unit': 'ms'},
        'p99_latency': {'name': 'P99 Latency (ms)', 'unit': 'ms'},
        'std_latency': {'name': 'Std Dev Latency (ms)', 'unit': 'ms'}
    }

    summary_data = []

    for key, info in metrics_to_report.items():
        if not op_df.empty and key in op_df.columns:
            op_mean = op_df[key].mean()
            op_std = op_df[key].std()
            summary_data.append(['Operational', info['name'], f"{op_mean:.2f}", f"{op_std:.2f}"])
        
        if not ent_df.empty and key in ent_df.columns:
            ent_mean = ent_df[key].mean()
            ent_std = ent_df[key].std()
            summary_data.append(['Enterprise', info['name'], f"{ent_mean:.2f}", f"{ent_std:.2f}"])

    # Create a DataFrame for prettier printing
    summary_df = pd.DataFrame(summary_data, columns=['SDK', 'Metric', 'Mean', 'Std Dev'])
    
    header = f"📊 Aggregated Performance Results ({num_runs} Runs) 📊"
    print("\n" + "=" * len(header))
    print(header)
    print("=" * len(header))
    
    # Use pandas to_string() for nice formatting
    if not summary_df.empty:
        print(summary_df.to_string(index=False))
    
    print("=" * len(header))
    print(f"Mean and Standard Deviation calculated across {num_runs} full test executions.")
    print("=" * len(header) + "\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Analyze multi-run performance test results.")
    parser.add_argument(
        "results_dir",
        type=str,
        help="The path to the multi-run results directory containing 'run_1', 'run_2', etc."
    )
    args = parser.parse_args()
    
    base_dir = Path(args.results_dir)
    if not base_dir.is_dir():
        logger.error(f"Provided path is not a directory: {base_dir}")
        sys.exit(1)
        
    analyze_multi_run(base_dir)

if __name__ == "__main__":
    main()