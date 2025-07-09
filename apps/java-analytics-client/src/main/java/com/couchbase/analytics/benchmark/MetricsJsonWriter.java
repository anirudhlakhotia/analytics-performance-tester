package com.couchbase.analytics.benchmark;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.text.DecimalFormat;

public class MetricsJsonWriter implements Runnable {
    private static final Logger LOGGER = LoggerFactory.getLogger(MetricsJsonWriter.class);
    private static final DecimalFormat DECIMAL_FORMAT = new DecimalFormat("#.##");
    
    // Constants
    private static final long RESULT_QUEUE_POLL_TIMEOUT_MS = 100;
    private static final long RESULT_WRITER_LOG_INTERVAL_MS = 5000;
    private static final int RESULT_WRITER_LOG_BATCH_SIZE = 1000;
    
    private final BlockingQueue<Object> resultQueue = new LinkedBlockingQueue<>();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final AtomicLong writtenCount = new AtomicLong(0);
    private final String outputFile;
    
    public MetricsJsonWriter(String outputFile) {
        this.outputFile = outputFile;
        LOGGER.info("Created MetricsJsonWriter for file: {}", outputFile);
    }
    
    public void writeResult(QueryExecutionMetrics metrics) {
        if (!resultQueue.offer(metrics)) {
            LOGGER.warn("Failed to queue result, queue may be full (size: {})", resultQueue.size());
        }
    }
    
    @Override
    public void run() {
        // Ensure output directory exists
        File outputFileObj = new File(outputFile);
        outputFileObj.getParentFile().mkdirs();
        
        LOGGER.info("MetricsJsonWriter starting for file: {}", outputFile);
        LOGGER.info("Output directory: {}", outputFileObj.getParent());
        
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputFile))) {
            LOGGER.info("Opened output file for writing: {}", outputFile);
            
            long lastLogTime = System.currentTimeMillis();
            long processedInInterval = 0;
            
            while (running.get() || !resultQueue.isEmpty()) {
                try {
                    Object result = resultQueue.poll(RESULT_QUEUE_POLL_TIMEOUT_MS, 
                                                    java.util.concurrent.TimeUnit.MILLISECONDS);
                    if (result != null) {
                        String jsonLine = objectMapper.writeValueAsString(result);
                        writer.write(jsonLine);
                        writer.newLine();
                        writer.flush(); // Ensure data is written immediately
                        
                        long count = writtenCount.incrementAndGet();
                        processedInInterval++;
                        
                        // Log progress using config constants
                        long currentTime = System.currentTimeMillis();
                        if (currentTime - lastLogTime >= RESULT_WRITER_LOG_INTERVAL_MS || 
                            count % RESULT_WRITER_LOG_BATCH_SIZE == 0) {
                            double rate = processedInInterval / ((currentTime - lastLogTime) / 1000.0);
                            LOGGER.info("MetricsJsonWriter: {} total results written, {} queued, {} results/sec", 
                                count, resultQueue.size(), DECIMAL_FORMAT.format(rate));
                            lastLogTime = currentTime;
                            processedInInterval = 0;
                        }
                        
                        // Trace logging for debugging
                        if (count <= 10) {
                            LOGGER.debug("Wrote result #{}: {}", count, 
                                result.getClass().getSimpleName());
                        }
                    } else if (running.get()) {
                        // Periodic status when no results are being written
                        if (writtenCount.get() > 0) {
                            LOGGER.debug("MetricsJsonWriter waiting for results... (queue size: {})", 
                                resultQueue.size());
                        }
                    }
                } catch (InterruptedException e) {
                    LOGGER.info("MetricsJsonWriter interrupted");
                    Thread.currentThread().interrupt();
                    break;
                } catch (IOException e) {
                    LOGGER.error("Failed to write result to file", e);
                }
            }
            
            // Write any remaining results
            while (!resultQueue.isEmpty()) {
                try {
                    Object result = resultQueue.poll();
                    if (result != null) {
                        String jsonLine = objectMapper.writeValueAsString(result);
                        writer.write(jsonLine);
                        writer.newLine();
                        writtenCount.incrementAndGet();
                    }
                } catch (IOException e) {
                    LOGGER.error("Failed to write remaining result", e);
                }
            }
            
            LOGGER.info("MetricsJsonWriter completed. Total results written: {}", writtenCount.get());
            
        } catch (IOException e) {
            LOGGER.error("Failed to open output file: {}", outputFile, e);
        }
    }
    
    public void stop() {
        LOGGER.info("Stopping MetricsJsonWriter... (queue size: {})", resultQueue.size());
        running.set(false);
    }
    
    public long getWrittenCount() {
        return writtenCount.get();
    }
    
    public int getQueueSize() {
        return resultQueue.size();
    }
}
