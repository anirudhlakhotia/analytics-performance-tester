package com.couchbase.analytics.benchmark;

import com.fasterxml.jackson.annotation.JsonProperty;

public class TestMetadata {
    private final String sdkType;
    private final long testStartTimeMs;
    private final long testEndTimeMs;
    private final long configuredDurationMs;
    private final int totalRequests;
    private final int successfulRequests;
    private final String queryName;
    
    // Additional fields for historical tracking
    private final String runTimestamp;
    private final String javaVersion;
    private final String osName;
    private final double successRate;
    
    public TestMetadata(String sdkType, long testStartTimeMs, long testEndTimeMs, 
                       long configuredDurationMs, int totalRequests, int successfulRequests, 
                       String queryName, String runTimestamp) {
        this.sdkType = sdkType;
        this.testStartTimeMs = testStartTimeMs;
        this.testEndTimeMs = testEndTimeMs;
        this.configuredDurationMs = configuredDurationMs;
        this.totalRequests = totalRequests;
        this.successfulRequests = successfulRequests;
        this.queryName = queryName;
        
        // Use provided timestamp from host (not generated)
        this.runTimestamp = runTimestamp;
        this.javaVersion = System.getProperty("java.version");
        this.osName = System.getProperty("os.name");
        this.successRate = totalRequests > 0 ? (successfulRequests * 100.0) / totalRequests : 0;
    }
    
    // All getters remain the same...
    @JsonProperty("sdk_type")
    public String getSdkType() { return sdkType; }
    
    @JsonProperty("test_start_time_ms")
    public long getTestStartTimeMs() { return testStartTimeMs; }
    
    @JsonProperty("test_end_time_ms")
    public long getTestEndTimeMs() { return testEndTimeMs; }
    
    @JsonProperty("configured_duration_ms")
    public long getConfiguredDurationMs() { return configuredDurationMs; }
    
    @JsonProperty("actual_duration_ms")
    public long getActualDurationMs() { return testEndTimeMs - testStartTimeMs; }
    
    @JsonProperty("total_requests")
    public int getTotalRequests() { return totalRequests; }
    
    @JsonProperty("successful_requests") 
    public int getSuccessfulRequests() { return successfulRequests; }
    
    @JsonProperty("query_name")
    public String getQueryName() { return queryName; }
    
    @JsonProperty("throughput_rps")
    public double getThroughputRps() {
        long actualDuration = getActualDurationMs();
        return actualDuration > 0 ? (successfulRequests * 1000.0) / actualDuration : 0;
    }
    
    // New getters for historical tracking
    @JsonProperty("run_timestamp")
    public String getRunTimestamp() { return runTimestamp; }
    
    @JsonProperty("java_version")
    public String getJavaVersion() { return javaVersion; }
    
    @JsonProperty("os_name")
    public String getOsName() { return osName; }
    
    @JsonProperty("success_rate")
    public double getSuccessRate() { return successRate; }
} 