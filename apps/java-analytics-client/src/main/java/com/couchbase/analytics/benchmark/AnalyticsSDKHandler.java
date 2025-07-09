package com.couchbase.analytics.benchmark;

public interface AnalyticsSDKHandler {
    QueryExecutionMetrics executeQuery(String query, String queryName, int sequenceNumber);
    String getSDKType();
    void close();
} 