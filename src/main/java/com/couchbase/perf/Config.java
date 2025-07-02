package com.couchbase.perf;

/**
 * Configuration for Analytics SDK Performance Testing
 * 
 * This class contains all configurable parameters for the performance test.
 * Modify these values to adjust test behavior without changing code.
 */
public class Config {
    // ===========================================
    // TEST CONFIGURATION - MODIFY AS NEEDED
    // ===========================================
    
    /** Number of concurrent threads per SDK test */
    public static final int THREAD_COUNT = 100;
    
    /** Time between requests per thread (milliseconds) */
    public static final long REQUEST_INTERVAL_MS = 2500; // 2.5 second intervals
    
    /** Duration of each SDK test (milliseconds) */
    public static final long TEST_DURATION_MS = 300_000; // 5 minutes per SDK
    
    /** Query to execute for performance testing */
    public static final String QUERY = "SELECT 1+1 as result";
    
    // ===========================================
    // TIMING CONSTANTS
    // ===========================================
    
    /** Milliseconds in one second (for time conversions) */
    public static final long MILLISECONDS_PER_SECOND = 1000L;
    
    /** Nanoseconds in one millisecond (for time conversions) */
    public static final long NANOSECONDS_PER_MILLISECOND = 1_000_000L;
    
    /** Nanoseconds in one second (for time conversions) */
    public static final long NANOSECONDS_PER_SECOND = NANOSECONDS_PER_MILLISECOND * MILLISECONDS_PER_SECOND;
    
    // ===========================================
    // CLUSTER CONFIGURATION
    // ===========================================
    
    /** Path to cbdinocluster binary */
    public static final String CBDINOCLUSTER_PATH = System.getProperty("cbdinocluster.path", "./cbdinocluster");
    
    /** Cluster configuration file for cbdinocluster */
    public static final String CLUSTER_CONFIG_FILE = "cluster-config.yaml";
    
    /** Default connection string (will be overridden by actual cluster IP) */
    public static final String FALLBACK_CONNECTION_STRING = "127.0.0.1";
    
    /** Cluster credentials */
    public static final String USERNAME = "Administrator";
    public static final String PASSWORD = "password";
    
    /** Time to wait for cluster startup (seconds) */
    public static final int CLUSTER_STARTUP_WAIT_SECONDS = 15;
    
    /** Time to wait for cluster shutdown (seconds) */
    public static final int CLUSTER_SHUTDOWN_TIMEOUT_SECONDS = 30;
    
    // ===========================================
    // OUTPUT CONFIGURATION
    // ===========================================
    
    /** Directory for test results */
    public static final String RESULTS_DIR = "results";
    
    /** File pattern for SDK results */
    public static final String RESULTS_FILE_PATTERN = RESULTS_DIR + "/%s_results.jsonl";
    
    // ===========================================
    // PERFORMANCE TESTING PARAMETERS
    // ===========================================
    
    /** Connection timeout for analytics queries (seconds) */
    public static final int ANALYTICS_TIMEOUT_SECONDS = 30;
    
    /** Thread pool shutdown timeout (seconds) */
    public static final int THREAD_SHUTDOWN_TIMEOUT_SECONDS = 30;
    
    /** Progress reporting interval (milliseconds) */
    public static final long PROGRESS_REPORT_INTERVAL_MS = 5000;
    
    // ===========================================
    // RESULT WRITER CONFIGURATION
    // ===========================================
    
    /** Timeout for polling results from queue (milliseconds) */
    public static final long RESULT_QUEUE_POLL_TIMEOUT_MS = 1000L;
    
    /** Progress logging interval for result writer (milliseconds) */
    public static final long RESULT_WRITER_LOG_INTERVAL_MS = 5000L;
    
    /** Number of results to process before forcing a log message */
    public static final int RESULT_WRITER_LOG_BATCH_SIZE = 1000;
    
    /** Timeout for result writer thread join (milliseconds) */
    public static final long RESULT_WRITER_JOIN_TIMEOUT_MS = 5000L;
    
    /** Duration of the warmup phase (milliseconds) before measurement starts */
    public static final long WARMUP_DURATION_MS = 30_000; // 30 seconds
    
    // ===========================================
    // HELPER METHODS
    // ===========================================
    
    /**
     * Get results file path for a specific SDK
     * 
     * @param sdkType the type of SDK (e.g., "operational", "enterprise")
     * @return the file path for storing results
     */
    public static String getResultsFile(String sdkType) {
        return String.format(RESULTS_FILE_PATTERN, sdkType);
    }
    
    /**
     * Convert milliseconds to seconds as a double
     * 
     * @param milliseconds the time in milliseconds
     * @return the time in seconds as a double
     */
    public static double millisecondsToSeconds(long milliseconds) {
        return milliseconds / (double) MILLISECONDS_PER_SECOND;
    }
    
    /**
     * Convert nanoseconds to milliseconds, rounding to nearest second
     * Used for bucketing timestamps
     * 
     * @param nanoseconds the time in nanoseconds
     * @return the timestamp in milliseconds, rounded to nearest second
     */
    public static long nanosecondsToRoundedSecondMs(long nanoseconds) {
        return (nanoseconds / NANOSECONDS_PER_MILLISECOND / MILLISECONDS_PER_SECOND) * MILLISECONDS_PER_SECOND;
    }
    
    /**
     * Print current configuration to console
     * Useful for debugging and verifying test parameters
     */
    public static void printConfiguration() {
        System.out.println("=== PERFORMANCE TEST CONFIGURATION ===");
        System.out.println("Threads per SDK: " + THREAD_COUNT);
        System.out.println("Request interval: " + REQUEST_INTERVAL_MS + "ms");
        System.out.println("Test duration: " + TEST_DURATION_MS + "ms (" + millisecondsToSeconds(TEST_DURATION_MS) + "s)");
        System.out.println("Query: " + QUERY);
        System.out.println("Results directory: " + RESULTS_DIR);
        System.out.println("Analytics timeout: " + ANALYTICS_TIMEOUT_SECONDS + "s");
        System.out.println("=======================================");
    }
}
