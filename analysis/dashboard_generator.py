#!/usr/bin/env python3
"""
Analytics SDK Performance Test Result Analyzer

Generates developer-friendly HTML dashboard from JSONL test results
Supports single-language comparisons (Java vs Java, Go vs Go, or Python vs Python)
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
        'go': ['operational-go.jsonl', 'enterprise-go.jsonl'],
        'python': ['operational-python.jsonl', 'enterprise-python.jsonl']
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
    
    if success_count == 0:
        return {
            'total_requests': total_requests,
            'successful_requests': success_count,
            'success_rate': success_rate,
            'throughput_rps': 0,
            'error': "No successful requests to analyze"
        }
    
    # Calculate throughput (requests per second)
    throughput_rps = success_count / test_duration_s
    
    # Get timing data for successful requests only
    durations = successful_df['duration_ms']
    
    return {
        'total_requests': total_requests,
        'successful_requests': success_count,
        'success_rate': success_rate,
        'throughput_rps': throughput_rps,
        'mean_latency': durations.mean(),
        'median_latency': durations.median(),
        'p95_latency': durations.quantile(0.95),
        'p99_latency': durations.quantile(0.99),
        'min_latency': durations.min(),
        'max_latency': durations.max(),
        'std_latency': durations.std(),
        'language': language
    }

def create_latency_histogram(operational_df, enterprise_df, language="unknown"):
    """Create overlapping histogram of latency distributions."""
    fig = go.Figure()
    
    logger.info(f"create_latency_histogram: operational={len(operational_df)}, enterprise={len(enterprise_df)}")
    
    has_data = False
    
    # Process operational data
    if not operational_df.empty:
        op_successful = operational_df[operational_df['success']]
        logger.info(f"Operational successful records: {len(op_successful)}")
        
        if not op_successful.empty:
            # Get duration values and convert to plain Python list
            durations = op_successful['duration_ms'].values.tolist()
            logger.info(f"Operational durations: {len(durations)} values")
            logger.info(f"Operational sample: {durations[:5]}")
            logger.info(f"Operational range: {min(durations):.2f} to {max(durations):.2f}")
            
            fig.add_trace(go.Histogram(
                x=durations,
                name='Operational SDK',
                opacity=0.7,
                marker_color=COLORS['operational'],
                xbins=dict(size=2.0)  # Fixed bin size of 2ms
            ))
            has_data = True
    
    # Process enterprise data
    if not enterprise_df.empty:
        ent_successful = enterprise_df[enterprise_df['success']]
        logger.info(f"Enterprise successful records: {len(ent_successful)}")
        
        if not ent_successful.empty:
            # Get duration values and convert to plain Python list
            durations = ent_successful['duration_ms'].values.tolist()
            logger.info(f"Enterprise durations: {len(durations)} values")
            logger.info(f"Enterprise sample: {durations[:5]}")
            logger.info(f"Enterprise range: {min(durations):.2f} to {max(durations):.2f}")
            
            fig.add_trace(go.Histogram(
                x=durations,
                name='Enterprise SDK',
                opacity=0.7,
                marker_color=COLORS['enterprise'],
                xbins=dict(size=2.0)  # Fixed bin size of 2ms
            ))
            has_data = True
    
    if not has_data:
        logger.warning("No data found for histogram")
        fig.update_layout(
            title=f'Query Latency Distribution ({language.title()})',
            xaxis_title='Latency (ms)',
            yaxis_title='Count',
            template='plotly_white',
            annotations=[{
                'text': 'No data available',
                'x': 0.5, 'y': 0.5,
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False,
                'font': {'size': 16, 'color': 'gray'}
            }]
        )
    else:
        fig.update_layout(
            title=f'Query Latency Distribution ({language.title()})',
            xaxis_title='Latency (ms)',
            yaxis_title='Count',
            barmode='overlay',
            template='plotly_white',
            height=500
        )
    
    logger.info(f"Histogram created with {len(fig.data)} traces")
    return fig

def create_latency_timeseries(operational_df, enterprise_df, language="unknown"):
    """Create time series plot of query latencies over actual elapsed time."""
    fig = go.Figure()
    
    # Debug logging
    logger.info(f"create_latency_timeseries: operational={len(operational_df)}, enterprise={len(enterprise_df)}")

    # Get successful data with explicit boolean check
    op_successful = pd.DataFrame()
    ent_successful = pd.DataFrame()
    
    if not operational_df.empty:
        op_successful = operational_df[operational_df['success']].copy()
        logger.info(f"Operational successful records: {len(op_successful)}")
    
    if not enterprise_df.empty:
        ent_successful = enterprise_df[enterprise_df['success']].copy()
        logger.info(f"Enterprise successful records: {len(ent_successful)}")

    # Check if we have any data to plot
    if op_successful.empty and ent_successful.empty:
        logger.warning("No successful data found for latency time series")
        fig.update_layout(
            title=f'Query Latency Over Time ({language.title()})',
            xaxis_title='Elapsed Time (seconds)',
            yaxis_title='Latency (ms)',
            template='plotly_white',
            annotations=[{
                'text': 'No successful requests found',
                'x': 0.5, 'y': 0.5,
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False,
                'font': {'size': 16, 'color': 'gray'}
            }]
        )
        return fig

    # Find global start time for consistent X-axis
    all_times = []
    if not op_successful.empty:
        all_times.extend(op_successful['absolute_start_time_ms'].astype(float).tolist())
    if not ent_successful.empty:
        all_times.extend(ent_successful['absolute_start_time_ms'].astype(float).tolist())
    
    global_start_time = min(all_times)
    logger.info(f"Global start time: {global_start_time}, total time points: {len(all_times)}")

    # Plot operational data
    if not op_successful.empty:
        # Calculate elapsed seconds from global start
        elapsed_seconds = (op_successful['absolute_start_time_ms'].astype(float) - global_start_time) / 1000.0
        duration_ms = op_successful['duration_ms'].astype(float)
        
        logger.info(f"Operational: {len(elapsed_seconds)} points, time range: {elapsed_seconds.min():.1f}-{elapsed_seconds.max():.1f}s")
        
        fig.add_trace(go.Scatter(
            x=elapsed_seconds,
            y=duration_ms,
            mode='markers',
            name='Operational SDK',
            marker=dict(color=COLORS['operational'], size=4, opacity=0.6),
            hovertemplate='<b>Operational SDK</b><br>Time: %{x:.1f}s<br>Latency: %{y:.2f}ms<br>Seq: ' + 
                         op_successful['sequence_number'].astype(str) + '<extra></extra>'
        ))

    # Plot enterprise data  
    if not ent_successful.empty:
        # Calculate elapsed seconds from global start
        elapsed_seconds = (ent_successful['absolute_start_time_ms'].astype(float) - global_start_time) / 1000.0
        duration_ms = ent_successful['duration_ms'].astype(float)
        
        logger.info(f"Enterprise: {len(elapsed_seconds)} points, time range: {elapsed_seconds.min():.1f}-{elapsed_seconds.max():.1f}s")
        
        fig.add_trace(go.Scatter(
            x=elapsed_seconds,
            y=duration_ms,
            mode='markers',
            name='Enterprise SDK',
            marker=dict(color=COLORS['enterprise'], size=4, opacity=0.6),
            hovertemplate='<b>Enterprise SDK</b><br>Time: %{x:.1f}s<br>Latency: %{y:.2f}ms<br>Seq: ' + 
                         ent_successful['sequence_number'].astype(str) + '<extra></extra>'
        ))
    
    fig.update_layout(
        title=f'Query Latency Over Time ({language.title()})',
        xaxis_title='Elapsed Time (seconds)',
        yaxis_title='Latency (ms)',
        template='plotly_white',
        showlegend=True,
        height=500
    )
    
    return fig

def create_latency_by_sequence(operational_df, enterprise_df, language="unknown"):
    """Create alternative plot showing latency by sequence number."""
    fig = go.Figure()
    
    logger.info(f"create_latency_by_sequence: operational={len(operational_df)}, enterprise={len(enterprise_df)}")

    # Get successful data
    if not operational_df.empty:
        op_successful = operational_df[operational_df['success']].copy()
        if not op_successful.empty:
            # Sort by sequence number to ensure proper order
            op_successful = op_successful.sort_values('sequence_number')
            
            fig.add_trace(go.Scatter(
                x=op_successful['sequence_number'],
                y=op_successful['duration_ms'].astype(float),
                mode='markers',
                name='Operational SDK',
                marker=dict(color=COLORS['operational'], size=4, opacity=0.6),
                hovertemplate='<b>Operational SDK</b><br>Query #%{x}<br>Latency: %{y:.2f}ms<extra></extra>'
            ))

    if not enterprise_df.empty:
        ent_successful = enterprise_df[enterprise_df['success']].copy()
        if not ent_successful.empty:
            # Sort by sequence number to ensure proper order
            ent_successful = ent_successful.sort_values('sequence_number')
            
            fig.add_trace(go.Scatter(
                x=ent_successful['sequence_number'],
                y=ent_successful['duration_ms'].astype(float),
                mode='markers',
                name='Enterprise SDK',
                marker=dict(color=COLORS['enterprise'], size=4, opacity=0.6),
                hovertemplate='<b>Enterprise SDK</b><br>Query #%{x}<br>Latency: %{y:.2f}ms<extra></extra>'
            ))
    
    fig.update_layout(
        title=f'Query Latency by Sequence ({language.title()})',
        xaxis_title='Query Sequence Number',
        yaxis_title='Latency (ms)',
        template='plotly_white',
        showlegend=True,
        height=500
    )
    
    return fig

def create_throughput_timeseries(operational_df, enterprise_df, language="unknown", window_size_seconds=5):
    """Create time series plot of throughput over time using sliding window."""
    fig = go.Figure()
    
    logger.info(f"create_throughput_timeseries: operational={len(operational_df)}, enterprise={len(enterprise_df)}")

    # Get successful data
    datasets = {}
    global_times = []
    
    if not operational_df.empty:
        op_successful = operational_df[operational_df['success']].copy()
        if not op_successful.empty:
            datasets['Operational SDK'] = op_successful
            global_times.extend(op_successful['absolute_start_time_ms'].astype(float).tolist())
    
    if not enterprise_df.empty:
        ent_successful = enterprise_df[enterprise_df['success']].copy()
        if not ent_successful.empty:
            datasets['Enterprise SDK'] = ent_successful
            global_times.extend(ent_successful['absolute_start_time_ms'].astype(float).tolist())
    
    if not global_times:
        logger.warning("No data for throughput calculation")
        fig.update_layout(
            title=f'Throughput Over Time ({language.title()}) - {window_size_seconds}s Windows',
            xaxis_title='Elapsed Time (seconds)',
            yaxis_title='Throughput (RPS)',
            template='plotly_white',
            annotations=[{
                'text': 'No data available',
                'x': 0.5, 'y': 0.5,
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False,
                'font': {'size': 16, 'color': 'gray'}
            }]
        )
        return fig

    # Find global time range
    global_start = min(global_times)
    global_end = max(global_times)
    total_duration = (global_end - global_start) / 1000.0
    
    logger.info(f"Throughput calculation: {total_duration:.1f}s duration, {len(datasets)} datasets")

    # Create time windows
    num_windows = max(1, int(total_duration / window_size_seconds))
    time_windows = np.linspace(0, total_duration, num_windows + 1)
    
    for sdk_name, df in datasets.items():
        if df.empty:
            continue
            
        # Calculate elapsed time for this dataset
        elapsed_times = (df['absolute_start_time_ms'].astype(float) - global_start) / 1000.0
        
        # Calculate throughput for each window
        window_centers = []
        throughputs = []
        
        for i in range(len(time_windows) - 1):
            window_start = time_windows[i]
            window_end = time_windows[i + 1]
            window_center = (window_start + window_end) / 2
            
            # Count requests in this window
            requests_in_window = ((elapsed_times >= window_start) & (elapsed_times < window_end)).sum()
            throughput = requests_in_window / window_size_seconds
            
            window_centers.append(window_center)
            throughputs.append(throughput)
        
        if window_centers:
            color = COLORS['operational'] if sdk_name == 'Operational SDK' else COLORS['enterprise']
            
            logger.info(f"{sdk_name}: {len(window_centers)} windows, max throughput: {max(throughputs):.2f} RPS")
                
            fig.add_trace(go.Scatter(
                x=window_centers,
                y=throughputs,
                    mode='lines+markers',
                name=sdk_name,
                line=dict(color=color, width=2),
                marker=dict(color=color, size=6),
                hovertemplate=f'<b>{sdk_name}</b><br>Time: %{{x:.1f}}s<br>Throughput: %{{y:.2f}} RPS<extra></extra>'
            ))
    
    fig.update_layout(
        title=f'Throughput Over Time ({language.title()}) - {window_size_seconds}s Windows',
        xaxis_title='Elapsed Time (seconds)',
        yaxis_title='Throughput (RPS)',
        template='plotly_white',
        showlegend=True,
        height=500
    )
    
    return fig

def create_percentile_comparison(operational_metrics, enterprise_metrics, language="unknown"):
    """Create bar chart comparing latency percentiles."""
    percentiles = ['min_latency', 'median_latency', 'p95_latency', 'p99_latency', 'max_latency']
    percentile_labels = ['Min', 'Median', 'P95', 'P99', 'Max']
    
    operational_values = [operational_metrics.get(p, 0) if operational_metrics else 0 for p in percentiles]
    enterprise_values = [enterprise_metrics.get(p, 0) if enterprise_metrics else 0 for p in percentiles]
    
    fig = go.Figure(data=[
        go.Bar(name='Operational SDK', x=percentile_labels, y=operational_values, marker_color=COLORS['operational']),
        go.Bar(name='Enterprise SDK', x=percentile_labels, y=enterprise_values, marker_color=COLORS['enterprise'])
    ])
    
    fig.update_layout(
        title=f'Latency Percentiles Comparison ({language.title()})',
        xaxis_title='Percentile',
        yaxis_title='Latency (ms)',
        barmode='group',
        template='plotly_white'
    )
    
    return fig

def create_throughput_comparison(operational_metrics, enterprise_metrics, language="unknown"):
    """Create bar chart comparing throughput."""
    sdks = []
    throughputs = []
    colors = []
    
    if operational_metrics:
        sdks.append('Operational SDK')
        throughputs.append(operational_metrics.get('throughput_rps', 0))
        colors.append(COLORS['operational'])
    
    if enterprise_metrics:
        sdks.append('Enterprise SDK')
        throughputs.append(enterprise_metrics.get('throughput_rps', 0))
        colors.append(COLORS['enterprise'])
    
    fig = go.Figure(data=[
        go.Bar(x=sdks, y=throughputs, marker_color=colors)
    ])
    
    fig.update_layout(
        title=f'Throughput Comparison ({language.title()})',
        xaxis_title='SDK',
        yaxis_title='Requests per Second (RPS)',
        template='plotly_white'
    )
    
    return fig

def create_success_rate_comparison(operational_metrics, enterprise_metrics, language="unknown"):
    """Create bar chart comparing success rates."""
    sdks = []
    success_rates = []
    colors = []
    
    if operational_metrics:
        sdks.append('Operational SDK')
        success_rates.append(operational_metrics.get('success_rate', 0))
        colors.append(COLORS['operational'])
    
    if enterprise_metrics:
        sdks.append('Enterprise SDK')  
        success_rates.append(enterprise_metrics.get('success_rate', 0))
        colors.append(COLORS['enterprise'])
    
    fig = go.Figure(data=[
        go.Bar(x=sdks, y=success_rates, marker_color=colors)
    ])
    
    fig.update_layout(
        title=f'Success Rate Comparison ({language.title()})',
        xaxis_title='SDK',
        yaxis_title='Success Rate (%)',
        template='plotly_white',
        yaxis=dict(range=[0, 105])  # Set range to 0-105% for better visualization
    )
    
    return fig

def create_metrics_table(operational_metrics, enterprise_metrics, language="unknown"):
    """Create HTML table with detailed metrics."""
    
    def format_metric(value, unit="", decimals=2):
        """Format a metric value with appropriate precision."""
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            if decimals == 0:
                return f"{int(value)}{unit}"
            else:
                return f"{value:.{decimals}f}{unit}"
        return str(value)
    
    # Define metrics to display
    metrics = [
        ('Total Requests', 'total_requests', '', 0),
        ('Successful Requests', 'successful_requests', '', 0),
        ('Success Rate', 'success_rate', '%', 2),
        ('Throughput', 'throughput_rps', ' RPS', 2),
        ('Mean Latency', 'mean_latency', ' ms', 2),
        ('Median Latency', 'median_latency', ' ms', 2),
        ('P95 Latency', 'p95_latency', ' ms', 2),
        ('P99 Latency', 'p99_latency', ' ms', 2),
        ('Min Latency', 'min_latency', ' ms', 2),
        ('Max Latency', 'max_latency', ' ms', 2),
        ('Std Dev Latency', 'std_latency', ' ms', 2)
    ]
    
    # Build HTML table
    table_html = f"""
    <div class="table-container">
        <h3>Performance Metrics Summary ({language.title()})</h3>
        <table class="metrics-table">
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Operational SDK</th>
                    <th>Enterprise SDK</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for metric_name, metric_key, unit, decimals in metrics:
        op_value = format_metric(operational_metrics.get(metric_key) if operational_metrics else None, unit, decimals)
        ent_value = format_metric(enterprise_metrics.get(metric_key) if enterprise_metrics else None, unit, decimals)
        
        table_html += f"""
                <tr>
                    <td>{metric_name}</td>
                    <td>{op_value}</td>
                    <td>{ent_value}</td>
                </tr>
        """
    
    table_html += """
            </tbody>
        </table>
    </div>
    """
    
    return table_html

def create_latency_progression(operational_df, enterprise_df, language="unknown"):
    """Create scatter plot showing latency progression by query sequence."""
    fig = go.Figure()
    
    logger.info(f"create_latency_progression: operational={len(operational_df)}, enterprise={len(enterprise_df)}")
    
    has_data = False
    
    # Process operational data
    if not operational_df.empty:
        op_successful = operational_df[operational_df['success']].copy()
        logger.info(f"Operational successful records: {len(op_successful)}")
        
        if not op_successful.empty:
            # Sort by sequence number to ensure proper order
            op_successful = op_successful.sort_values('sequence_number')
            
            sequence_nums = op_successful['sequence_number'].values.tolist()
            durations = op_successful['duration_ms'].values.tolist()
            
            logger.info(f"Operational: {len(sequence_nums)} points, sequence range: {min(sequence_nums)}-{max(sequence_nums)}")
            logger.info(f"Operational latency range: {min(durations):.2f}-{max(durations):.2f}ms")
            
            fig.add_trace(go.Scatter(
                x=sequence_nums,
                y=durations,
                mode='markers+lines',
                name='Operational SDK',
                marker=dict(color=COLORS['operational'], size=6, opacity=0.7),
                line=dict(color=COLORS['operational'], width=1, dash='dot'),
                hovertemplate='<b>Operational SDK</b><br>Query #%{x}<br>Latency: %{y:.2f}ms<extra></extra>'
            ))
            has_data = True
    
    # Process enterprise data
    if not enterprise_df.empty:
        ent_successful = enterprise_df[enterprise_df['success']].copy()
        logger.info(f"Enterprise successful records: {len(ent_successful)}")
        
        if not ent_successful.empty:
            # Sort by sequence number to ensure proper order
            ent_successful = ent_successful.sort_values('sequence_number')
            
            sequence_nums = ent_successful['sequence_number'].values.tolist()
            durations = ent_successful['duration_ms'].values.tolist()
            
            logger.info(f"Enterprise: {len(sequence_nums)} points, sequence range: {min(sequence_nums)}-{max(sequence_nums)}")
            logger.info(f"Enterprise latency range: {min(durations):.2f}-{max(durations):.2f}ms")
            
            fig.add_trace(go.Scatter(
                x=sequence_nums,
                y=durations,
                mode='markers+lines',
                name='Enterprise SDK',
                marker=dict(color=COLORS['enterprise'], size=6, opacity=0.7),
                line=dict(color=COLORS['enterprise'], width=1, dash='dot'),
                hovertemplate='<b>Enterprise SDK</b><br>Query #%{x}<br>Latency: %{y:.2f}ms<extra></extra>'
            ))
            has_data = True
    
    if not has_data:
        logger.warning("No data found for latency progression")
        fig.update_layout(
            title=f'Query Latency Progression ({language.title()})',
            xaxis_title='Query Sequence Number',
            yaxis_title='Latency (ms)',
            template='plotly_white',
            annotations=[{
                'text': 'No data available',
                'x': 0.5, 'y': 0.5,
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False,
                'font': {'size': 16, 'color': 'gray'}
            }]
        )
    else:
        fig.update_layout(
            title=f'Query Latency Progression ({language.title()})',
            xaxis_title='Query Sequence Number',
            yaxis_title='Latency (ms)',
            template='plotly_white',
            showlegend=True,
            height=600,
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)'
            )
        )
    
    logger.info(f"Latency progression plot created with {len(fig.data)} traces")
    return fig

def generate_html_dashboard(operational_metrics, enterprise_metrics, language="unknown", operational_df=None, enterprise_df=None):
    """Generate complete HTML dashboard."""
    
    # Handle None DataFrames
    if operational_df is None:
        operational_df = pd.DataFrame()
    if enterprise_df is None:
        enterprise_df = pd.DataFrame()
    
    # Create all visualizations
    latency_progression = create_latency_progression(operational_df, enterprise_df, language)
    percentile_comparison = create_percentile_comparison(operational_metrics, enterprise_metrics, language)
    throughput_comparison = create_throughput_comparison(operational_metrics, enterprise_metrics, language)
    success_rate_comparison = create_success_rate_comparison(operational_metrics, enterprise_metrics, language)
    metrics_table = create_metrics_table(operational_metrics, enterprise_metrics, language)
    
    # Convert plots to HTML
    latency_progression_html = pyo.plot(latency_progression, output_type='div', include_plotlyjs=False)
    percentile_comparison_html = pyo.plot(percentile_comparison, output_type='div', include_plotlyjs=False)
    throughput_comparison_html = pyo.plot(throughput_comparison, output_type='div', include_plotlyjs=False)
    success_rate_comparison_html = pyo.plot(success_rate_comparison, output_type='div', include_plotlyjs=False)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build complete HTML page with new professional styling
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analytics SDK Performance Dashboard ({language.title()})</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f8f9fa; /* Light grey background */
                color: #212529; /* Dark grey text for contrast */
            }}
            .container {{
                max-width: 1600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.05);
                padding: 40px;
                border: 1px solid #dee2e6;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 1px solid #e9ecef;
            }}
            .header h1 {{
                font-size: 2.25rem;
                font-weight: 700;
                color: #343a40;
                margin: 0;
            }}
            .header h2 {{
                font-size: 1.5rem;
                font-weight: 500;
                color: #495057;
                margin: 10px 0;
            }}
            .timestamp {{
                color: #6c757d;
                font-size: 0.9rem;
                font-weight: 400;
            }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 30px;
                margin: 30px 0;
            }}
            .chart-container, .table-container {{
                background-color: #ffffff;
                padding: 25px;
                border-radius: 10px;
                border: 1px solid #e9ecef;
                box-shadow: 0 2px 8px rgba(0,0,0,0.03);
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .chart-container:hover, .table-container:hover {{
                transform: translateY(-5px);
                box-shadow: 0 6px 24px rgba(0,0,0,0.07);
            }}
            .full-width {{
                grid-column: 1 / -1;
            }}
            .metrics-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .metrics-table th, .metrics-table td {{
                padding: 14px 18px;
                text-align: left;
                border-bottom: 1px solid #dee2e6;
                font-size: 0.95rem;
            }}
            .metrics-table th {{
                background-color: #f8f9fa;
                font-weight: 600;
                color: #495057;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-top: 1px solid #dee2e6;
            }}
            .metrics-table tr:last-child td {{
                border-bottom: none;
            }}
            .metrics-table tr:hover {{
                background-color: #f1f3f5;
            }}
            .metrics-table td:first-child {{
                font-weight: 500;
                color: #343a40;
            }}
            .section-title {{
                font-size: 1.75rem;
                font-weight: 600;
                color: #343a40;
                margin-top: 40px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #3498db;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Analytics Performance Dashboard</h1>
                <h2>{language.title()} SDK Comparison</h2>
                <p class="timestamp">Generated on {timestamp}</p>
            </div>

            <div class="section-title">Performance Summary</div>
            <div class="table-container full-width">
                {metrics_table}
            </div>

            <div class="section-title">Performance Visualizations</div>
            <div class="grid-container">
                <div class="chart-container">
                    {throughput_comparison_html}
                </div>
                <div class="chart-container">
                    {success_rate_comparison_html}
                </div>
                <div class="chart-container full-width">
                    {percentile_comparison_html}
                </div>
                <div class="chart-container full-width">
                    {latency_progression_html}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

def main():
    parser = argparse.ArgumentParser(description='Generate Analytics Performance Dashboard')
    parser.add_argument('--run-dir', type=str, help='Path to specific run directory')
    parser.add_argument('--output', type=str, help='Output HTML file path')
    args = parser.parse_args()
    
    # Auto-detect result files
    if args.run_dir:
        data_files, language = auto_detect_result_files(args.run_dir)
        args.output = args.output or str(Path(args.run_dir) / "reports" / "dashboard.html")
    else:
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
        print("  For Python: operational-python.jsonl, enterprise-python.jsonl")
        print("  Legacy: operational.jsonl, enterprise.jsonl")
        sys.exit(1)
    
    logger.info(f"Found {len(data_files)} result files for {language.upper()}:")
    for key, file_info in data_files.items():
        logger.info(f"  - {file_info['display_name']}: {file_info['path']}")
    
    # Calculate metrics for available datasets
    operational_metrics = None
    enterprise_metrics = None
    operational_df = pd.DataFrame()
    enterprise_df = pd.DataFrame()
    
    if 'operational' in data_files:
        operational_df = load_data(data_files['operational']['path'])
        if not operational_df.empty:
            operational_metrics = calculate_detailed_metrics(operational_df, language)
            logger.info(f"Operational SDK: {len(operational_df)} records loaded")
        else:
            logger.warning("Operational SDK: No data found")
    
    if 'enterprise' in data_files:
        enterprise_df = load_data(data_files['enterprise']['path'])
        if not enterprise_df.empty:
            enterprise_metrics = calculate_detailed_metrics(enterprise_df, language)
            logger.info(f"Enterprise SDK: {len(enterprise_df)} records loaded")
        else:
            logger.warning("Enterprise SDK: No data found")
    
    if not operational_metrics and not enterprise_metrics:
        logger.error("No valid data found in either SDK result file")
        sys.exit(1)
    
    # Generate HTML dashboard
    html_content = generate_html_dashboard(
        operational_metrics, enterprise_metrics, language,
        operational_df, enterprise_df
    )
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write dashboard
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    logger.info(f"Dashboard generated: {output_path}")
    logger.info(f"Dashboard URL: file://{output_path.absolute()}")

if __name__ == "__main__":
    main()
