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
        'throughput_rps': 'Throughput (req/s)',
        'mean_latency': 'Avg Latency (ms)',
        'p95_latency': 'P95 Latency (ms)',
        'p99_latency': 'P99 Latency (ms)',
        'std_latency': 'Std Dev Latency (ms)'
    }

    summary_rows = []
    for key, name in metrics_to_report.items():
        row = {'Metric': name}
        
        # Operational SDK
        if not op_df.empty:
            if key in op_df.columns:
                mean = op_df[key].mean()
                std = op_df[key].std()
                row['Operational SDK'] = f"{mean:.2f} (± {std:.2f})"
            else:
                row['Operational SDK'] = "N/A"
        
        # Enterprise SDK
        if not ent_df.empty:
            if key in ent_df.columns:
                mean = ent_df[key].mean()
                std = ent_df[key].std()
                row['Enterprise SDK'] = f"{mean:.2f} (± {std:.2f})"
            else:
                row['Enterprise SDK'] = "N/A"
                
        summary_rows.append(row)

    columns = ['Metric']
    if not op_df.empty:
        columns.append('Operational SDK')
    if not ent_df.empty:
        columns.append('Enterprise SDK')
    
    summary_df = pd.DataFrame(summary_rows, columns=columns)
    
    print(f"\nPerformance Summary ({num_runs} Runs)")
    
    if not summary_df.empty:
        print(summary_df.to_string(index=False))
    
    print(f"\nValues are shown as Mean (± Standard Deviation) across the {num_runs} runs.")


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