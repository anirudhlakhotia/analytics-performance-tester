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
        long absoluteStartTimeMs = System.currentTimeMillis();  // Capture absolute time first
        long startTime = System.nanoTime();
        
        boolean success = false;
        String errorMessage = null;
        int rowCount = 0;

        try {
            LOGGER.debug("Executing enterprise analytics query #{}: {}", sequenceNumber, query);
            
            QueryResult result = enterpriseCluster.executeQuery(query);
            rowCount = result.rows().size();
            success = true;
            
            LOGGER.debug("Enterprise analytics query #{} completed in {} ns with {} rows", 
                        sequenceNumber, (System.nanoTime() - startTime), rowCount);
                        
        } catch (Exception e) {
            errorMessage = e.getMessage();
            LOGGER.error("Enterprise analytics query #{} failed: {}", sequenceNumber, errorMessage);
            success = false;
        }
        
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