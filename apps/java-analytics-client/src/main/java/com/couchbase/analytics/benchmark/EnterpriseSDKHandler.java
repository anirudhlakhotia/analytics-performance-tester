package com.couchbase.analytics.benchmark;

import com.couchbase.analytics.client.java.Cluster;
import com.couchbase.analytics.client.java.QueryResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class EnterpriseSDKHandler implements AnalyticsSDKHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(EnterpriseSDKHandler.class);
    private final Cluster enterpriseCluster;
    
    public EnterpriseSDKHandler(Cluster enterpriseCluster) {
        this.enterpriseCluster = enterpriseCluster;
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
                LOGGER.info("Executing enterprise analytics query #{}", sequenceNumber);
            }
            
            QueryResult result = enterpriseCluster.executeQuery(query);
            // This consumes the rows, it's part of the work being measured.
            rowCount = result.rows().size();
            success = true;
        } catch (Exception e) {
            errorMessage = e.getMessage();
            success = false;
        }
        
        // ✅ FIXED: Capture endTime AFTER the operation completes.
        long endTime = System.nanoTime();

        return new QueryExecutionMetrics(
            startTime, endTime, success, errorMessage, rowCount,
            "enterprise", queryName, sequenceNumber, absoluteStartTimeMs
        );
    }
    
    @Override
    public String getSDKType() {
        return "enterprise";
    }
    
    @Override
    public void close() {
        if (enterpriseCluster != null) {
            enterpriseCluster.close();
        }
    }
} 