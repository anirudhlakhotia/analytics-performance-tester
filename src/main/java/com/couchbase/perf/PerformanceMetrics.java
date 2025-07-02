package com.couchbase.perf;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Instant;

/**
 * Performance metrics data class for capturing detailed timing and execution information
 * 
 * This class captures comprehensive performance data for individual query executions,
 * including timing information, success/failure status, and metadata for analysis.
 *
 */
public class PerformanceMetrics {
    @JsonProperty("thread_id")
    private final int threadId;
    
    @JsonProperty("test_uuid")
    private final String testUuid;
    
    @JsonProperty("timestamp")
    private final long timestamp;
    
    @JsonProperty("initiated_nanos")
    private final long initiatedNanos;
    
    @JsonProperty("start_time_nanos")
    private final long startTimeNanos;
    
    @JsonProperty("end_time_nanos")
    private final long endTimeNanos;
    
    @JsonProperty("duration_nanos")
    private final long durationNanos;
    
    @JsonProperty("elapsed_nanos")
    private final long elapsedNanos;
    
    @JsonProperty("duration_ms")
    private final double durationMs;
    
    @JsonProperty("success")
    private final boolean success;
    
    @JsonProperty("error_message")
    private final String errorMessage;
    
    @JsonProperty("error_type")
    private final String errorType;
    
    @JsonProperty("row_count")
    private final long rowCount;
    
    @JsonProperty("query")
    private final String query;
    
    @JsonProperty("test_start_time_ms")
    private final long testStartTimeMs;
    
    @JsonProperty("bucket_timestamp_ms")
    private final long bucketTimestampMs;
    
    @JsonProperty("sdk_type")
    private final String sdkType;

    /**
     * Constructor for QueryTask (original interface)
     * 
     * @param threadId the ID of the thread executing the query
     * @param testUuid unique identifier for the test run
     * @param initiatedNanos nanosecond timestamp when query was initiated
     * @param startTimeNanos nanosecond timestamp when query execution started
     * @param endTimeNanos nanosecond timestamp when query execution ended
     * @param success whether the query executed successfully
     * @param errorMessage error message if query failed (null if successful)
     * @param errorType type/category of error if query failed (null if successful)
     * @param rowCount number of rows returned by the query
     * @param query the query that was executed
     * @param testStartTimeMs millisecond timestamp when the test started
     * @param sdkType the type of SDK used ("operational" or "enterprise")
     */
    public PerformanceMetrics(int threadId, String testUuid, long initiatedNanos, 
                             long startTimeNanos, long endTimeNanos, boolean success, 
                             String errorMessage, String errorType, long rowCount, 
                             String query, long testStartTimeMs, String sdkType) {
        this.threadId = threadId;
        this.testUuid = testUuid;
        this.timestamp = Instant.now().toEpochMilli();
        this.initiatedNanos = initiatedNanos;
        this.startTimeNanos = startTimeNanos;
        this.endTimeNanos = endTimeNanos;
        this.durationNanos = endTimeNanos - startTimeNanos;
        this.elapsedNanos = endTimeNanos - initiatedNanos;
        this.durationMs = durationNanos / (double) Config.NANOSECONDS_PER_MILLISECOND;
        this.success = success;
        this.errorMessage = errorMessage;
        this.errorType = errorType;
        this.rowCount = rowCount;
        this.query = query;
        this.testStartTimeMs = testStartTimeMs;
        this.bucketTimestampMs = Config.nanosecondsToRoundedSecondMs(startTimeNanos);
        this.sdkType = sdkType;
    }
    
    /**
     * Constructor for SDK comparison (simplified interface)
     * 
     * @param startTimeNanos nanosecond timestamp when query execution started
     * @param endTimeNanos nanosecond timestamp when query execution ended
     * @param success whether the query executed successfully
     * @param errorMessage error message if query failed (null if successful)
     * @param rowCount number of rows returned by the query
     * @param sdkType the type of SDK used ("operational" or "enterprise")
     */
    public PerformanceMetrics(long startTimeNanos, long endTimeNanos,
                             boolean success, String errorMessage, int rowCount, String sdkType) {
        this.threadId = (int) Thread.currentThread().getId();
        this.testUuid = "sdk-comparison";
        this.timestamp = Instant.now().toEpochMilli();
        this.initiatedNanos = startTimeNanos;
        this.startTimeNanos = startTimeNanos;
        this.endTimeNanos = endTimeNanos;
        this.durationNanos = endTimeNanos - startTimeNanos;
        this.elapsedNanos = this.durationNanos;
        this.durationMs = this.durationNanos / (double) Config.NANOSECONDS_PER_MILLISECOND;
        this.success = success;
        this.errorMessage = errorMessage;
        this.errorType = errorMessage != null ? "Error" : null;
        this.rowCount = rowCount;
        this.query = "SDK Comparison Query";
        this.testStartTimeMs = System.currentTimeMillis();
        this.bucketTimestampMs = Config.nanosecondsToRoundedSecondMs(startTimeNanos);
        this.sdkType = sdkType;
    }
    
    // Getters with JavaDoc
    
    /** @return the ID of the thread that executed this query */
    public int getThreadId() { return threadId; }
    
    /** @return the unique identifier for the test run */
    public String getTestUuid() { return testUuid; }
    
    /** @return the timestamp when this metric was created */
    public long getTimestamp() { return timestamp; }
    
    /** @return the nanosecond timestamp when query was initiated */
    public long getInitiatedNanos() { return initiatedNanos; }
    
    /** @return the nanosecond timestamp when query execution started */
    public long getStartTimeNanos() { return startTimeNanos; }
    
    /** @return the nanosecond timestamp when query execution ended */
    public long getEndTimeNanos() { return endTimeNanos; }
    
    /** @return the total duration of query execution in nanoseconds */
    public long getDurationNanos() { return durationNanos; }
    
    /** @return the elapsed time from initiation to completion in nanoseconds */
    public long getElapsedNanos() { return elapsedNanos; }
    
    /** @return the duration of query execution in milliseconds */
    public double getDurationMs() { return durationMs; }
    
    /** @return true if the query executed successfully, false otherwise */
    public boolean isSuccess() { return success; }
    
    /** @return the error message if query failed, null if successful */
    public String getErrorMessage() { return errorMessage; }
    
    /** @return the type/category of error if query failed, null if successful */
    public String getErrorType() { return errorType; }
    
    /** @return the number of rows returned by the query */
    public long getRowCount() { return rowCount; }
    
    /** @return the SQL query that was executed */
    public String getQuery() { return query; }
    
    /** @return the millisecond timestamp when the test started */
    public long getTestStartTimeMs() { return testStartTimeMs; }
    
    /** @return the bucket timestamp in milliseconds (rounded to nearest second) */
    public long getBucketTimestampMs() { return bucketTimestampMs; }
    
    /** @return the type of SDK used ("operational" or "enterprise") */
    public String getSdkType() { return sdkType; }
}
