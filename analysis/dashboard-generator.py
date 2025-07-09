#!/usr/bin/env python3
"""
Analytics SDK Performance Test Result Analyzer

Generates developer-friendly HTML dashboard from JSONL test results
"""

import json
import argparse
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from pathlib import Path
import logging
import os
import sys
import yaml

# Constants
RESULTS_DIR = Path(__file__).parent.parent / "results"
RAW_DIR = RESULTS_DIR / "raw"
REPORTS_DIR = RESULTS_DIR / "reports"
DASHBOARD_FILE = REPORTS_DIR / "dashboard.html"
CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

# Color scheme
COLORS = {
    'operational': '#2E86AB',  # Professional blue
    'enterprise': '#A23B72',   # Professional purple
    'success': '#43AA8B',      # Green
    'error': '#F18F01'         # Orange
}

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.warning(f"Could not load config from {CONFIG_FILE}: {e}")
        return None

def load_data(file_path):
    """Loads JSONL data, returns an empty DataFrame if file is missing or empty."""
    if not file_path.exists() or os.path.getsize(file_path) == 0:
        logger.warning(f"Data file not found or is empty: {file_path}")
        return pd.DataFrame()
    return pd.read_json(file_path, lines=True)

# FIXED: Correct throughput calculation in dashboard-generator.py
def calculate_detailed_metrics(df):
    """Calculate detailed metrics including all requested statistics."""
    if df.empty:
        return None
    
    # Load config to get actual test duration
    config = load_config()
    test_duration_ms = config.get('test', {}).get('duration_ms', 30000) if config else 30000
    test_duration_s = test_duration_ms / 1000.0
    
    total_requests = len(df)
    successful_df = df[df['success']]
    success_count = len(successful_df)
    success_rate = (success_count / total_requests) * 100 if total_requests > 0 else 0
    
    if successful_df.empty:
        return {
            'total_requests': total_requests,
            'success_rate': 0,
            'avg_latency': 0,
            'min_latency': 0,
            'max_latency': 0,
            'std_latency': 0,
            'p95_latency': 0,
            'p99_latency': 0,
            'throughput': 0,
            'test_duration_s': test_duration_s
        }
    
    # FIXED: Calculate throughput using actual test duration from timestamps
    if 'timestamp' in successful_df.columns and len(successful_df) > 1:
        # Handle both pandas Timestamp objects and numeric values
        timestamps = successful_df['timestamp']
        
        if hasattr(timestamps.iloc[0], 'timestamp'):
            # If pandas Timestamp objects, convert to milliseconds
            start_ms = timestamps.min().timestamp() * 1000
            end_ms = timestamps.max().timestamp() * 1000
        else:
            # Already numeric timestamps in milliseconds
            start_ms = float(timestamps.min())
            end_ms = float(timestamps.max())
        
        actual_duration_s = (end_ms - start_ms) / 1000.0
        actual_duration_s = max(actual_duration_s, 1.0)  # Ensure minimum duration
        
        throughput = success_count / actual_duration_s
        final_test_duration_s = actual_duration_s
    else:
        # Fallback to config duration if timestamps are unreliable
        throughput = success_count / test_duration_s
        final_test_duration_s = test_duration_s
    
    # Detailed latency metrics
    latencies = successful_df['duration_ms']
    
    return {
        'total_requests': total_requests,
        'success_rate': success_rate,
        'avg_latency': latencies.mean(),
        'min_latency': latencies.min(),
        'max_latency': latencies.max(),
        'std_latency': latencies.std(),
        'p95_latency': latencies.quantile(0.95),
        'p99_latency': latencies.quantile(0.99),
        'throughput': throughput,
        'test_duration_s': final_test_duration_s
    }

def create_detailed_summary_table(op_metrics, ent_metrics):
    """Create detailed summary table with all requested metrics."""
    # Prepare data for the table
    metrics_data = []
    
    for name, metrics, color in [("Operational SDK", op_metrics, COLORS['operational']), 
                                 ("Enterprise SDK", ent_metrics, COLORS['enterprise'])]:
        if not metrics:
            metrics_data.append([
                f"<b>{name}</b>", "No data", "No data", "No data", 
                "No data", "No data", "No data", "No data", "No data"
            ])
            continue
            
        metrics_data.append([
            f"<b>{name}</b>",
            f"{metrics['success_rate']:.1f}%",
            f"{metrics['throughput']:.1f}",
            f"{metrics['avg_latency']:.1f}",
            f"{metrics['min_latency']:.1f}",
            f"{metrics['max_latency']:.1f}",
            f"{metrics['std_latency']:.1f}",
            f"{metrics['p95_latency']:.1f}",
            f"{metrics['p99_latency']:.1f}"
        ])
    
    # Create table with better styling
    return go.Table(
        header=dict(
            values=[
                "<b>SDK</b>", 
                "<b>Success<br>Rate</b>", 
                "<b>Throughput<br>(req/s)</b>",
                "<b>Average<br>(ms)</b>", 
                "<b>Min<br>(ms)</b>", 
                "<b>Max<br>(ms)</b>", 
                "<b>Std Dev<br>(ms)</b>",
                "<b>P95<br>(ms)</b>", 
                "<b>P99<br>(ms)</b>"
            ],
            fill_color='#f1f1f2',
            align='center',
            font=dict(size=13, color='black'),
            height=50
        ),
        cells=dict(
            values=list(zip(*metrics_data)),
            fill_color=['white', '#f8f9fa'],
            align='center',
            font=dict(size=12),
            height=35
        )
    )

def create_developer_dashboard(operational_df, enterprise_df, metadata=None, run_timestamp=None, output_path=None):
    """Creates a clean, developer-focused dashboard with detailed metrics."""
    logger.info("Generating developer-friendly dashboard...")
    
    # Use provided output path or fall back to default
    dashboard_file = Path(output_path) if output_path else DASHBOARD_FILE
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Calculate detailed metrics
    op_metrics = calculate_detailed_metrics(operational_df)
    ent_metrics = calculate_detailed_metrics(enterprise_df)
    
    # Process successful requests
    op_succ = operational_df[operational_df['success']] if not operational_df.empty else pd.DataFrame()
    ent_succ = enterprise_df[enterprise_df['success']] if not enterprise_df.empty else pd.DataFrame()
    
    # Create clean 2x2 layout
    fig = make_subplots(
        rows=3, cols=2,
        specs=[
            [{"type": "table", "colspan": 2}, None],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "xy", "colspan": 2}, None]
        ],
        vertical_spacing=0.1,
        horizontal_spacing=0.1,
        subplot_titles=(
            "📊 Detailed Performance Metrics",
            "⚡ Key Latency Metrics", "🚀 Throughput Comparison", 
            "📈 Performance Over Time"
        )
    )
    
    # 1. Detailed Summary Table
    summary_table = create_detailed_summary_table(op_metrics, ent_metrics)
    fig.add_trace(summary_table, row=1, col=1)
    
    # 2. Key Latency Metrics Comparison (Average, P95, P99)
    if op_metrics and ent_metrics:
        latency_metrics = ['Average', 'P95', 'P99']
        op_latencies = [op_metrics['avg_latency'], op_metrics['p95_latency'], op_metrics['p99_latency']]
        ent_latencies = [ent_metrics['avg_latency'], ent_metrics['p95_latency'], ent_metrics['p99_latency']]
        
        fig.add_trace(go.Bar(
            x=latency_metrics, y=op_latencies, 
            name='Operational SDK', 
            marker_color=COLORS['operational'],
            text=[f"{val:.1f}ms" for val in op_latencies],
            textposition='auto'
        ), row=2, col=1)
        
        fig.add_trace(go.Bar(
            x=latency_metrics, y=ent_latencies, 
            name='Enterprise SDK', 
            marker_color=COLORS['enterprise'],
            text=[f"{val:.1f}ms" for val in ent_latencies],
            textposition='auto'
        ), row=2, col=1)
    
    # 3. Throughput Comparison
    if op_metrics and ent_metrics:
        throughput_data = [op_metrics['throughput'], ent_metrics['throughput']]
        sdk_names = ['Operational SDK', 'Enterprise SDK']
        
        fig.add_trace(go.Bar(
            x=sdk_names, y=throughput_data,
            marker_color=[COLORS['operational'], COLORS['enterprise']],
            text=[f"{val:.1f}" for val in throughput_data],
            textposition='auto',
            showlegend=False
        ), row=2, col=2)
    
    # 4. Performance Over Time (Using sequence number instead of timestamp)
    if not op_succ.empty or not ent_succ.empty:
        # Create sequence numbers for time series (since timestamps are not reliable)
        if not op_succ.empty:
            op_time_series = op_succ.copy().reset_index(drop=True)
            op_time_series['sequence'] = range(len(op_time_series))
            
            # Sample data points for cleaner visualization
            sample_size = min(100, len(op_time_series))
            op_sampled = op_time_series.iloc[::len(op_time_series)//sample_size]
            
            fig.add_trace(go.Scatter(
                x=op_sampled['sequence'], 
                y=op_sampled['duration_ms'],
                mode='lines+markers',
                name='Operational SDK',
                line=dict(color=COLORS['operational'], width=3),
                marker=dict(size=6)
            ), row=3, col=1)
        
        if not ent_succ.empty:
            ent_time_series = ent_succ.copy().reset_index(drop=True)
            ent_time_series['sequence'] = range(len(ent_time_series))
            
            # Sample data points for cleaner visualization
            sample_size = min(100, len(ent_time_series))
            ent_sampled = ent_time_series.iloc[::len(ent_time_series)//sample_size]
            
            fig.add_trace(go.Scatter(
                x=ent_sampled['sequence'], 
                y=ent_sampled['duration_ms'],
                mode='lines+markers',
                name='Enterprise SDK',
                line=dict(color=COLORS['enterprise'], width=3),
                marker=dict(size=6)
            ), row=3, col=1)
    
    # Add metadata to title if available
    title_parts = ["Analytics SDK Performance Comparison"]
    if run_timestamp:
        title_parts.append(f"<span style='font-size:16px; color:#666;'>Run: {run_timestamp}</span>")
    if metadata:
        title_parts.append(f"<span style='font-size:14px; color:#888;'>Java {metadata.get('java_version', 'Unknown')} on {metadata.get('os_name', 'Unknown')}</span>")
    
    fig.update_layout(
        title={
            'text': "<br>".join(title_parts),
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#2c3e50'}
        },
        # ... rest of layout ...
    )
    
    # Update layout with clean, professional styling
    fig.update_layout(
        height=1200,
        title={
            'text': "Analytics SDK Performance Comparison<br><span style='font-size:16px; color:#666;'>Comprehensive Performance Analysis</span>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 24, 'color': '#2c3e50'}
        },
        showlegend=True,
        legend=dict(
            x=1.02,
            y=0.5,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.2)',
            borderwidth=1
        ),
        template='plotly_white',
        margin=dict(l=50, r=150, t=100, b=50)
    )
    
    # Update axes
    fig.update_xaxes(title_text="Latency Metrics", row=2, col=1)
    fig.update_yaxes(title_text="Latency (ms)", row=2, col=1)
    
    fig.update_xaxes(title_text="SDK", row=2, col=2)
    fig.update_yaxes(title_text="Throughput (req/s)", row=2, col=2)
    
    fig.update_xaxes(title_text="Request Sequence", row=3, col=1)
    fig.update_yaxes(title_text="Latency (ms)", row=3, col=1)
    
    # Save dashboard
    fig.write_html(dashboard_file, 
                   include_plotlyjs=True, 
                   config={'displayModeBar': False})
    
    logger.info(f"Developer dashboard saved to: {dashboard_file}")
    return op_metrics, ent_metrics

def print_comparison_summary(op_metrics, ent_metrics):
    """Print a detailed comparison summary to console."""
    print("=" * 80)
    print("🚀 ANALYTICS SDK PERFORMANCE COMPARISON")
    print("=" * 80)
    
    if not op_metrics or not ent_metrics:
        print("❌ Unable to generate comparison - missing metrics data")
        return
    
    # Create comparison table
    print("📊 DETAILED COMPARISON:")
    print(f"{'':24} {'Operational':>12} {'Enterprise':>12}")
    print("-" * 50)
    print(f"{'Success Rate:':<24} {op_metrics['success_rate']:>10.1f}% {ent_metrics['success_rate']:>10.1f}%")
    print(f"{'Throughput:':<24} {op_metrics['throughput']:>10.1f} rps {ent_metrics['throughput']:>10.1f} rps")
    print(f"{'Average Latency:':<24} {op_metrics['avg_latency']:>10.1f}ms {ent_metrics['avg_latency']:>10.1f}ms")
    print(f"{'Min Latency:':<24} {op_metrics['min_latency']:>10.1f}ms {ent_metrics['min_latency']:>10.1f}ms")
    print(f"{'Max Latency:':<24} {op_metrics['max_latency']:>10.1f}ms {ent_metrics['max_latency']:>10.1f}ms")
    print(f"{'Std Deviation:':<24} {op_metrics['std_latency']:>10.1f}ms {ent_metrics['std_latency']:>10.1f}ms")
    print(f"{'95th Percentile:':<24} {op_metrics['p95_latency']:>10.1f}ms {ent_metrics['p95_latency']:>10.1f}ms")
    print(f"{'99th Percentile:':<24} {op_metrics['p99_latency']:>10.1f}ms {ent_metrics['p99_latency']:>10.1f}ms")
    
    # Performance analysis
    print("\n🏆 PERFORMANCE ANALYSIS:")
    
    # Latency comparison
    if ent_metrics['avg_latency'] < op_metrics['avg_latency']:
        diff = op_metrics['avg_latency'] - ent_metrics['avg_latency']
        print(f"⚡ Lower Average Latency: Enterprise SDK ({diff:.1f}ms faster)")
    else:
        diff = ent_metrics['avg_latency'] - op_metrics['avg_latency']
        print(f"⚡ Lower Average Latency: Operational SDK ({diff:.1f}ms faster)")
    
    # P95 comparison
    if ent_metrics['p95_latency'] < op_metrics['p95_latency']:
        diff = op_metrics['p95_latency'] - ent_metrics['p95_latency']
        print(f"📊 Better P95 Latency: Enterprise SDK ({diff:.1f}ms better)")
    else:
        diff = ent_metrics['p95_latency'] - op_metrics['p95_latency']
        print(f"📊 Better P95 Latency: Operational SDK ({diff:.1f}ms better)")
    
    # Throughput comparison
    if ent_metrics['throughput'] > op_metrics['throughput']:
        diff = ent_metrics['throughput'] - op_metrics['throughput']
        print(f"🚀 Higher Throughput: Enterprise SDK (+{diff:.1f} rps)")
    else:
        diff = op_metrics['throughput'] - ent_metrics['throughput']
        print(f"🚀 Higher Throughput: Operational SDK (+{diff:.1f} rps)")
    
    # Consistency comparison
    if ent_metrics['std_latency'] < op_metrics['std_latency']:
        print(f"📈 More Consistent: Enterprise SDK (lower std dev)")
    else:
        print(f"📈 More Consistent: Operational SDK (lower std dev)")
    
    print(f"\n📋 Full dashboard: {DASHBOARD_FILE}")
    print("=" * 80)

def main():
    """Main function to generate the performance dashboard."""
    parser = argparse.ArgumentParser(description='Generate Analytics SDK Performance Dashboard')
    parser.add_argument('--output', '-o', help='Output HTML file path')
    parser.add_argument('--operational-data', help='Operational SDK results file')
    parser.add_argument('--enterprise-data', help='Enterprise SDK results file')
    parser.add_argument('--run-timestamp', help='Run timestamp for this analysis')
    parser.add_argument('--run-dir', help='Run directory (auto-detects files)')
    
    args = parser.parse_args()
    
    # Auto-detect file paths if run-dir is provided
    if args.run_dir:
        run_path = Path(args.run_dir)
        args.operational_data = args.operational_data or str(run_path / "raw" / "operational.jsonl")
        args.enterprise_data = args.enterprise_data or str(run_path / "raw" / "enterprise.jsonl") 
        args.output = args.output or str(run_path / "reports" / "dashboard.html")
    
    # Use latest results if no specific files provided
    if not args.operational_data:
        latest_dir = Path(__file__).parent.parent / "results" / "latest"
        if latest_dir.exists():
            args.operational_data = str(latest_dir / "raw" / "operational.jsonl")
            args.enterprise_data = str(latest_dir / "raw" / "enterprise.jsonl")
            args.output = str(latest_dir / "reports" / "dashboard.html")
    
    # Load test metadata if available
    metadata = load_test_metadata(args)
    
    # Load data
    logger.info("Loading performance data...")
    operational_df = load_data(Path(args.operational_data))
    enterprise_df = load_data(Path(args.enterprise_data))
    
    if operational_df.empty and enterprise_df.empty:
        logger.error("No data found in either file. Please run the performance tests first.")
        sys.exit(1)
    
    logger.info(f"Loaded {len(operational_df)} operational and {len(enterprise_df)} enterprise results")
    
    # Generate dashboard with metadata and output path
    op_metrics, ent_metrics = create_developer_dashboard(
        operational_df, enterprise_df, metadata, args.run_timestamp, args.output
    )
    
    # Print summary
    print_comparison_summary(op_metrics, ent_metrics)
    
    logger.info(f"Dashboard generated successfully: {args.output}")

def load_test_metadata(args):
    """Load test metadata if available."""
    metadata_file = None
    
    if args.run_dir:
        metadata_file = Path(args.run_dir) / "raw" / "test-metadata.json"
    elif args.operational_data:
        metadata_file = Path(args.operational_data).parent / "test-metadata.json"
    
    if metadata_file and metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load metadata: {e}")
    
    return None

if __name__ == "__main__":
    main()
