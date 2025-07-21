package com.couchbase.analytics.benchmark;

import com.couchbase.client.java.Cluster;
import com.couchbase.client.java.ClusterOptions;
import com.couchbase.client.java.env.ClusterEnvironment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Simplified, decoupled Analytics runner.
 * This is a "dumb" worker that:
 * 1. Reads configuration from environment variables (set by shell script)
 * 2. Connects to the cluster
 * 3. Runs the performance test loop
 * 4. Writes results to the specified output file
 * 5. Exits
 * 
 * NO orchestration logic, NO directory management, NO symlink creation.
 * This makes it easy to port to Go or any other language.
 */
public class SimpleAnalyticsRunner {
    private static final Logger LOGGER = LoggerFactory.getLogger(SimpleAnalyticsRunner.class);
    
    private final AtomicInteger sequenceCounter = new AtomicInteger(0);
    
    // Configuration from environment variables
    private final long durationMs;
    private final long warmupMs;
    private final int threads;
    private final long requestIntervalMs;
    private final long progressReportIntervalMs;
    
    private final String connectionString;
    private final String username;
    private final String password;
    private final int analyticsTimeoutS;
    private final int connectionTimeoutS;
    
    private final String query;
    private final String queryName;
    private final String outputFile;
    private final String runTimestamp;
    private final String sdkType;
    
    // ✅ FIXED: Add a field for the writer to manage its lifecycle
    private MetricsJsonWriter resultWriter;

    public SimpleAnalyticsRunner() {
        // All configuration comes from environment variables set by the shell script
        this.durationMs = getLongEnv("BENCHMARK_DURATION_MS");
        this.warmupMs = getLongEnv("BENCHMARK_WARMUP_MS");
        this.threads = getIntEnv("BENCHMARK_THREADS");
        this.requestIntervalMs = getLongEnv("BENCHMARK_REQUEST_INTERVAL_MS");
        this.progressReportIntervalMs = getLongEnv("BENCHMARK_PROGRESS_INTERVAL_MS");
        
        this.connectionString = getRequiredEnv("CLUSTER_CONNECTION_STRING");
        this.username = getRequiredEnv("CLUSTER_USERNAME");
        this.password = getRequiredEnv("CLUSTER_PASSWORD");
        this.analyticsTimeoutS = getIntEnv("BENCHMARK_ANALYTICS_TIMEOUT_S");
        this.connectionTimeoutS = getIntEnv("BENCHMARK_CONNECTION_TIMEOUT_S");
        
        this.query = getRequiredEnv("BENCHMARK_QUERY");
        this.queryName = getRequiredEnv("BENCHMARK_QUERY_NAME");
        this.outputFile = getRequiredEnv("BENCHMARK_OUTPUT_FILE");
        this.runTimestamp = getRequiredEnv("BENCHMARK_RUN_TIMESTAMP");
        this.sdkType = getRequiredEnv("BENCHMARK_SDK_TYPE");
    }
    
    public static void main(String[] args) {
        LOGGER.info("🚀 Starting Simple Analytics Runner");
        
        try {
            SimpleAnalyticsRunner runner = new SimpleAnalyticsRunner();
            
            // Log configuration (for debugging)
            LOGGER.info("📊 Configuration:");
            LOGGER.info("   SDK Type: {}", runner.sdkType);
            LOGGER.info("   Duration: {}ms", runner.durationMs);
            LOGGER.info("   Warmup: {}ms", runner.warmupMs);
            LOGGER.info("   Threads: {}", runner.threads);
            LOGGER.info("   Query: {}", runner.query);
            LOGGER.info("   Output: {}", runner.outputFile);
            LOGGER.info("   Run Timestamp: {}", runner.runTimestamp);
            
            runner.run();
            
            LOGGER.info("✅ Analytics runner completed successfully");
            
        } catch (Exception e) {
            LOGGER.error("❌ Analytics runner failed", e);
            System.exit(1);
        }
    }
    
    public void run() throws Exception {
        // 1. Create SDK handler and writer
        AnalyticsSDKHandler handler = createSDKHandler();
        this.resultWriter = new MetricsJsonWriter(outputFile);
        Thread writerThread = new Thread(resultWriter);
        writerThread.start();
        
        try {
            // 2. Run warmup
            runWarmup(handler);
            
            // 3. Run performance test
            runPerformanceTest(handler);
            
        } finally {
            // 4. ✅ FIXED: Proper shutdown sequence
            LOGGER.info("Shutting down metrics writer...");
            resultWriter.stop(); // Signal writer to stop and drain
            try {
                writerThread.join(5000); // Wait up to 5 seconds for the writer thread to finish
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                LOGGER.error("Interrupted while waiting for writer to finish.", e);
            }
            
            handler.close();
            
            LOGGER.info("Total results written: {}", resultWriter.getWrittenCount());
        }
    }
    
    private AnalyticsSDKHandler createSDKHandler() throws Exception {
        switch (sdkType.toLowerCase()) {
            case "operational":
                return createOperationalHandler();
            case "enterprise":
                return createEnterpriseHandler();
            default:
                throw new IllegalArgumentException("Unknown SDK type: " + sdkType);
        }
    }
    
    private AnalyticsSDKHandler createOperationalHandler() throws Exception {
        ClusterEnvironment environment = ClusterEnvironment.builder()
            .timeoutConfig(timeouts -> timeouts.analyticsTimeout(
                Duration.ofSeconds(analyticsTimeoutS)))
            .build();
            
        Cluster cluster = Cluster.connect(
            connectionString,
            ClusterOptions.clusterOptions(username, password)
                .environment(environment)
        );
        
        cluster.waitUntilReady(Duration.ofSeconds(connectionTimeoutS));
        LOGGER.info("✅ Operational SDK connected successfully");
        
        return new OperationalSDKHandler(cluster);
    }
    
    private AnalyticsSDKHandler createEnterpriseHandler() throws Exception {
        // Parse host from connection string
        String host = connectionString.replace("couchbase://", "").split(":")[0];
        String analyticsUrl = "http://" + host + ":8095";
        
        com.couchbase.analytics.client.java.Cluster cluster = 
            com.couchbase.analytics.client.java.Cluster.newInstance(
                analyticsUrl,
                com.couchbase.analytics.client.java.Credential.of(username, password)
            );
        
        // Test connection
        cluster.executeQuery("SELECT 1 as test");
        LOGGER.info("✅ Enterprise SDK connected successfully");
        
        return new EnterpriseSDKHandler(cluster);
    }
    
    private void runWarmup(AnalyticsSDKHandler handler) throws InterruptedException {
        LOGGER.info("🔥 Starting JIT warmup for {}ms...", warmupMs);
        
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        long warmupEndTime = System.currentTimeMillis() + warmupMs;

        for (int i = 0; i < threads; i++) {
            executor.submit(() -> {
                while (System.currentTimeMillis() < warmupEndTime) {
                    try {
                        // Use a different query name for warmup
                        handler.executeQuery(query, "warmup", sequenceCounter.incrementAndGet());
                    } catch (Exception e) {
                        // Suppress warmup errors
                    }
                }
            });
        }

        executor.shutdown();
        executor.awaitTermination(warmupMs + 5000, TimeUnit.MILLISECONDS);
        LOGGER.info("✅ JIT warmup complete");
    }
    
    private void runPerformanceTest(AnalyticsSDKHandler handler) throws Exception {
        LOGGER.info("📊 Starting performance measurement for {}ms", durationMs);
        
        // ✅ FIXED: Reset sequence counter for the main test run
        this.sequenceCounter.set(0);
        
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        AtomicLong requestCount = new AtomicLong(0);
        AtomicLong successCount = new AtomicLong(0);
        
        long actualStartTime = System.currentTimeMillis();
        long endTime = actualStartTime + durationMs;
        
        for (int i = 0; i < threads; i++) {
            executor.submit(() -> {
                long nextExecutionTime = System.currentTimeMillis();
                
                while (System.currentTimeMillis() < endTime) {
                    requestCount.incrementAndGet();
                    
                    QueryExecutionMetrics result = handler.executeQuery(
                            query, queryName, sequenceCounter.incrementAndGet());
                    
                    if (result.isSuccess()) {
                        successCount.incrementAndGet();
                    }
                    
                    resultWriter.writeResult(result);
                    
                    // Coordinated Omission Timing
                    nextExecutionTime += requestIntervalMs;
                    long sleepTime = nextExecutionTime - System.currentTimeMillis();
                    if (sleepTime > 0) {
                        try {
                            Thread.sleep(sleepTime);
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                        }
                    }
                }
            });
        }

        // Monitor progress
        Thread monitor = new Thread(() -> {
            try {
                monitorProgress(actualStartTime, endTime, requestCount, successCount);
            } catch (InterruptedException e) {
                // This is expected when the main thread interrupts the monitor to stop it.
                Thread.currentThread().interrupt();
                LOGGER.debug("Progress monitor was interrupted, shutting down.");
            }
        });
        monitor.setDaemon(true); // So it doesn't block exit
        monitor.start();

        executor.shutdown();
        executor.awaitTermination(durationMs + 10000, TimeUnit.MILLISECONDS);
        
        // Stop the monitor
        monitor.interrupt();
    }
    
    private void monitorProgress(long startTime, long endTime, AtomicLong requestCount, AtomicLong successCount) 
            throws InterruptedException {
        
        while (System.currentTimeMillis() < endTime) {
            Thread.sleep(progressReportIntervalMs);
            
            long elapsed = System.currentTimeMillis() - startTime;
            long requests = requestCount.get();
            long successes = successCount.get();
            
            // FIX: Use successful requests for RPS calculation
            double rps = successes / (elapsed / 1000.0);
            double successRate = requests > 0 ? (successes * 100.0) / requests : 0;
            
            LOGGER.info("Progress - {}s elapsed | {} requests | {} successes | {}% success | {} RPS", 
                       elapsed / 1000, 
                       requests,
                       successes,  // Add success count to output
                       String.format("%.2f", successRate), 
                       String.format("%.2f", rps));
        }
    }
    
    // Helper methods
    private String getRequiredEnv(String name) {
        String value = System.getenv(name);
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalStateException("Required environment variable not set: " + name);
        }
        return value.trim();
    }
    
    private long getLongEnv(String name) {
        String value = getRequiredEnv(name);
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException e) {
            throw new IllegalStateException("Invalid long value for " + name + ": " + value);
        }
    }
    
    private int getIntEnv(String name) {
        String value = getRequiredEnv(name);
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new IllegalStateException("Invalid int value for " + name + ": " + value);
        }
    }
} 