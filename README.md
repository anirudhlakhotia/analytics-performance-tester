# Couchbase Analytics Performance Tester

A comprehensive performance testing tool that compares **Operational Analytics SDK** (traditional Couchbase Java SDK) against the **Enterprise Analytics SDK** (new columnar-specific SDK).

## Overview

This tool implements a statistically rigorous performance comparison using:
- **Multi-threaded concurrent execution** to simulate realistic load
- **Fixed-interval scheduling** to avoid coordinated omission bias
- **Comprehensive metrics collection** including latency percentiles and error analysis

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS PERFORMANCE TESTER                 │
├─────────────────────────────────────────────────────────────────┤
│  1. Cluster Management (cbdinocluster)                          │
│  2. Sequential SDK Testing (Operational → Enterprise)           │
│  3. Multi-threaded Query Execution (N threads × 2.5s interval)  │
│  4. Real-time Data Collection & Aggregation                     │
│  5. Statistical Analysis & Reporting                            │
└─────────────────────────────────────────────────────────────────┘
```

### Test Flow
1. **Cluster Setup**: Start enterprise analytics cluster using cbdinocluster
2. **Operational SDK Test**: Connect and run performance test with operational analytics SDK
3. **Enterprise SDK Test**: Connect and run performance test with new enterprise analytics SDK
4. **Analysis**: Compare results and generate performance report
5. **Cleanup**: Stop cluster and clean up resources

## Prerequisites

### System Requirements
- **Java 17+** (OpenJDK or Oracle JDK)
- **Maven 3.6+**
- **Docker** (for cbdinocluster)
- **macOS/Linux** (Windows with WSL2)

### Required Files

#### 1. cbdinocluster Binary
You have several options for providing the cbdinocluster binary:

**Option A: Place in project root (default)**
```bash
# Download cbdinocluster (replace with actual download URL)
curl -L -o cbdinocluster https://github.com/couchbaselabs/cbdinocluster/releases/latest/download/cbdinocluster-darwin-amd64
chmod +x cbdinocluster
```

**Option B: Use existing binary elsewhere**
```bash
# Point to existing binary using system property
mvn exec:java -Dcbdinocluster.path=/path/to/your/cbdinocluster -Dexec.mainClass="com.couchbase.perf.AnalyticsPerformanceTester"

# Or set environment variable
export CBDINOCLUSTER_PATH=/path/to/your/cbdinocluster
./run-performance-test.sh
```

**Option C: Modify Config.java permanently**
```java
// Edit src/main/java/com/couchbase/perf/Config.java
public static final String CBDINOCLUSTER_PATH = "/absolute/path/to/cbdinocluster";
```

#### 2. Enterprise Analytics SDK
The project requires the local Enterprise Analytics SDK to be built and installed:

```bash
# Navigate to the SDK directory (sibling to this project)
cd ../couchbase-analytics-jvm-clients

# Build and install to local Maven repository
mvn clean install -DskipTests
```

**Expected Location**: `../couchbase-analytics-jvm-clients/` (sibling directory)

## Installation

### 1. Clone and Setup
```bash
git clone <repository-url>
cd analytics-performance-tester
```

### 2. Install cbdinocluster
```bash
# Download cbdinocluster binary (example for macOS)
curl -L -o cbdinocluster https://github.com/couchbaselabs/cbdinocluster/releases/latest/download/cbdinocluster-darwin-amd64
chmod +x cbdinocluster
```

### 3. Build Enterprise Analytics SDK
```bash
# Navigate to SDK directory (adjust path as needed)
cd ../couchbase-analytics-jvm-clients
mvn clean install -DskipTests
cd ../analytics-performance-tester
```

### 4. Verify Installation
```bash
./run-performance-test.sh help
```

## Configuration

### cbdinocluster Binary Path
The project supports multiple ways to specify the cbdinocluster binary location:

1. **Environment Variable** (recommended for existing installations):
   ```bash
   export CBDINOCLUSTER_PATH=/usr/local/bin/cbdinocluster
   ./run-performance-test.sh
   ```

2. **System Property** (for one-time runs):
   ```bash
   mvn exec:java -Dcbdinocluster.path=/path/to/cbdinocluster -Dexec.mainClass="com.couchbase.perf.AnalyticsPerformanceTester"
   ```

3. **Default Location** (project root):
   ```bash
   # Place binary in project root as ./cbdinocluster
   ```

4. **Hardcode in Config.java** (permanent change):
   ```java
   public static final String CBDINOCLUSTER_PATH = "/absolute/path/to/cbdinocluster";
   ```

### Test Parameters
Edit `src/main/java/com/couchbase/perf/Config.java` to customize:

```java
// Thread Configuration
public static final int THREAD_COUNT = 10;                    // Concurrent threads
public static final long TEST_DURATION_MS = 60_000;          // Test duration (60s)
public static final long REQUEST_INTERVAL_MS = 2_500;        // Request interval (2.5s)

// Query Configuration  
public static final String QUERY = "SELECT 1+1 as result";   // Test query

// Cluster Configuration
public static final String USERNAME = "Administrator";        // Cluster username
public static final String PASSWORD = "password";            // Cluster password
```

### Cluster Configuration
Edit `cluster-config.yaml` for cluster setup:

```yaml
columnar: true             
nodes:
  - count: 1               
    version: 2.0.0-1024    
docker:
  load-balancer: true      
```

## Usage

### Quick Start
```bash
# Run complete performance test
./run-performance-test.sh
```

### Available Commands
```bash
# Run complete test (default)
./run-performance-test.sh run

# Clean up existing clusters
./run-performance-test.sh clean

# Build application only
./run-performance-test.sh build

# Show help
./run-performance-test.sh help
```

### Manual Execution
```bash
# Build the application
mvn clean compile

# Run the test
mvn exec:java -Dexec.mainClass="com.couchbase.perf.AnalyticsPerformanceTester"
```

## Output and Results

### Console Output
```
========================================
ANALYTICS SDK PERFORMANCE TESTER
========================================

🚀 Starting enterprise analytics cluster...
✅ Cluster ready at: 192.168.106.130

🔍 Testing Operational Analytics SDK...
✅ Operational SDK connected successfully
📊 Starting operational SDK performance test

🔍 Testing Enterprise Analytics SDK...  
✅ Enterprise SDK connected successfully
📊 Starting enterprise SDK performance test

📊 PERFORMANCE COMPARISON REPORT
=====================================
Operational SDK Results:
  Total Requests: 240
  Success Rate: 100.00%
  Average RPS: 4.00

Enterprise SDK Results:
  Total Requests: 240  
  Success Rate: 100.00%
  Average RPS: 4.00

🚀 Performance is equivalent (0.00% difference)
```

### Result Files

#### Individual Results (`results/operational_results.jsonl`, `results/enterprise_results.jsonl`)
Raw performance data for each query execution:
```json
{
  "thread_id": 1,
  "timestamp": 1703123456789,
  "duration_nanos": 3060000,
  "success": true,
  "sdk_type": "operational",
  "query": "SELECT 1+1 as result"
}
```

#### Bucketed Results (`results/bucket_results.jsonl`)
Aggregated 1-second performance buckets:
```json
{
  "timestamp_secs": 1703123456,
  "operations_total": 847,
  "operations_success": 839,
  "duration_p95_us": 8500,
  "duration_p99_us": 15000,
  "sdk_type": "operational"
}
```

## Project Structure

```
analytics-performance-tester/
├── README.md                           # This file
├── pom.xml                            # Maven configuration
├── cluster-config.yaml                # Cluster configuration
├── cbdinocluster                      # Cluster management binary
├── run-performance-test.sh            # Main execution script
├── cleanup.sh                         # Cleanup script
├── results/                           # Test results directory
│   ├── operational_results.jsonl     # Raw operational SDK results
│   ├── enterprise_results.jsonl      # Raw enterprise SDK results
│   ├── bucket_results.jsonl          # Aggregated bucket results
│   └── archive_*/                     # Archived previous results
└── src/main/java/com/couchbase/perf/
    ├── AnalyticsPerformanceTester.java # Main orchestrator
    ├── Config.java                    # Configuration constants
    ├── ClusterManager.java            # Cluster lifecycle management
    ├── OperationalAnalyticsHandler.java # Traditional SDK wrapper
    ├── EnterpriseAnalyticsHandler.java # New SDK wrapper
    ├── QueryTask.java                 # Individual query execution
    ├── PerformanceMetrics.java        # Individual result data
    ├── PerformanceAggregator.java     # Time-series bucketing
    ├── BucketResult.java              # Aggregated result data
    └── ResultWriter.java              # JSONL output writer
```

## Troubleshooting

### Common Issues

#### 1. "cbdinocluster binary not found"
```bash
# Download and make executable
curl -L -o cbdinocluster <download-url>
chmod +x cbdinocluster
```

#### 2. "Missing artifact couchbase-analytics-java-client"
```bash
# Build and install the Enterprise Analytics SDK
cd ../couchbase-analytics-jvm-clients
mvn clean install -DskipTests
```

#### 3. "Connection refused" errors
```bash
# Clean up existing clusters and retry
./cleanup.sh
./run-performance-test.sh
```

#### 4. Docker permission issues
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Restart terminal session
```

### Debug Mode
Enable debug logging by setting log level in `src/main/resources/simplelogger.properties`:
```properties
org.slf4j.simpleLogger.defaultLogLevel=debug
```

### Manual Cleanup
```bash
# Clean up all resources
./cleanup.sh
```

## Extending the Tool

### Adding New Queries
Edit `Config.java`:
```java
public static final String QUERY = "SELECT COUNT(*) FROM dataset WHERE condition = true";
```

### Changing Load Patterns
Modify thread configuration:
```java
public static final int THREAD_COUNT = 50;              // More concurrent load
public static final long REQUEST_INTERVAL_MS = 1_000;   // Higher frequency
```

### Custom Metrics
Extend `PerformanceMetrics.java` to capture additional data points.

## Performance Analysis

The tool generates comprehensive performance data suitable for:
- **Throughput analysis**: Requests per second comparison
- **Latency analysis**: Response time distribution (P50, P95, P99)
- **Reliability analysis**: Success rates and error patterns
- **Time-series analysis**: Performance evolution over time


## What's Being Measured

### Individual Query Metrics
Each query execution captures:
- **Timing**: Nanosecond-precision start/end times
- **Duration**: Pure execution time vs total elapsed time
- **Success/Failure**: Boolean success with detailed error messages
- **Result Size**: Number of rows returned
- **Thread Context**: Which thread executed the query
- **SDK Type**: Operational vs Enterprise SDK identification

### Aggregated Bucket Metrics
Every second of test execution produces:
- **Throughput**: Operations per second
- **Latency Percentiles**: P50, P95, P99 response times
- **Success Rates**: Percentage of successful operations
- **Error Categorization**: Grouped error types and counts
- **Statistical Distribution**: Min, max, average response times

### Coordinated Omission Avoidance
The test uses **fixed-interval scheduling** where each thread executes queries every 2.5 seconds regardless of response time. This prevents the "coordinated omission" problem where slow responses artificially reduce load, leading to misleadingly good latency measurements.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request