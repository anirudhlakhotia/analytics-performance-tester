package com.couchbase.perf;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Calculates latency percentiles from a results.jsonl file.
 */
public class LatencyCalculator {
    private static final Logger LOGGER = LoggerFactory.getLogger(LatencyCalculator.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * Reads a results file, extracts all durations, and calculates key percentiles.
     * @param resultsFilePath Path to the JSONL results file.
     * @return A LatencyStats object containing calculated percentiles.
     * @throws IOException If the file cannot be read.
     */
    public LatencyStats calculate(String resultsFilePath) throws IOException {
        LOGGER.info("Calculating latency percentiles from {}...", resultsFilePath);
        List<Long> durations = new ArrayList<>();
        int totalLines = 0;
        int failedLines = 0;

        try (BufferedReader reader = new BufferedReader(new FileReader(resultsFilePath))) {
            String line;
            while ((line = reader.readLine()) != null) {
                totalLines++;
                try {
                    JsonNode node = MAPPER.readTree(line);
                    if (node.has("duration_nanos")) {
                        durations.add(node.get("duration_nanos").asLong());
                    }
                } catch (Exception e) {
                    failedLines++;
                    LOGGER.warn("Could not parse line {}, skipping: {}", totalLines, line);
                }
            }
        }

        if (failedLines > 0) {
            LOGGER.warn("Failed to parse {} out of {} lines ({}%)", 
                        failedLines, totalLines, (failedLines * 100.0) / totalLines);
        }

        if (durations.isEmpty()) {
            LOGGER.warn("No duration data found in results file, cannot calculate percentiles.");
            return new LatencyStats(0, 0, 0, 0, 0, 0);
        }

        Collections.sort(durations);

        double p50 = getPercentile(durations, 50.0);
        double p90 = getPercentile(durations, 90.0);
        double p95 = getPercentile(durations, 95.0);
        double p99 = getPercentile(durations, 99.0);
        double p999 = getPercentile(durations, 99.9);
        double max = nanosToMillis(durations.get(durations.size() - 1));
        
        LatencyStats stats = new LatencyStats(p50, p90, p95, p99, p999, max);
        LOGGER.info("Latency stats calculated: {}", stats);
        return stats;
    }

    private double getPercentile(List<Long> sortedDurations, double percentile) {
        if (sortedDurations.isEmpty()) return 0;
        
        double index = (percentile / 100.0) * (sortedDurations.size() - 1);
        int lowerIndex = (int) Math.floor(index);
        int upperIndex = (int) Math.ceil(index);
        
        if (lowerIndex == upperIndex) {
            return nanosToMillis(sortedDurations.get(lowerIndex));
        }
        
        // Linear interpolation between two closest values
        double weight = index - lowerIndex;
        long lowerValue = sortedDurations.get(lowerIndex);
        long upperValue = sortedDurations.get(upperIndex);
        
        return nanosToMillis((long) (lowerValue + weight * (upperValue - lowerValue)));
    }
    
    private double nanosToMillis(long nanos) {
        return nanos / (double) Config.NANOSECONDS_PER_MILLISECOND;
    }
} 