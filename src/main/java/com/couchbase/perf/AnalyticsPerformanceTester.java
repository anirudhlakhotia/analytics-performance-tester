package com.couchbase.perf;

import com.couchbase.client.java.Cluster;
import com.couchbase.client.java.ClusterOptions;
import com.couchbase.client.java.env.ClusterEnvironment;
import com.couchbase.analytics.client.java.Credential;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.DecimalFormat;
import java.time.Duration;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Analytics SDK Performance Tester
 * 
 * This tool compares performance between:
 * 1. Operational Analytics SDK (traditional Couchbase Java SDK)
 * 2. Enterprise Analytics SDK 
 * 
 * The test runs sequentially:
 * 1. Start enterprise analytics cluster using cbdinocluster
 * 2. Test Operational SDK
 * 3. Test Enterprise SDK  
 * 4. Stop cluster and generate reports
 */
public class AnalyticsPerformanceTester {
    private static final Logger LOGGER = LoggerFactory.getLogger(AnalyticsPerformanceTester.class);
    private static final DecimalFormat DECIMAL_FORMAT = new DecimalFormat("#.##");
    
    private final ClusterManager clusterManager;
    
    /**
     * Constructs a new AnalyticsPerformanceTester with default cluster manager
     */
    public AnalyticsPerformanceTester() {
        this.clusterManager = new ClusterManager();
    }
    
    /**
     * Main entry point for the performance testing application
     * 
     * @param args command line arguments (currently unused)
     */
    public static void main(String[] args) {
        LOGGER.info("========================================");
        LOGGER.info("ANALYTICS SDK PERFORMANCE TESTER");
        LOGGER.info("========================================");
        
        // Show configuration
        Config.printConfiguration();
        
        AnalyticsPerformanceTester tester = new AnalyticsPerformanceTester();
        try {
            tester.runPerformanceComparison();
            LOGGER.info("✅ Performance test completed successfully!");
        } catch (Exception e) {
            LOGGER.error("❌ Performance test failed", e);
            System.exit(1);
        }
    }
    
    /**
     * Main test flow: cluster setup -> test both SDKs -> cleanup
     * 
     * @throws Exception if cluster management or SDK testing fails
     */
    public void runPerformanceComparison() throws Exception {
        String connectionString = null;
        
        try {
            // Step 1: Start cluster
            connectionString = startCluster();
            
            // Step 2: Test both SDKs
            AnalyticsTestResult operationalResult = testOperationalSDK(connectionString);
            AnalyticsTestResult enterpriseResult = testEnterpriseSDK(connectionString);
            
            // Step 3: Print comparison
            printComparisonReport(operationalResult, enterpriseResult);
            
        } finally {
            // Step 4: Cleanup
            stopCluster();
        }
    }
    
    /**
     * Start the enterprise analytics cluster and return connection string
     * 
     * @return the connection string for the started cluster
     * @throws Exception if cluster startup fails
     */
    private String startCluster() throws Exception {
        LOGGER.info("🚀 Starting enterprise analytics cluster...");
        clusterManager.startCluster();
        
        // Wait for cluster to be ready
        Thread.sleep(Config.CLUSTER_STARTUP_WAIT_SECONDS * Config.MILLISECONDS_PER_SECOND);
            
            String connectionString = clusterManager.getConnectionString();
        LOGGER.info("✅ Cluster ready at: {}", connectionString);
        return connectionString;
    }
    
    /**
     * Test the Operational Analytics SDK performance
     * 
     * @param connectionString the cluster connection string
     * @return test results containing performance metrics
     * @throws Exception if SDK connection or testing fails
     */
    private AnalyticsTestResult testOperationalSDK(String connectionString) throws Exception {
        LOGGER.info("🔍 Testing Operational Analytics SDK...");
        
        ClusterEnvironment environment = ClusterEnvironment.builder()
            .timeoutConfig(timeouts -> timeouts.analyticsTimeout(Duration.ofSeconds(Config.ANALYTICS_TIMEOUT_SECONDS)))
            .build();
            
        Cluster cluster = Cluster.connect(
            "couchbase://" + connectionString,
                ClusterOptions.clusterOptions(Config.USERNAME, Config.PASSWORD)
                    .environment(environment)
            );
        
        try {
            // Test connection
            cluster.analyticsQuery("SELECT 1 as test").rowsAsObject();
            LOGGER.info("✅ Operational SDK connected successfully");
            
            // Run performance test
            AnalyticsHandler handler = new OperationalAnalyticsHandler(cluster);
            return runSDKPerformanceTest("operational", handler);
            
        } finally {
            cluster.disconnect();
            environment.shutdown();
        }
    }
    
    /**
     * Test the Enterprise Analytics SDK performance
     * 
     * @param connectionString the cluster connection string
     * @return test results containing performance metrics
     * @throws Exception if SDK connection or testing fails
     */
    private AnalyticsTestResult testEnterpriseSDK(String connectionString) throws Exception {
        LOGGER.info("🔍 Testing Enterprise Analytics SDK...");
        
        String analyticsUrl = "http://" + connectionString + ":8095";
        LOGGER.info("Enterprise SDK URL: {}", analyticsUrl);
        
        com.couchbase.analytics.client.java.Cluster cluster = 
            com.couchbase.analytics.client.java.Cluster.newInstance(
                analyticsUrl,
                Credential.of(Config.USERNAME, Config.PASSWORD)
            );
        
        try {
            // Test connection
            cluster.executeQuery("SELECT 1 as test");
            LOGGER.info("✅ Enterprise SDK connected successfully");
            
            // Run performance test
            AnalyticsHandler handler = new EnterpriseAnalyticsHandler(cluster);
            return runSDKPerformanceTest("enterprise", handler);
            
        } finally {
            cluster.close();
        }
    }
    
    /**
     * Run performance test for a specific SDK
     * 
     * @param sdkType the type of SDK being tested ("operational" or "enterprise")
     * @param handler the analytics handler for the specific SDK
     * @return test results containing performance metrics
     * @throws IOException if result writing fails
     * @throws InterruptedException if thread execution is interrupted
     */
    private AnalyticsTestResult runSDKPerformanceTest(String sdkType, AnalyticsHandler handler) 
            throws IOException, InterruptedException {
        
        // 1. WARMUP PHASE
        warmup(handler);

        // 2. MEASUREMENT PHASE
        LOGGER.info("📊 Starting {} SDK performance test", sdkType);
        LOGGER.info("Configuration: {} threads × {}s duration", 
                   Config.THREAD_COUNT, Config.millisecondsToSeconds(Config.TEST_DURATION_MS));
        
        ExecutorService executor = Executors.newFixedThreadPool(Config.THREAD_COUNT);
        AtomicLong requestCount = new AtomicLong(0);
        AtomicLong successCount = new AtomicLong(0);
        
        String resultsFile = Config.getResultsFile(sdkType);
        ResultWriter resultWriter = new ResultWriter(resultsFile);
        Thread writerThread = new Thread(resultWriter);
        writerThread.start();
        
        long startTime = System.currentTimeMillis();
        
        try {
            submitWorkerThreads(executor, handler, requestCount, successCount, resultWriter, startTime);
            monitorProgress(sdkType, requestCount, successCount, startTime);
        } finally {
            shutdownExecutor(executor);
            stopResultWriter(resultWriter, writerThread);
            handler.close();
        }

        // 3. ANALYSIS PHASE
        LOGGER.info("🔬 Analyzing results from {}...", resultsFile);
        LatencyStats latencyStats = new LatencyCalculator().calculate(resultsFile);

        return calculateResults(sdkType, requestCount, successCount, startTime, latencyStats);
    }
    
    /**
     * Runs a warmup phase to allow for JIT compilation and connection pool ramp-up.
     * Executes queries for a configured duration without recording any metrics.
     * @param handler The analytics handler to use for executing queries.
     * @throws InterruptedException if the thread is interrupted while waiting for warmup completion.
     */
    private void warmup(AnalyticsHandler handler) throws InterruptedException {
        LOGGER.info("🔥 Starting warmup for {}ms...", Config.WARMUP_DURATION_MS);
        ExecutorService executor = Executors.newFixedThreadPool(Config.THREAD_COUNT);
        long warmupEndTime = System.currentTimeMillis() + Config.WARMUP_DURATION_MS;

        for (int i = 0; i < Config.THREAD_COUNT; i++) {
            executor.submit(() -> {
                while (System.currentTimeMillis() < warmupEndTime) {
                    try {
                        handler.executeQuery(Config.QUERY); // Execute without recording
                        Thread.sleep(Config.REQUEST_INTERVAL_MS);
                    } catch (Exception e) {
                        // Suppress errors during warmup but log them as warnings
                        LOGGER.warn("Warmup query failed: {}", e.getMessage());
                    }
                }
            });
        }

        executor.shutdown();
        if (!executor.awaitTermination(Config.WARMUP_DURATION_MS + 5000, TimeUnit.MILLISECONDS)) {
            LOGGER.warn("Warmup executor did not terminate gracefully.");
            executor.shutdownNow();
        }
        LOGGER.info("✅ Warmup complete.");
    }
    
    /**
     * Submit worker threads to execute queries concurrently
     * 
     * @param executor the thread pool executor
     * @param handler the analytics handler for query execution
     * @param requestCount atomic counter for total requests
     * @param successCount atomic counter for successful requests
     * @param resultWriter writer for persisting individual results
     * @param startTime test start time in milliseconds
     */
    private void submitWorkerThreads(ExecutorService executor, AnalyticsHandler handler,
                                   AtomicLong requestCount, AtomicLong successCount, 
                                   ResultWriter resultWriter, long startTime) {
        
        long endTime = startTime + Config.TEST_DURATION_MS;
        
        for (int i = 0; i < Config.THREAD_COUNT; i++) {
            final int threadId = i;
            executor.submit(() -> {
                while (System.currentTimeMillis() < endTime) {
                    try {
                        PerformanceMetrics result = handler.executeQuery(Config.QUERY);
                        requestCount.incrementAndGet();
                        
                        if (result.isSuccess()) {
                            successCount.incrementAndGet();
                        }
                        
                        resultWriter.writeResult(result);
                        Thread.sleep(Config.REQUEST_INTERVAL_MS);
                        
                    } catch (Exception e) {
                        LOGGER.error("Thread {} error: {}", threadId, e.getMessage());
                    }
                }
            });
        }
    }
    
    /**
     * Monitor and report progress during test execution
     * 
     * @param sdkType the type of SDK being tested
     * @param requestCount atomic counter for total requests
     * @param successCount atomic counter for successful requests
     * @param startTime test start time in milliseconds
     * @throws InterruptedException if thread sleep is interrupted
     */
    private void monitorProgress(String sdkType, AtomicLong requestCount, 
                               AtomicLong successCount, long startTime) throws InterruptedException {
        
        long endTime = startTime + Config.TEST_DURATION_MS;
        
        while (System.currentTimeMillis() < endTime) {
            Thread.sleep(Config.PROGRESS_REPORT_INTERVAL_MS);
            
            long elapsed = System.currentTimeMillis() - startTime;
            long requests = requestCount.get();
            long successes = successCount.get();
            double rps = requests / Config.millisecondsToSeconds(elapsed);
            double successRate = requests > 0 ? (successes * 100.0) / requests : 0;
            
            LOGGER.info("{} SDK - {}s elapsed | {} requests | {}% success | {} RPS", 
                       sdkType, 
                       Config.millisecondsToSeconds(elapsed), 
                       requests, 
                       DECIMAL_FORMAT.format(successRate), 
                       DECIMAL_FORMAT.format(rps));
        }
    }
    
    /**
     * Calculate final test results and metrics
     * 
     * @param sdkType the type of SDK being tested
     * @param requestCount atomic counter for total requests
     * @param successCount atomic counter for successful requests
     * @param startTime test start time in milliseconds
     * @param latencyStats calculated latency statistics
     * @return final test results with all calculated metrics
     */
    private AnalyticsTestResult calculateResults(String sdkType, AtomicLong requestCount, 
                                               AtomicLong successCount, long startTime,
                                               LatencyStats latencyStats) {
        
        long totalRequests = requestCount.get();
        long totalSuccesses = successCount.get();
        long actualDuration = System.currentTimeMillis() - startTime;
        
        double successRate = totalRequests > 0 ? (totalSuccesses * 100.0) / totalRequests : 0;
        double avgRps = totalRequests / Config.millisecondsToSeconds(actualDuration);
        
        AnalyticsTestResult result = new AnalyticsTestResult(
            sdkType, totalRequests, totalSuccesses, successRate, avgRps, actualDuration, latencyStats
        );
        
        LOGGER.info("✅ {} SDK Test Complete:", sdkType.toUpperCase());
        LOGGER.info("   Requests: {}", totalRequests);
        LOGGER.info("   Success Rate: {}%", DECIMAL_FORMAT.format(successRate));
        LOGGER.info("   Average RPS: {}", DECIMAL_FORMAT.format(avgRps));
        LOGGER.info("   Latency Stats (ms): p50={}, p99={}, max={}", 
                DECIMAL_FORMAT.format(latencyStats.p50), 
                DECIMAL_FORMAT.format(latencyStats.p99), 
                DECIMAL_FORMAT.format(latencyStats.max));

        return result;
    }
    
    /**
     * Print comprehensive comparison report between both SDKs
     * 
     * @param operational results from the operational analytics SDK test
     * @param enterprise results from the enterprise analytics SDK test
     */
    private void printComparisonReport(AnalyticsTestResult operational, AnalyticsTestResult enterprise) {
        LOGGER.info("📈 PERFORMANCE COMPARISON REPORT");
        LOGGER.info("=====================================");
        
        LOGGER.info("Operational SDK: {} requests, {}% success, {} RPS",
                   operational.totalRequests, 
                   DECIMAL_FORMAT.format(operational.successRate),
                   DECIMAL_FORMAT.format(operational.avgRps));
                   
        LOGGER.info("Enterprise SDK:  {} requests, {}% success, {} RPS",
                   enterprise.totalRequests,
                   DECIMAL_FORMAT.format(enterprise.successRate), 
                   DECIMAL_FORMAT.format(enterprise.avgRps));
        
        LOGGER.info("-----------------------------------------------------------------------------------------");
        LOGGER.info(String.format("%-15s | %-10s | %-10s | %-10s | %-10s | %-10s",
                "SDK", "p50 (ms)", "p90 (ms)", "p95 (ms)", "p99 (ms)", "p99.9 (ms)"));
        LOGGER.info("-----------------------------------------------------------------------------------------");
        LOGGER.info(String.format("%-15s | %-10.2f | %-10.2f | %-10.2f | %-10.2f | %-10.2f",
                "Operational",
                operational.latencyStats.p50,
                operational.latencyStats.p90,
                operational.latencyStats.p95,
                operational.latencyStats.p99,
                operational.latencyStats.p999));
        LOGGER.info(String.format("%-15s | %-10.2f | %-10.2f | %-10.2f | %-10.2f | %-10.2f",
                "Enterprise",
                enterprise.latencyStats.p50,
                enterprise.latencyStats.p90,
                enterprise.latencyStats.p95,
                enterprise.latencyStats.p99,
                enterprise.latencyStats.p999));
        LOGGER.info("-----------------------------------------------------------------------------------------");
        
        // Performance comparison
        if (enterprise.avgRps > operational.avgRps) {
            double improvement = ((enterprise.avgRps - operational.avgRps) / operational.avgRps) * 100;
            LOGGER.info("🚀 Enterprise SDK is {}% FASTER", DECIMAL_FORMAT.format(improvement));
        } else {
            double degradation = ((operational.avgRps - enterprise.avgRps) / operational.avgRps) * 100;
            LOGGER.info("⚠️  Enterprise SDK is {}% slower", DECIMAL_FORMAT.format(degradation));
        }
        
        LOGGER.info("Results files:");
        LOGGER.info("  📄 Operational: {}", Config.getResultsFile("operational"));
        LOGGER.info("  📄 Enterprise:  {}", Config.getResultsFile("enterprise"));
    }
    
    /**
     * Gracefully shutdown the executor service
     * 
     * @param executor the executor service to shutdown
     * @throws InterruptedException if shutdown is interrupted
     */
    private void shutdownExecutor(ExecutorService executor) throws InterruptedException {
        executor.shutdown();
        if (!executor.awaitTermination(Config.THREAD_SHUTDOWN_TIMEOUT_SECONDS, TimeUnit.SECONDS)) {
            LOGGER.warn("Executor did not terminate gracefully, forcing shutdown");
            executor.shutdownNow();
        }
    }
    
    /**
     * Stop the result writer thread gracefully
     * 
     * @param resultWriter the result writer to stop
     * @param writerThread the writer thread to join
     * @throws InterruptedException if thread join is interrupted
     */
    private void stopResultWriter(ResultWriter resultWriter, Thread writerThread) throws InterruptedException {
        resultWriter.stop();
        writerThread.join(Config.RESULT_WRITER_JOIN_TIMEOUT_MS);
    }
    
    /**
     * Stop the cluster gracefully with error handling
     */
    private void stopCluster() {
        try {
            LOGGER.info("🛑 Stopping cluster...");
            clusterManager.stopCluster();
            LOGGER.info("✅ Cluster stopped");
        } catch (Exception e) {
            LOGGER.warn("Failed to stop cluster cleanly", e);
        }
    }
    
    /**
     * Data class to hold test results for a single SDK
     * 
     * Contains all the metrics collected during a performance test run,
     * including request counts, success rates, and performance statistics.
     */
    private static class AnalyticsTestResult {
        /** The type of SDK tested (e.g., "operational", "enterprise") */
        final String sdkType;
        
        /** Total number of requests attempted */
        final long totalRequests;
        
        /** Total number of successful requests */
        final long totalSuccesses;
        
        /** Success rate as a percentage (0-100) */
        final double successRate;
        
        /** Average requests per second */
        final double avgRps;
        
        /** Actual test duration in milliseconds */
        final long durationMs;
        
        /** Calculated latency statistics */
        final LatencyStats latencyStats;
        
        /**
         * Constructs a new test result
         * 
         * @param sdkType the type of SDK tested
         * @param totalRequests total number of requests attempted
         * @param totalSuccesses total number of successful requests
         * @param successRate success rate as a percentage
         * @param avgRps average requests per second
         * @param durationMs actual test duration in milliseconds
         * @param latencyStats calculated latency statistics
         */
        AnalyticsTestResult(String sdkType, long totalRequests, long totalSuccesses, 
                          double successRate, double avgRps, long durationMs, LatencyStats latencyStats) {
            this.sdkType = sdkType;
            this.totalRequests = totalRequests;
            this.totalSuccesses = totalSuccesses;
            this.successRate = successRate;
            this.avgRps = avgRps;
            this.durationMs = durationMs;
            this.latencyStats = latencyStats;
        }
    }
}
