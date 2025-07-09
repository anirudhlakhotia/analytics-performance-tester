package com.couchbase.analytics.benchmark;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Immutable data class representing the metrics for a single query execution.
 * Thread-safe and suitable for concurrent environments.
 */
public class QueryExecutionMetrics {
    private final long startTime;
    private final long endTime;
    private final long absoluteStartTimeMs;
    private final long absoluteEndTimeMs;
    private final int sequenceNumber;
    private final boolean success;
    private final String errorMessage;
    private final int rowCount;
    private final String sdkType;
    private final String queryName;
    private final long durationNanos;
    
    public QueryExecutionMetrics(
            long startTime,
            long endTime, 
            boolean success,
            String errorMessage,
            int rowCount,
            String sdkType,
            String queryName,
            int sequenceNumber,
            long absoluteStartTimeMs) {  // Add absolute timestamp parameter
        this.startTime = startTime;
        this.endTime = endTime;
        this.absoluteStartTimeMs = absoluteStartTimeMs;
        this.absoluteEndTimeMs = absoluteStartTimeMs + ((endTime - startTime) / 1_000_000);  // Simple calculation
        this.sequenceNumber = sequenceNumber;
        this.success = success;
        this.errorMessage = errorMessage;
        this.rowCount = rowCount;
        this.sdkType = sdkType;
        this.queryName = queryName;
        this.durationNanos = endTime - startTime;
    }
    
    // Getters only - no setters for immutability
    @JsonProperty("start_time")
    public long getStartTime() { return startTime; }
    
    @JsonProperty("end_time") 
    public long getEndTime() { return endTime; }
    
    @JsonProperty("success")
    public boolean isSuccess() { return success; }
    
    @JsonProperty("error_message")
    public String getErrorMessage() { return errorMessage; }
    
    @JsonProperty("row_count")
    public int getRowCount() { return rowCount; }
    
    @JsonProperty("sdk_type")
    public String getSdkType() { return sdkType; }
    
    @JsonProperty("query_name")
    public String getQueryName() { return queryName; }
    
    @JsonProperty("duration_nanos")
    public long getDurationNanos() { return durationNanos; }
    
    @JsonProperty("duration_ms")
    public double getDurationMs() {
        return durationNanos / 1_000_000.0;
    }
    
    @JsonProperty("absolute_start_time_ms")
    public long getAbsoluteStartTimeMs() { return absoluteStartTimeMs; }
    
    @JsonProperty("absolute_end_time_ms") 
    public long getAbsoluteEndTimeMs() { return absoluteEndTimeMs; } // This getter was not in the new_code, but should be consistent
    
    @JsonProperty("sequence_number")
    public int getSequenceNumber() { return sequenceNumber; }
    
    @JsonProperty("timestamp")
    public long getTimestamp() {
        return absoluteStartTimeMs;
    }
}
