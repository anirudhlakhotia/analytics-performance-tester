package com.couchbase.perf;

import com.couchbase.client.java.Cluster;
import com.couchbase.client.java.analytics.AnalyticsResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Duration;

public class OperationalAnalyticsHandler implements AnalyticsHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(OperationalAnalyticsHandler.class);
    private final Cluster operationalCluster;
    
    public OperationalAnalyticsHandler(Cluster operationalCluster) {
        this.operationalCluster = operationalCluster;
    }
    
    @Override
    public PerformanceMetrics executeQuery(String query) {
        long startTime = System.nanoTime();
        boolean success = false;
        String errorMessage = null;
        int rowCount = 0;

        try {
            LOGGER.debug("Executing operational analytics query: {}", query);
            
            AnalyticsResult result = operationalCluster.analyticsQuery(query);
            rowCount = result.rowsAsObject().size();
            success = true;
            
            long endTime = System.nanoTime();
            
            LOGGER.debug("Operational analytics query completed in {} ns with {} rows", 
                        (endTime - startTime), rowCount);
            
            return new PerformanceMetrics(
                startTime, endTime, success, errorMessage, rowCount, "operational"
            );
            
        } catch (Exception e) {
            errorMessage = e.getMessage();
            long endTime = System.nanoTime();
            
            LOGGER.error("Operational analytics query failed after {} ns: {}", 
                        (endTime - startTime), errorMessage);
            
            return new PerformanceMetrics(
                startTime, endTime, success, errorMessage, 0, "operational"
            );
        }
    }
    
    @Override
    public String getSDKType() {
        return "operational";
    }
    
    @Override
    public void close() {
        // No-op, cluster lifecycle managed by the caller
    }
} 