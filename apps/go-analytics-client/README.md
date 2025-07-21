# Go Analytics Client

This is the Go implementation of the Couchbase Analytics performance testing client.

## Features

- **Dual SDK Support**: Supports both operational (`gocb`) and enterprise (`gocbanalytics`) SDKs
- **Configurable Testing**: Environment variable-based configuration
- **Performance Metrics**: Detailed JSON output with timing and success metrics
- **Concurrent Testing**: Multi-threaded query execution
- **Coordinated Omission**: Proper timing to avoid measurement bias

## Building

```bash
make build
```

## Usage

The application reads configuration from environment variables (same as the Java version):

```bash
export BENCHMARK_DURATION_MS=30000
export BENCHMARK_WARMUP_MS=5000
export BENCHMARK_THREADS=10
export BENCHMARK_REQUEST_INTERVAL_MS=100
export BENCHMARK_PROGRESS_INTERVAL_MS=5000
export CLUSTER_CONNECTION_STRING="couchbase://localhost"
export CLUSTER_USERNAME="Administrator"
export CLUSTER_PASSWORD="password"
export BENCHMARK_ANALYTICS_TIMEOUT_S=60
export BENCHMARK_CONNECTION_TIMEOUT_S=10
export BENCHMARK_QUERY="SELECT COUNT(*) FROM dataset"
export BENCHMARK_QUERY_NAME="count_query"
export BENCHMARK_OUTPUT_FILE="results.jsonl"
export BENCHMARK_RUN_TIMESTAMP="2024-01-01_12-00-00"
export BENCHMARK_SDK_TYPE="operational"  # or "enterprise"

make run
```

## Dependencies

- **gocb**: Couchbase operational SDK
- **gocbanalytics**: Couchbase analytics SDK
- **Go 1.21+**: Required Go version

## Architecture

The application follows the same structure as the Java version:

- `main.go`: Main application and configuration
- `sdk_handler.go`: SDK handler interface
- `operational_handler.go`: Operational SDK implementation
- `enterprise_handler.go`: Enterprise SDK implementation
- `metrics.go`: Query execution metrics
- `metrics_writer.go`: JSON metrics writer

## Output Format

The application outputs metrics in the same JSON format as the Java version, ensuring compatibility with existing analysis tools. 