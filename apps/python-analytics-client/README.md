# Python Analytics Client

This directory contains the Python implementation of the analytics performance test runner. It is designed to be a component of the larger `analytics-performance-tester` framework and is orchestrated by the shell scripts in the root `scripts/` directory.

## 🎯 Purpose

The client's responsibility is to:
1. Connect to a Couchbase cluster.
2. Execute a given Analytics query in a loop for a specified duration.
3. Record performance metrics for each query execution.
4. Write the results to a `.jsonl` file for later analysis by the dashboard generator.

It supports testing both the **Operational SDK** (`couchbase`) and the **Enterprise SDK** (`couchbase-analytics`).

## 📋 Prerequisites

- Python 3.8+
- The required Python packages, which can be installed from the `requirements.txt` file.

### Setup

Before running the client, install the necessary dependencies:
```bash
# From inside the apps/python-analytics-client/ directory
pip install -r requirements.txt
```

## ⚙️ Configuration (The Recommended Way)

The best way to run this test client is by using the orchestrator scripts from the root of the repository (e.g., `./scripts/run-full-benchmark-python.sh`).

These scripts read all test parameters from the central `config.yaml` file. This file is the **single source of truth** for the entire performance testing framework, ensuring that tests are consistent across all language runners (Python, Java, etc.).

The orchestrator scripts handle:
1.  Reading settings like test duration, query statements, and timeouts from `config.yaml`.
2.  Exporting these settings as the environment variables that the Python client expects.
3.  Creating the necessary results directories and executing the test.

By using the scripts, you only need to modify `config.yaml` to change test parameters.

## 🔧 Environment Variables

The Python client is configured entirely through environment variables. **You should not need to set these manually.** The table below shows how settings from `config.yaml` are mapped to the environment variables used by this client.

| `config.yaml` Path | Environment Variable | Description |
| :--- | :--- |:---|
| `test.duration_ms` | `TEST_DURATION_MS` | Total duration of the test run in milliseconds. |
| `sdk.analytics_timeout_s`| `ANALYTICS_TIMEOUT_S` | Timeout for individual Analytics queries in seconds. |
| `cluster.username` | `USERNAME` | The username for authenticating with the cluster. |
| `cluster.password` | `PASSWORD` | The password for the specified user. |
| `queries[0].statement` | `QUERY_STATEMENT` | The exact Analytics query statement to be executed. |
| `output.raw_data_dir` | `RESULTS_DIR` | The directory path where the output file will be saved. |
| *(N/A)* | `SDK_TYPE` | `operational` or `enterprise`, set by the orchestrator. |
| *(N/A)* | `CONNECTION_STRING`| `couchbase://...`, passed as an argument to the script. |
| *(N/A)* | `LANGUAGE` | `python`, set by the orchestrator. |

---

### Troubleshooting Environment Variables

You might encounter an error from the orchestrator script like this:
> [ERROR] Analytics SDK path '/Users/anirudh.lakhotia/Documents/analytics-performance-tester/analytics-python-client' does not exist. Please set the ANALYTICS_SDK_PATH environment variable or check your project structure.

This error comes from the `run-full-benchmark-*.sh` scripts, not the Python client itself. It highlights an important variable used by the **orchestrator**:

| Variable | Example Value | Description |
| :--- | :--- | :--- |
| `ANALYTICS_SDK_PATH` | `/path/to/analytics-python-client` | This should be the **absolute path** to the directory containing the enterprise analytics python client. |


## 🎮 How to Run Tests

### Running Full Benchmarks (Recommended Method)

Using the orchestrator scripts is the best way to run the performance tests. They handle all the configuration and setup for you.

#### Single Test Run
This script runs both the operational and enterprise SDK tests once and generates a dashboard.
```bash
# From the root of the analytics-performance-tester repository
./scripts/run-full-benchmark-python.sh
```

#### Multiple Test Runs
This script runs the single test script multiple times to gather data for statistical analysis (mean, standard deviation) across runs.
```bash
# From the root of the analytics-performance-tester repository
./scripts/run-full-benchmark-python-multiple.sh
```