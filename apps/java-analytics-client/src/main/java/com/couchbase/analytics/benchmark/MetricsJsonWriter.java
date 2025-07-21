package com.couchbase.analytics.benchmark;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/**
 * A robust, thread-safe metrics writer that ensures all data is flushed on shutdown.
 */
public class MetricsJsonWriter implements Runnable {
    private static final Logger LOGGER = LoggerFactory.getLogger(MetricsJsonWriter.class);

    private final String outputFile;
    private final BlockingQueue<QueryExecutionMetrics> queue = new LinkedBlockingQueue<>(10000);
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final AtomicBoolean running = new AtomicBoolean(true);
    private final AtomicLong writtenCount = new AtomicLong(0);

    public MetricsJsonWriter(String outputFile) {
        this.outputFile = outputFile;
    }

    /**
     * Attempts to queue a metrics object for writing. Non-blocking.
     */
    public void writeResult(QueryExecutionMetrics metrics) {
        if (running.get()) {
            if (!this.queue.offer(metrics)) {
                LOGGER.warn("Metrics queue is full, dropping result for query #{}", metrics.getSequenceNumber());
            }
        }
    }

    /**
     * Signals the writer to stop accepting new metrics and drain the queue.
     */
    public void stop() {
        running.set(false);
    }
    
    public long getWrittenCount() {
        return writtenCount.get();
    }

    @Override
    public void run() {
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputFile))) {
            // Loop as long as the runner is active OR the queue has items to drain
            while (running.get() || !queue.isEmpty()) {
                // Poll with a timeout to prevent busy-waiting
                QueryExecutionMetrics metrics = queue.poll(100, TimeUnit.MILLISECONDS);
                if (metrics != null) {
                    try {
                        writer.write(objectMapper.writeValueAsString(metrics));
                        writer.newLine();
                        writtenCount.incrementAndGet();
                    } catch (IOException e) {
                        LOGGER.error("Failed to write metric to file", e);
                    }
                }
            }
            writer.flush();
        } catch (IOException e) {
            LOGGER.error("Failed to open or write to output file: {}", outputFile, e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            LOGGER.warn("Metrics writer was interrupted while polling queue.");
        } finally {
            LOGGER.info("Metrics writer has shut down.");
        }
    }
}
