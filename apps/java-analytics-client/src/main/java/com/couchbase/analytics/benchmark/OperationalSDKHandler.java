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
        long absoluteStartTimeMs = System.currentTimeMillis();
        long startTime = System.nanoTime();
        
        boolean success = false;
        String errorMessage = null;
        int rowCount = 0;

        try {
            if (sequenceNumber <= 10 || sequenceNumber % 1000 == 0) {
                 LOGGER.info("Executing operational analytics query #{}", sequenceNumber);
            }
            
            AnalyticsResult result = operationalCluster.analyticsQuery(query);
            // This consumes the rows, it's part of the work being measured.
            rowCount = result.rowsAsObject().size();
            success = true;
        } catch (Exception e) {
            errorMessage = e.getMessage();
            success = false;
        }

        // ✅ FIXED: Capture endTime AFTER the operation completes for consistency.
        long endTime = System.nanoTime();
        
        return new QueryExecutionMetrics(
            startTime, endTime, success, errorMessage, rowCount, 
            "operational", queryName, sequenceNumber, absoluteStartTimeMs
        );
    }
    
    @Override
    public String getSDKType() {
        return "operational";
    }
    
    @Override
    public void close() {
        // Cluster lifecycle is managed by the main runner, so this is a no-op.
    }
} 