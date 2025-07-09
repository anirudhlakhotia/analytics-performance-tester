package com.couchbase.analytics.benchmark;

import com.couchbase.client.java.Cluster;
import com.couchbase.client.java.analytics.AnalyticsResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class OperationalSDKHandler implements AnalyticsSDKHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(OperationalSDKHandler.class);
    private final Cluster operationalCluster;
    
    public OperationalSDKHandler(Cluster operationalCluster) {
        this.operationalCluster = operationalCluster;
    }
    
    @Override
    public QueryExecutionMetrics executeQuery(String query, String queryName, int sequenceNumber) {
        long absoluteStartTimeMs = System.currentTimeMillis();  // Capture absolute time first
        long startTime = System.nanoTime();
        
        boolean success = false;
        String errorMessage = null;
        int rowCount = 0;

        try {
            LOGGER.debug("Executing operational analytics query #{}: {}", sequenceNumber, query);
            
            AnalyticsResult result = operationalCluster.analyticsQuery(query);
            rowCount = result.rowsAsObject().size();
            success = true;
            
            long endTime = System.nanoTime();
            
            LOGGER.debug("Operational analytics query #{} completed in {} ns with {} rows", 
                        sequenceNumber, (endTime - startTime), rowCount);
            
            return new QueryExecutionMetrics(
                startTime, endTime, success, errorMessage, rowCount, 
                "operational", queryName, sequenceNumber, absoluteStartTimeMs
            );
            
        } catch (Exception e) {
            errorMessage = e.getMessage();
            long endTime = System.nanoTime();
            
            LOGGER.error("Operational analytics query #{} failed after {} ns: {}", 
                        sequenceNumber, (endTime - startTime), errorMessage);
            
            return new QueryExecutionMetrics(
                startTime, endTime, false, errorMessage, 0, 
                "operational", queryName, sequenceNumber, absoluteStartTimeMs
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