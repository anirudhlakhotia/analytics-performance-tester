#!/usr/bin/env python3
"""
Simple Analytics Runner (Python)

This is a "dumb" worker that:
1. Reads configuration from environment variables (set by shell script)
2. Connects to the cluster
3. Runs the performance test loop
4. Writes results to the specified output file
5. Exits

NO orchestration logic, NO directory management
"""

import logging
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from sdk_handler import AnalyticsSDKHandler, create_sdk_handler
from metrics_writer import MetricsJSONWriter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Configuration:
    """Configuration loaded from environment variables"""
    
    def __init__(self):
        self.duration_ms = self._get_required_int("BENCHMARK_DURATION_MS")
        self.warmup_ms = self._get_required_int("BENCHMARK_WARMUP_MS")
        self.threads = self._get_required_int("BENCHMARK_THREADS")
        self.request_interval_ms = self._get_required_int("BENCHMARK_REQUEST_INTERVAL_MS")
        self.progress_report_interval_ms = self._get_required_int("BENCHMARK_PROGRESS_INTERVAL_MS")
        
        self.connection_string = self._get_required_env("CLUSTER_CONNECTION_STRING")
        self.username = self._get_required_env("CLUSTER_USERNAME")
        self.password = self._get_required_env("CLUSTER_PASSWORD")
        self.analytics_timeout_s = self._get_required_int("BENCHMARK_ANALYTICS_TIMEOUT_S")
        self.connection_timeout_s = self._get_required_int("BENCHMARK_CONNECTION_TIMEOUT_S")
        
        self.query = self._get_required_env("BENCHMARK_QUERY")
        self.query_name = self._get_required_env("BENCHMARK_QUERY_NAME")
        self.output_file = self._get_required_env("BENCHMARK_OUTPUT_FILE")
        self.run_timestamp = self._get_required_env("BENCHMARK_RUN_TIMESTAMP")
        self.sdk_type = self._get_required_env("BENCHMARK_SDK_TYPE")
    
    def _get_required_env(self, name: str) -> str:
        value = os.getenv(name)
        if not value:
            logger.error(f"Required environment variable not set: {name}")
            logger.error("This application should be run via the shell scripts that set up the environment.")
            logger.error("Try: scripts/run-full-benchmark-python.sh")
            sys.exit(1)
        return value
    
    def _get_required_int(self, name: str) -> int:
        value = self._get_required_env(name)
        try:
            return int(value)
        except ValueError:
            logger.error(f"Invalid integer value for {name}: {value}")
            sys.exit(1)


class SimpleAnalyticsRunner:
    """Main analytics performance test runner"""
    
    def __init__(self):
        self.config = Configuration()
        self.sequence_counter = 0
        self.sequence_lock = threading.Lock()
        
    def run(self) -> None:
        """Execute the performance test"""
        logger.info("🚀 Starting Simple Analytics Runner (Python)")
        
        # Log configuration
        logger.info("📊 Configuration:")
        logger.info(f"   SDK Type: {self.config.sdk_type}")
        logger.info(f"   Duration: {self.config.duration_ms}ms")
        logger.info(f"   Warmup: {self.config.warmup_ms}ms")
        logger.info(f"   Threads: {self.config.threads}")
        logger.info(f"   Query: {self.config.query}")
        logger.info(f"   Output: {self.config.output_file}")
        logger.info(f"   Run Timestamp: {self.config.run_timestamp}")
        
        # Create SDK handler
        handler = create_sdk_handler(self.config)
        
        try:
            # Run warmup
            self._run_warmup(handler)
            
            # Run performance test
            self._run_performance_test(handler)
            
            logger.info("✅ Analytics runner completed successfully")
            
        finally:
            handler.close()
    
    def _run_warmup(self, handler: AnalyticsSDKHandler) -> None:
        """Perform warmup"""
        logger.info(f"🔥 Starting warmup for {self.config.warmup_ms}ms...")
        
        start_time = time.time()
        end_time = start_time + (self.config.warmup_ms / 1000.0)
        
        def warmup_worker():
            while time.time() < end_time:
                with self.sequence_lock:
                    self.sequence_counter += 1
                    seq = self.sequence_counter
                
                try:
                    handler.execute_query(self.config.query, "warmup", seq)
                    # Suppress warmup errors
                except Exception:
                    pass
        
        # Start warmup threads
        with ThreadPoolExecutor(max_workers=self.config.threads) as executor:
            futures = [executor.submit(warmup_worker) for _ in range(self.config.threads)]
            for future in futures:
                future.result()
        
        logger.info("✅ Warmup complete")
    
    def _run_performance_test(self, handler: AnalyticsSDKHandler) -> None:
        """Execute the main performance test"""
        logger.info(f"📊 Starting performance measurement for {self.config.duration_ms}ms")
        
        # Reset sequence counter for actual test
        with self.sequence_lock:
            self.sequence_counter = 0
        
        request_count = 0
        success_count = 0
        count_lock = threading.Lock()
        
        # Create metrics writer
        writer = MetricsJSONWriter(self.config.output_file)
        writer.start()
        
        start_time = time.time()
        end_time = start_time + (self.config.duration_ms / 1000.0)
        
        def performance_worker():
            nonlocal request_count, success_count
            
            next_execution_time = time.time()
            
            while time.time() < end_time:
                with count_lock:
                    request_count += 1
                
                with self.sequence_lock:
                    self.sequence_counter += 1
                    seq = self.sequence_counter
                
                result = handler.execute_query(self.config.query, self.config.query_name, seq)
                
                if result.success:
                    with count_lock:
                        success_count += 1
                
                writer.write_result(result)
                
                # Fixed coordinated omission timing
                next_execution_time += (self.config.request_interval_ms / 1000.0)
                sleep_time = next_execution_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        # Start progress monitoring
        progress_thread = threading.Thread(
            target=self._monitor_progress,
            args=(start_time, end_time, lambda: request_count, lambda: success_count)
        )
        progress_thread.daemon = True
        progress_thread.start()
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.config.threads) as executor:
            futures = [executor.submit(performance_worker) for _ in range(self.config.threads)]
            for future in futures:
                future.result()
        
        # Shutdown writer
        logger.info("All workers finished, shutting down metrics writer...")
        writer.stop()
        writer.wait()
        
        # Final summary
        success_rate = (success_count * 100.0) / request_count if request_count > 0 else 0.0
        
        logger.info(f"✅ {handler.get_sdk_type()} SDK Test Complete:")
        logger.info(f"   Total Requests: {request_count}")
        logger.info(f"   Success Rate: {success_rate:.2f}%")
        logger.info(f"   Results written: {writer.get_written_count()}")
        logger.info(f"   Raw data written to: {self.config.output_file}")
    
    def _monitor_progress(self, start_time: float, end_time: float, 
                         get_request_count, get_success_count) -> None:
        """Monitor and log progress during the test"""
        interval = self.config.progress_report_interval_ms / 1000.0
        
        while time.time() < end_time:
            time.sleep(interval)
            
            if time.time() >= end_time:
                break
            
            elapsed = time.time() - start_time
            requests = get_request_count()
            successes = get_success_count()
            
            rps = successes / elapsed if elapsed > 0 else 0.0
            success_rate = (successes * 100.0) / requests if requests > 0 else 0.0
            
            logger.info(f"Progress - {int(elapsed)}s elapsed | {requests} requests | "
                       f"{successes} successes | {success_rate:.2f}% success | {rps:.2f} RPS")


def main():
    try:
        runner = SimpleAnalyticsRunner()
        runner.run()
    except Exception as e:
        logger.error(f"❌ Analytics runner failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 