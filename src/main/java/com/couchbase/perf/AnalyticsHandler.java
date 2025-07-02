package com.couchbase.perf;

public interface AnalyticsHandler {
    PerformanceMetrics executeQuery(String query);
    String getSDKType();
    void close();
} 