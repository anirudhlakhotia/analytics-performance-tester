package com.couchbase.perf;

import com.couchbase.analytics.client.java.Cluster;
import com.couchbase.analytics.client.java.QueryResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class EnterpriseAnalyticsHandler implements AnalyticsHandler {
    private static final Logger LOGGER = LoggerFactory.getLogger(EnterpriseAnalyticsHandler.class);
    private final Cluster enterpriseCluster;
    
    public EnterpriseAnalyticsHandler(Cluster enterpriseCluster) {
        this.enterpriseCluster = enterpriseCluster;
    }
    
    @Override
    public PerformanceMetrics executeQuery(String query) {
        long startTime = System.nanoTime();
        boolean success = false;
        String errorMessage = null;
        int rowCount = 0;

        try {
            QueryResult result = enterpriseCluster.executeQuery(query);
            rowCount = result.rows().size();
            success = true;
        } catch (Exception e) {
            errorMessage = e.getMessage();
        }
        
        long endTime = System.nanoTime();

        return new PerformanceMetrics(
                startTime,
                endTime,
                success,
                errorMessage,
                rowCount,
                "enterprise"
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