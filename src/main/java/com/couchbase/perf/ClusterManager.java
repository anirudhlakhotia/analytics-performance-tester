package com.couchbase.perf;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.concurrent.TimeUnit;

public class ClusterManager {
    private static final Logger LOGGER = LoggerFactory.getLogger(ClusterManager.class);
    private String clusterId;
    private Process clusterProcess;
    private String connectionString;
    
    public void startCluster() throws IOException, InterruptedException {
        LOGGER.info("Starting Couchbase cluster with config file: {}", Config.CLUSTER_CONFIG_FILE);
        
        // Verify cbdinocluster binary exists
        Path cbdinoclusterPath = Paths.get(Config.CBDINOCLUSTER_PATH);
        if (!cbdinoclusterPath.toFile().exists()) {
            throw new RuntimeException("cbdinocluster binary not found at: " + Config.CBDINOCLUSTER_PATH + 
                ". Please ensure cbdinocluster is properly installed and the path is correct.");
        }
        
        // Verify cluster config file exists
        File configFile = new File(Config.CLUSTER_CONFIG_FILE);
        if (!configFile.exists()) {
            throw new RuntimeException("Cluster config file not found: " + Config.CLUSTER_CONFIG_FILE);
        }
        
        // Allocate using def-file approach - fail fast if this doesn't work
        allocateWithDefFile();
        
        if (clusterId == null) {
            // Try to get cluster ID from ps command
            clusterId = getLatestClusterId();
        }
        
        if (clusterId == null) {
            throw new RuntimeException("Failed to obtain cluster ID after successful allocation");
        }
        
        LOGGER.info("Cluster allocated successfully with ID: {}", clusterId);
        
        // Wait for cluster to be ready
        LOGGER.info("Waiting for cluster to be ready...");
        waitForClusterReady();
        
        // Get connection string
        connectionString = fetchConnectionString();
        LOGGER.info("Cluster ready. Connection string: {}", connectionString);
    }
    
    private void allocateWithDefFile() throws IOException, InterruptedException {
        LOGGER.info("Allocating cluster with def-file: {}", Config.CLUSTER_CONFIG_FILE);
        
        ProcessBuilder pb = new ProcessBuilder(
            Config.CBDINOCLUSTER_PATH, 
            "allocate", 
            "--def-file", 
            Config.CLUSTER_CONFIG_FILE
        );
        pb.redirectErrorStream(true);
        
        LOGGER.info("Executing: {}", String.join(" ", pb.command()));
        clusterProcess = pb.start();
        
        // Capture output
        StringBuilder output = new StringBuilder();
        
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(clusterProcess.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                LOGGER.info("cbdinocluster: {}", line);
                output.append(line).append("\n");
                
                // Look for cluster ID
                extractClusterIdFromLine(line);
            }
        }
        
        int exitCode = clusterProcess.waitFor();
        LOGGER.info("cbdinocluster process exited with code: {}", exitCode);
        
        if (exitCode != 0) {
            LOGGER.error("Cluster allocation failed with exit code: {}", exitCode);
            LOGGER.error("Full cbdinocluster output:");
            LOGGER.error(output.toString());
            throw new RuntimeException("Failed to allocate cluster with def-file. Exit code: " + exitCode);
        }
        
        LOGGER.info("Cluster allocation completed successfully");
    }
    
    private boolean extractClusterIdFromLine(String line) {
        // Look for cluster ID in various possible formats
        if (line.contains("Cluster allocated with ID:") || 
            line.contains("cluster-id:") || 
            line.contains("Allocated cluster:") ||
            line.matches(".*[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}.*")) {
            // Extract UUID pattern
            String[] parts = line.split("\\s+");
            for (String part : parts) {
                if (part.matches("[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")) {
                    clusterId = part;
                    LOGGER.info("Extracted cluster ID: {}", clusterId);
                    return true;
                }
            }
        }
        return false;
    }
    
    private String getLatestClusterId() throws IOException, InterruptedException {
        LOGGER.info("Attempting to get cluster ID from ps command...");
        
        ProcessBuilder pb = new ProcessBuilder(Config.CBDINOCLUSTER_PATH, "ps");
        Process process = pb.start();
        
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                LOGGER.info("ps output: {}", line);
                output.append(line).append("\n");
            }
        }
        
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new RuntimeException("Failed to list clusters with ps command. Exit code: " + exitCode);
        }
        
        // Parse output to get the most recent cluster ID
        String psOutput = output.toString();
        if (psOutput.matches(".*[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}.*")) {
            String[] parts = psOutput.split("[\n\\s]+");
            for (String part : parts) {
                if (part.matches("[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}")) {
                    LOGGER.info("Found cluster ID from ps: {}", part);
                    return part;
                }
            }
        }
        
        return null;
    }
    
    private void waitForClusterReady() throws InterruptedException {
        LOGGER.info("Waiting up to {} seconds for cluster to be ready...", Config.CLUSTER_STARTUP_WAIT_SECONDS);
        Thread.sleep(Config.CLUSTER_STARTUP_WAIT_SECONDS * 1000L);
    }
    
    private String fetchConnectionString() throws IOException, InterruptedException {
        if (clusterId == null) {
            throw new RuntimeException("Cannot fetch connection string: cluster ID is null");
        }
        
        LOGGER.info("Fetching connection string for cluster: {}", clusterId);
        ProcessBuilder pb = new ProcessBuilder(Config.CBDINOCLUSTER_PATH, "connstr", clusterId);
        Process process = pb.start();
        
        StringBuilder output = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                LOGGER.info("connstr output: {}", line);
                output.append(line).append("\n");
                
                if (!line.trim().isEmpty()) {
                    LOGGER.info("Raw connection string: {}", line);
                    // Extract just the host part if it's a full connection string
                    if (line.startsWith("couchbase://")) {
                        String host = line.substring("couchbase://".length()).split(",")[0];
                        LOGGER.info("Extracted host: {}", host);
                        return host;
                    }
                    return line.trim();
                }
            }
        }
        
        int exitCode = process.waitFor();
        if (exitCode != 0) {
            LOGGER.error("Failed to get connection string. Exit code: {}", exitCode);
            LOGGER.error("connstr output: {}", output.toString());
            throw new RuntimeException("Failed to get connection string for cluster: " + clusterId);
        }
        
        throw new RuntimeException("No connection string returned for cluster: " + clusterId);
    }
    
    public void stopCluster() throws IOException, InterruptedException {
        if (clusterId != null) {
            LOGGER.info("Stopping cluster: {}", clusterId);
            ProcessBuilder pb = new ProcessBuilder(Config.CBDINOCLUSTER_PATH, "rm", clusterId);
            Process process = pb.start();
            
            boolean finished = process.waitFor(Config.CLUSTER_SHUTDOWN_TIMEOUT_SECONDS, TimeUnit.SECONDS);
            if (!finished) {
                LOGGER.warn("Cluster shutdown timed out, forcing termination");
                process.destroyForcibly();
            }
            
            LOGGER.info("Cluster stopped");
        }
        
        // Clean up any remaining processes
        if (clusterProcess != null && clusterProcess.isAlive()) {
            clusterProcess.destroyForcibly();
        }
    }
    
    public String getClusterId() {
        return clusterId;
    }
    
    public String getConnectionString() {
        return connectionString != null ? connectionString : Config.FALLBACK_CONNECTION_STRING;
    }
}
