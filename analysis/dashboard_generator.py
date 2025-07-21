#!/usr/bin/env python3
"""
Analytics SDK Performance Test Result Analyzer

Generates developer-friendly HTML dashboard from JSONL test results
Supports single-language comparisons (Java vs Java or Go vs Go)
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
import glob
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Colors for SDKs
COLORS = {
    'operational': '#1f77b4',  # Blue
    'enterprise': '#d62728'    # Red
}

# Global constants
DASHBOARD_FILE = Path(__file__).parent.parent / "results" / "latest" / "reports" / "dashboard.html"

def load_config():
    """Load configuration from config.yaml."""
    try:
        config_path = Path(__file__).parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("config.yaml not found, using default duration")
        return None

def load_data(file_path):
    """Loads JSONL data, returns an empty DataFrame if file is missing or empty."""
    if not file_path.exists() or os.path.getsize(file_path) == 0:
        logger.warning(f"Data file not found or is empty: {file_path}")
        return pd.DataFrame()
    return pd.read_json(file_path, lines=True)

def auto_detect_result_files(run_dir):
    """Auto-detect available result files in the run directory."""
    raw_dir = Path(run_dir) / "raw"
    if not raw_dir.exists():
        return {}, None
    
    # Look for language-specific files first, then fallback to legacy
    files = {}
    language = None
    
    # Check for language-specific files
    patterns = {
        'java': ['operational-java.jsonl', 'enterprise-java.jsonl'],
        'go': ['operational-go.jsonl', 'enterprise-go.jsonl']
    }
    
    for lang, file_patterns in patterns.items():
        found_files = []
        for pattern in file_patterns:
            file_path = raw_dir / pattern
            if file_path.exists() and os.path.getsize(file_path) > 0:
                found_files.append(file_path)
        
        if found_files:
            language = lang
            for file_path in found_files:
                sdk_type = file_path.stem.replace(f'-{lang}', '')
                files[sdk_type] = {
                    'path': file_path,
                    'sdk_type': sdk_type,
                    'language': lang,
                    'display_name': f"{sdk_type.title()} SDK"
                }
            break
    
    # Fallback to legacy format if no language-specific files found
    if not files:
        legacy_patterns = ['operational.jsonl', 'enterprise.jsonl']
        for pattern in legacy_patterns:
            file_path = raw_dir / pattern
            if file_path.exists() and os.path.getsize(file_path) > 0:
                sdk_type = pattern.replace('.jsonl', '')
                files[sdk_type] = {
                    'path': file_path,
                    'sdk_type': sdk_type,
                    'language': 'unknown',
                    'display_name': f"{sdk_type.title()} SDK"
                }
        language = 'unknown'
    
    return files, language

def calculate_detailed_metrics(df, language="unknown"):
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
            'test_duration_s': test_duration_s,
            'language': language
        }
    
    # Calculate throughput using actual test duration from timestamps
    if 'timestamp' in successful_df.columns and len(successful_df) > 1:
        timestamps = successful_df['timestamp']
        
        if hasattr(timestamps.iloc[0], 'timestamp'):
            start_ms = timestamps.min().timestamp() * 1000
            end_ms = timestamps.max().timestamp() * 1000
        else:
            start_ms = float(timestamps.min())
            end_ms = float(timestamps.max())
        
        actual_duration_s = (end_ms - start_ms) / 1000.0
        actual_duration_s = max(actual_duration_s, 1.0)
        
        throughput = success_count / actual_duration_s
        final_test_duration_s = actual_duration_s
    else:
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
        'test_duration_s': final_test_duration_s,
        'language': language
    }

def create_summary_table(operational_metrics, enterprise_metrics, language):
    """Create summary table for operational vs enterprise comparison."""
    metrics_data = []
    
    for name, metrics in [("Operational SDK", operational_metrics), 
                         ("Enterprise SDK", enterprise_metrics)]:
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

def create_sdk_comparison_dashboard(data_files, language, operational_metrics, enterprise_metrics, 
                                  run_timestamp=None, output_path=None):
    """Creates a dashboard comparing operational vs enterprise SDKs for a single language."""
    logger.info(f"Generating {language.upper()} SDK comparison dashboard...")
    
    dashboard_file = Path(output_path) if output_path else DASHBOARD_FILE
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create layout matching the user's request: Summary table, Key Latency Metrics, Throughput Comparison, Performance Over Time
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=[
            "📊 Detailed Performance Metrics", "",
            "⚡ Key Latency Metrics", "🚀 Throughput Comparison",
            "📈 Performance Over Time", ""
        ],
        specs=[
            [{"type": "table", "colspan": 2}, None],  # Summary table spans both columns
            [{"type": "xy"}, {"type": "xy"}],         # Latency metrics | Throughput comparison
            [{"type": "xy", "colspan": 2}, None]      # Performance over time spans both columns
        ],
        vertical_spacing=0.12,  # More space between rows
        horizontal_spacing=0.1,
        row_heights=[0.25, 0.35, 0.4]  # Allocate more space to the performance over time chart
    )
    
    # Add summary table
    fig.add_trace(create_summary_table(operational_metrics, enterprise_metrics, language), 
                  row=1, col=1)
    
    # Load dataframes
    operational_df = pd.DataFrame()
    enterprise_df = pd.DataFrame()
    
    if 'operational' in data_files:
        operational_df = load_data(data_files['operational']['path'])
    if 'enterprise' in data_files:
        enterprise_df = load_data(data_files['enterprise']['path'])
    
    # Key Latency Metrics (grouped bar chart)
    latency_categories = ['Average', 'P95', 'P99']
    operational_latencies = []
    enterprise_latencies = []
    
    if operational_metrics:
        operational_latencies = [
            operational_metrics['avg_latency'],
            operational_metrics['p95_latency'], 
            operational_metrics['p99_latency']
        ]
    
    if enterprise_metrics:
        enterprise_latencies = [
            enterprise_metrics['avg_latency'],
            enterprise_metrics['p95_latency'],
            enterprise_metrics['p99_latency']
        ]
    
    if operational_latencies:
        fig.add_trace(go.Bar(
            x=latency_categories,
            y=operational_latencies,
            name='Operational SDK',
            marker_color=COLORS['operational'],
            text=[f'{val:.1f}ms' for val in operational_latencies],
            textposition='outside'
        ), row=2, col=1)
    
    if enterprise_latencies:
        fig.add_trace(go.Bar(
            x=latency_categories,
            y=enterprise_latencies,
            name='Enterprise SDK',
            marker_color=COLORS['enterprise'],
            text=[f'{val:.1f}ms' for val in enterprise_latencies],
            textposition='outside'
        ), row=2, col=1)
    
    # Throughput Comparison
    if operational_metrics and enterprise_metrics:
        fig.add_trace(go.Bar(
            x=['Operational SDK', 'Enterprise SDK'],
            y=[operational_metrics['throughput'], enterprise_metrics['throughput']],
            marker_color=[COLORS['operational'], COLORS['enterprise']],
            text=[f"{operational_metrics['throughput']:.1f}", f"{enterprise_metrics['throughput']:.1f}"],
            textposition='outside',
            showlegend=False
        ), row=2, col=2)
    elif operational_metrics:
        fig.add_trace(go.Bar(
            x=['Operational SDK'],
            y=[operational_metrics['throughput']],
            marker_color=[COLORS['operational']],
            text=[f"{operational_metrics['throughput']:.1f}"],
            textposition='outside',
            showlegend=False
        ), row=2, col=2)
    elif enterprise_metrics:
        fig.add_trace(go.Bar(
            x=['Enterprise SDK'],
            y=[enterprise_metrics['throughput']],
            marker_color=[COLORS['enterprise']],
            text=[f"{enterprise_metrics['throughput']:.1f}"],
            textposition='outside',
            showlegend=False
        ), row=2, col=2)
    
    # Performance Over Time (line chart with proper timestamp overlap)
    # Find the earliest start time to create relative timestamps
    all_start_times = []
    
    if not operational_df.empty:
        op_successful = operational_df[operational_df['success']]
        if not op_successful.empty and 'start_time' in op_successful.columns:
            all_start_times.extend(op_successful['start_time'].tolist())
    
    if not enterprise_df.empty:
        ent_successful = enterprise_df[enterprise_df['success']]
        if not ent_successful.empty and 'start_time' in ent_successful.columns:
            all_start_times.extend(ent_successful['start_time'].tolist())
    
    if all_start_times:
        # Convert nanoseconds to seconds relative to test start
        earliest_start = min(all_start_times)
        
        # Plot operational SDK
        if not operational_df.empty:
            op_successful = operational_df[operational_df['success']]
            if not op_successful.empty and len(op_successful) > 1:
                # Convert nanosecond timestamps to relative seconds
                relative_times = (op_successful['start_time'] - earliest_start) / 1_000_000_000
                
                # Sample data for cleaner visualization (every 10th point)
                if len(op_successful) > 500:
                    step = len(op_successful) // 500
                    op_sampled = op_successful.iloc[::step]
                    sampled_times = relative_times.iloc[::step]
                else:
                    op_sampled = op_successful
                    sampled_times = relative_times
                
                fig.add_trace(go.Scatter(
                    x=sampled_times,
                    y=op_sampled['duration_ms'],
                    mode='lines+markers',
                    name='Operational SDK',
                    line=dict(color=COLORS['operational'], width=2),
                    marker=dict(size=3),
                    opacity=0.7
                ), row=3, col=1)
        
        # Plot enterprise SDK
        if not enterprise_df.empty:
            ent_successful = enterprise_df[enterprise_df['success']]
            if not ent_successful.empty and len(ent_successful) > 1:
                # Convert nanosecond timestamps to relative seconds
                relative_times = (ent_successful['start_time'] - earliest_start) / 1_000_000_000
                
                # Sample data for cleaner visualization (every 10th point)
                if len(ent_successful) > 500:
                    step = len(ent_successful) // 500
                    ent_sampled = ent_successful.iloc[::step]
                    sampled_times = relative_times.iloc[::step]
                else:
                    ent_sampled = ent_successful
                    sampled_times = relative_times
                
                fig.add_trace(go.Scatter(
                    x=sampled_times,
                    y=ent_sampled['duration_ms'],
                    mode='lines+markers',
                    name='Enterprise SDK',
                    line=dict(color=COLORS['enterprise'], width=2),
                    marker=dict(size=3),
                    opacity=0.7
                ), row=3, col=1)
    
    # Update layout with increased height
    title_parts = ["Analytics SDK Performance Comparison"]
    if run_timestamp:
        title_parts.append(f"<span style='font-size:16px; color:#666;'>Run: {run_timestamp}</span>")
    title_parts.append(f"<span style='font-size:14px; color:#888;'>Comprehensive Performance Analysis</span>")
    
    fig.update_layout(
        height=1400,  # Increased height for better readability
        title={
            'text': "<br>".join(title_parts),
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
        margin=dict(l=50, r=150, t=120, b=50)
    )
    
    # Update axis labels
    fig.update_xaxes(title_text="Latency Metrics", row=2, col=1)
    fig.update_yaxes(title_text="Latency (ms)", row=2, col=1)
    
    fig.update_xaxes(title_text="SDK", row=2, col=2)
    fig.update_yaxes(title_text="Throughput (req/s)", row=2, col=2)
    
    fig.update_xaxes(title_text="Time (seconds)", row=3, col=1)
    fig.update_yaxes(title_text="Latency (ms)", row=3, col=1)
    
    # Save dashboard
    fig.write_html(dashboard_file, 
                   include_plotlyjs=True, 
                   config={'displayModeBar': False})
    
    logger.info(f"{language.upper()} SDK dashboard saved to: {dashboard_file}")
    return operational_metrics, enterprise_metrics

def print_sdk_comparison_summary(operational_metrics, enterprise_metrics, language):
    """Print a detailed comparison summary for operational vs enterprise SDKs."""
    print("=" * 80)
    print(f"🚀 {language.upper()} ANALYTICS SDK PERFORMANCE COMPARISON")
    print("=" * 80)
    
    if not operational_metrics and not enterprise_metrics:
        print("❌ No metrics data available")
        return
    
    # Print detailed table
    print("📊 DETAILED COMPARISON:")
    print(f"{'SDK Type':20} {'Success Rate':>12} {'Throughput':>12} {'Avg Latency':>12} {'P95 Latency':>12}")
    print("-" * 70)
    
    if operational_metrics:
        print(f"{'Operational':20} {operational_metrics['success_rate']:>10.1f}% {operational_metrics['throughput']:>10.1f} rps {operational_metrics['avg_latency']:>10.1f}ms {operational_metrics['p95_latency']:>10.1f}ms")
    
    if enterprise_metrics:
        print(f"{'Enterprise':20} {enterprise_metrics['success_rate']:>10.1f}% {enterprise_metrics['throughput']:>10.1f} rps {enterprise_metrics['avg_latency']:>10.1f}ms {enterprise_metrics['p95_latency']:>10.1f}ms")
    
    # SDK comparison
    if operational_metrics and enterprise_metrics:
        print("\n🏆 SDK COMPARISON:")
        
        # Latency comparison
        if enterprise_metrics['avg_latency'] < operational_metrics['avg_latency']:
            diff = operational_metrics['avg_latency'] - enterprise_metrics['avg_latency']
            print(f"⚡ Lower Average Latency: Enterprise SDK ({diff:.1f}ms faster)")
        elif operational_metrics['avg_latency'] < enterprise_metrics['avg_latency']:
            diff = enterprise_metrics['avg_latency'] - operational_metrics['avg_latency']
            print(f"⚡ Lower Average Latency: Operational SDK ({diff:.1f}ms faster)")
        else:
            print(f"⚡ Average Latency: Both SDKs perform similarly")
        
        # Throughput comparison
        if enterprise_metrics['throughput'] > operational_metrics['throughput']:
            diff = enterprise_metrics['throughput'] - operational_metrics['throughput']
            print(f"🚀 Higher Throughput: Enterprise SDK (+{diff:.1f} rps)")
        elif operational_metrics['throughput'] > enterprise_metrics['throughput']:
            diff = operational_metrics['throughput'] - enterprise_metrics['throughput']
            print(f"🚀 Higher Throughput: Operational SDK (+{diff:.1f} rps)")
        else:
            print(f"🚀 Throughput: Both SDKs perform similarly")
        
        # P95 comparison
        if enterprise_metrics['p95_latency'] < operational_metrics['p95_latency']:
            diff = operational_metrics['p95_latency'] - enterprise_metrics['p95_latency']
            print(f"📊 Better P95 Latency: Enterprise SDK ({diff:.1f}ms better)")
        elif operational_metrics['p95_latency'] < enterprise_metrics['p95_latency']:
            diff = enterprise_metrics['p95_latency'] - operational_metrics['p95_latency']
            print(f"📊 Better P95 Latency: Operational SDK ({diff:.1f}ms better)")
    
    print("\n📋 Full dashboard with detailed charts has been generated")
    print("=" * 80)

def main():
    """Main function to generate the performance dashboard."""
    parser = argparse.ArgumentParser(description='Generate Analytics SDK Performance Dashboard')
    parser.add_argument('--output', '-o', help='Output HTML file path')
    parser.add_argument('--run-timestamp', help='Run timestamp for this analysis')
    parser.add_argument('--run-dir', help='Run directory (auto-detects files)')
    
    args = parser.parse_args()
    
    # Auto-detect file paths if run-dir is provided
    if args.run_dir:
        run_path = Path(args.run_dir)
        data_files, language = auto_detect_result_files(run_path)
        args.output = args.output or str(run_path / "reports" / "dashboard.html")
    else:
        # Use latest results
        latest_dir = Path(__file__).parent.parent / "results" / "latest"
        if latest_dir.exists():
            data_files, language = auto_detect_result_files(latest_dir)
            args.output = args.output or str(latest_dir / "reports" / "dashboard.html")
        else:
            data_files, language = {}, None
    
    if not data_files:
        logger.error("No data files found. Please run the performance tests first.")
        print("Expected files in raw/ directory:")
        print("  For Go: operational-go.jsonl, enterprise-go.jsonl")
        print("  For Java: operational-java.jsonl, enterprise-java.jsonl")
        print("  Legacy: operational.jsonl, enterprise.jsonl")
        sys.exit(1)
    
    logger.info(f"Found {len(data_files)} result files for {language.upper()}:")
    for key, file_info in data_files.items():
        logger.info(f"  - {file_info['display_name']}: {file_info['path']}")
    
    # Calculate metrics for available datasets
    operational_metrics = None
    enterprise_metrics = None
    
    if 'operational' in data_files:
        df = load_data(data_files['operational']['path'])
        if not df.empty:
            operational_metrics = calculate_detailed_metrics(df, language)
            logger.info(f"Loaded {len(df)} results for Operational SDK")
    
    if 'enterprise' in data_files:
        df = load_data(data_files['enterprise']['path'])
        if not df.empty:
            enterprise_metrics = calculate_detailed_metrics(df, language)
            logger.info(f"Loaded {len(df)} results for Enterprise SDK")
    
    if not operational_metrics and not enterprise_metrics:
        logger.error("No valid data found in any file")
        sys.exit(1)
    
    # Generate dashboard
    create_sdk_comparison_dashboard(data_files, language, operational_metrics, enterprise_metrics, 
                                   args.run_timestamp, args.output)
    
    # Print summary
    print_sdk_comparison_summary(operational_metrics, enterprise_metrics, language)
    
    logger.info(f"Dashboard generated successfully: {args.output}")

if __name__ == "__main__":
    main()
