# Couchbase Analytics Performance Tester

A **decoupled, extensible performance testing framework** that compares **Operational Analytics SDK** (traditional Couchbase Java SDK) against the **Enterprise Analytics SDK** (new analytics SDK). Built with a clean architecture that's ready for multi-language support.

## 🚀 Quick Start

### Test Against Your Existing Cluster
```bash
# Most common usage - test against your existing cluster
./scripts/run-full-benchmark.sh --cluster couchbase://your-cluster-host:11210
```

### Auto-Create Test Cluster
```bash
# Automatically create a new cluster for testing
./scripts/run-full-benchmark.sh
```

That's it! The tool will run both SDK tests, generate an interactive dashboard, and open the results automatically.

## 🎯 Key Features

- ✅ **Existing Cluster Support** - Point at any cluster and start testing
- ✅ **Auto Cluster Creation** - Spin up test clusters automatically
- ✅ **Live Progress Monitoring** - Real-time RPS and success rates
- ✅ **Decoupled Architecture** - Easy to extend to Go, Python, etc.
- ✅ **Single Configuration File** - All settings in `config.yaml`
- ✅ **Timestamped Results** - Historical test run tracking
- ✅ **Interactive Dashboard** - Rich HTML reports with charts
- ✅ **No Hardcoded Paths** - Works on any machine/environment

## 📋 Prerequisites

```bash
# Install required tools
brew install yq                    # YAML processor (macOS)
# OR: apt-get install yq          # Ubuntu/Debian
# OR: download from https://github.com/mikefarah/yq/releases

# For auto cluster creation only
brew install cbdinocluster         # Cluster management tool
```

**Required:**
- Java 11+ and Maven
- Python 3 (for dashboard generation)
- `yq` (YAML processor)

**Optional (for auto cluster creation):**
- `cbdinocluster` binary
- Docker & Docker Compose

## 🔧 Configuration

### Main Configuration (`config.yaml`)

```yaml
# Test execution settings
test:
  duration_ms: 30000          # 30 seconds per SDK test
  warmup_ms: 30000           # 30 seconds JIT warmup
  threads: 100               # Concurrent threads
  request_interval_ms: 2500  # Time between requests per thread

# Queries to test (add/modify as needed)
queries:
  - name: "simple_arithmetic"
    statement: "SELECT 1+1 as result;"
    description: "Basic arithmetic test"
    
  - name: "date_functions" 
    statement: "SELECT NOW() as current_time, DATE_ADD(NOW(), 1, 'day') as tomorrow;"
    description: "Date function performance"
    
  - name: "string_operations"
    statement: "SELECT CONCAT('Hello', ' ', 'World') as greeting, LENGTH('Analytics') as len;"
    description: "String manipulation test"

# SDK settings
sdk:
  analytics_timeout_s: 15      # Query timeout
  connection_timeout_s: 30     # Cluster connection timeout

# Cluster credentials
cluster:
  username: "Administrator"
  password: "password"
```

### Cluster Configuration (`infrastructure/cluster-config.yaml`)

```yaml
columnar: true
nodes:
  - count: 1
    version: 2.0.0-1024
docker:
  load-balancer: false
```

## 🎮 Usage

### Testing Against Existing Clusters

**Most Common Usage:**
```bash
# Test against your production/development cluster
./scripts/run-full-benchmark.sh --cluster couchbase://your-cluster:11210

# Test against local cluster
./scripts/run-full-benchmark.sh --cluster couchbase://localhost:11210

# Test against cluster with custom port
./scripts/run-full-benchmark.sh --cluster couchbase://cluster.company.com:11210
```

**Environment Variable Support:**
```bash
# Set once, use multiple times
export CLUSTER_CONNECTION_STRING="couchbase://your-cluster:11210"
./scripts/run-full-benchmark.sh --cluster "$CLUSTER_CONNECTION_STRING"
```

**Connection String Formats:**
```bash
# Full couchbase:// URL
couchbase://192.168.1.100:11210

# Simple hostname (assumes default port)
my-cluster.example.com

# Multiple hosts (comma-separated)
couchbase://host1,host2,host3
```

### Auto Cluster Creation

```bash
# Create a new cluster automatically
./scripts/run-full-benchmark.sh

# This will:
# 1. Start a new Couchbase cluster using cbdinocluster
# 2. Run the performance tests
# 3. Generate dashboard
# 4. Clean up the cluster automatically
```

### Help & Options

```bash
# Show all available options
./scripts/run-full-benchmark.sh --help
```

## 🔍 Customizing Tests

### 1. Change Queries

Edit `config.yaml` to modify what gets tested:

```yaml
queries:
  # Simple performance test
  - name: "basic_select"
    statement: "SELECT 1 as test;"
    description: "Basic query performance"
    
  # Real-world analytics query
  - name: "travel_sample_analysis"
    statement: "SELECT country, COUNT(*) FROM travel-sample WHERE type='airport' GROUP BY country ORDER BY COUNT(*) DESC LIMIT 10;"
    description: "Travel sample aggregation"
    
  # Complex analytics
  - name: "complex_aggregation"
    statement: "SELECT DATE_TRUNC('day', created_at) as day, AVG(response_time) as avg_response FROM metrics WHERE created_at > DATE_SUB(NOW(), 7, 'day') GROUP BY day ORDER BY day;"
    description: "Time-series aggregation"
```

**Note:** Currently, the first query in the list is used. Multi-query support is coming soon.

### 2. Adjust Load Testing Parameters

```yaml
test:
  duration_ms: 60000          # 1 minute per SDK (instead of 30s)
  threads: 200                # More concurrent threads
  request_interval_ms: 1000   # Faster requests (1 second interval)
```

**Load Testing Presets:**

```yaml
# Light load testing
test:
  duration_ms: 30000
  threads: 10
  request_interval_ms: 5000

# Heavy load testing  
test:
  duration_ms: 300000         # 5 minutes
  threads: 500
  request_interval_ms: 500    # 2 requests per second per thread
```

### 3. SDK Timeout Settings

```yaml
sdk:
  analytics_timeout_s: 30     # Longer timeout for complex queries
  connection_timeout_s: 60    # Longer connection timeout
```

### 4. Cluster Configuration

For auto-created clusters, edit `infrastructure/cluster-config.yaml`:

```yaml
# Multi-node cluster
columnar: true
nodes:
  - count: 3
    version: 2.0.0-1024
    services: [kv,n1ql,index,analytics]
docker:
  load-balancer: true

# Single node with specific version
columnar: true
nodes:
  - count: 1
    version: 2.0.0-1024
docker:
  load-balancer: false
```

## 📊 Results & Analysis

### Output Structure

```
results/
├── runs/
│   └── 2025-01-09_14-30-15/           # Timestamped run
│       ├── raw/
│       │   ├── operational.jsonl       # Operational SDK results
│       │   └── enterprise.jsonl        # Enterprise SDK results
│       ├── reports/
│       │   └── dashboard.html          # 📊 Interactive dashboard
│       └── logs/
│           ├── operational.log         # Operational SDK logs
│           └── enterprise.log          # Enterprise SDK logs
└── latest -> runs/2025-01-09_14-30-15/  # Symlink to latest run
```

### Dashboard Features

Open `results/latest/reports/dashboard.html` to see:

- 📈 **Throughput Comparison** - Requests per second for both SDKs
- 📊 **Latency Analysis** - P50, P95, P99 response times
- 🎯 **Success Rate Tracking** - Percentage of successful operations
- 🔍 **Error Analysis** - Detailed error categorization
- 📋 **Test Metadata** - Configuration, environment, and run details

### Raw Data Analysis

The raw JSONL files contain detailed per-request metrics:

```json
{
  "start_time": 1234567890123,
  "end_time": 1234567890456,
  "success": true,
  "duration_ms": 333.0,
  "row_count": 1,
  "sdk_type": "operational",
  "query_name": "simple_arithmetic",
  "sequence_number": 1,
  "timestamp": 1234567890123
}
```

## 🏗️ Architecture

### Decoupled Design

The architecture is designed for easy extension to other languages:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Shell Script  │    │   Configuration  │    │   Dashboard     │
│   (Orchestrator)│────│   (config.yaml)  │────│   (Python)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────┐
│   Java Runner   │    │   Go Runner      │
│   (Current)     │    │   (Future)       │
└─────────────────┘    └──────────────────┘
```

**Key Principles:**
- **Shell orchestrator** handles cluster management, directory creation, and configuration parsing
- **Language runners** are simple workers that execute tests and write results
- **Single config file** (`config.yaml`) is the source of truth
- **No hardcoded paths** - everything is passed via environment variables
- **Testable components** - each part can be tested independently

### Current Components

```
analytics-performance-tester/
├── 📖 README.md                        # This file
├── 🔧 config.yaml                      # Main configuration
├── 🏗️ apps/java-analytics-client/      # Java test runner
├── 🛠️ infrastructure/
│   ├── cluster-config.yaml            # Cluster settings
│   └── cluster-manager.sh             # Cluster lifecycle
├── 📊 scripts/
│   └── run-full-benchmark.sh          # Main orchestrator
├── 🔬 analysis/
│   ├── dashboard_generator.py         # Dashboard creation
│   └── requirements.txt               # Python dependencies
└── 📈 results/                        # Generated results
    ├── runs/                          # Timestamped runs
    └── latest/                        # Symlink to latest
```

## 🔧 Development

### Adding New Queries

1. Edit `config.yaml`:
```yaml
queries:
  - name: "your_new_query"
    statement: "SELECT COUNT(*) FROM your_dataset WHERE condition = 'value';"
    description: "Description of what this tests"
```

2. Run tests:
```bash
./scripts/run-full-benchmark.sh --cluster your-cluster
```

### Extending to Other Languages

The architecture makes it easy to add Go, Python, or other language runners:

1. **Create new runner** (e.g., `apps/go-analytics-client/`)
2. **Read environment variables** (same as Java runner)
3. **Write JSONL results** (same format as Java)
4. **Update shell script** to call your runner

The shell orchestrator and dashboard generator work with any language that follows the interface.

### Testing Components

```bash
# Test configuration parsing
yq '.test.duration_ms' config.yaml

# Test Java runner directly
cd apps/java-analytics-client
mvn clean package
java -cp target/java-analytics-benchmark-1.0-SNAPSHOT.jar \
     com.couchbase.analytics.benchmark.SimpleAnalyticsRunner

# Test dashboard generation
python3 analysis/dashboard_generator.py --run-dir results/latest
```

## 🐛 Troubleshooting

### Common Issues

**"yq: command not found"**
```bash
# Install yq
brew install yq                    # macOS
sudo apt-get install yq           # Ubuntu/Debian
# OR download from: https://github.com/mikefarah/yq/releases
```

**"Connection refused"**
```bash
# Check if cluster is running
curl -s http://your-cluster:8091/pools

# Check cluster credentials in config.yaml
cluster:
  username: "Administrator"
  password: "password"
```

**"No results generated"**
```bash
# Check logs for errors
cat results/latest/logs/operational.log
cat results/latest/logs/enterprise.log

# Verify cluster has Analytics service enabled
curl -s http://your-cluster:8095/analytics/status
```

**"cbdinocluster not found" (auto cluster mode)**
```bash
# Install cbdinocluster
brew install cbdinocluster         # macOS
# OR download from: https://github.com/couchbaselabs/cbdinocluster/releases
```

### Debug Mode

Enable verbose logging by editing `apps/java-analytics-client/src/main/resources/simplelogger.properties`:

```properties
org.slf4j.simpleLogger.defaultLogLevel=DEBUG
org.slf4j.simpleLogger.log.com.couchbase.analytics.benchmark=DEBUG
```

### Performance Tuning

**For high-load testing:**
```yaml
test:
  threads: 500                    # More threads
  request_interval_ms: 100        # Faster requests
  duration_ms: 600000             # Longer test (10 minutes)

sdk:
  analytics_timeout_s: 60         # Longer timeout
  connection_timeout_s: 120       # Longer connection timeout
```

**For stability testing:**
```yaml
test:
  threads: 10                     # Fewer threads
  request_interval_ms: 10000      # Slower requests (10 seconds)
  duration_ms: 1800000            # Very long test (30 minutes)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Update documentation
5. Submit a pull request

### Architecture Guidelines

- Keep runners simple and focused
- Use environment variables for configuration
- Write results in JSONL format
- Follow the existing logging patterns
- Test against both existing and auto-created clusters