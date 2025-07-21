package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"
	"sync"
	"sync/atomic"
	"time"
)

// Configuration holds all configuration from environment variables
type Configuration struct {
	DurationMs              int64
	WarmupMs                int64
	Threads                 int
	RequestIntervalMs       int64
	ProgressReportIntervalMs int64
	
	ConnectionString     string
	Username             string
	Password             string
	AnalyticsTimeoutS    int
	ConnectionTimeoutS   int
	
	Query         string
	QueryName     string
	OutputFile    string
	RunTimestamp  string
	SDKType       string
}

// SimpleAnalyticsRunner is the main runner application
type SimpleAnalyticsRunner struct {
	config          Configuration
	sequenceCounter int64
}

func main() {
	log.Println("🚀 Starting Simple Analytics Runner (Go)")
	
	runner, err := NewSimpleAnalyticsRunner()
	if err != nil {
		log.Fatalf("❌ Failed to create runner: %v", err)
	}
	
	// Log configuration
	log.Printf("📊 Configuration:")
	log.Printf("   SDK Type: %s", runner.config.SDKType)
	log.Printf("   Duration: %dms", runner.config.DurationMs)
	log.Printf("   Warmup: %dms", runner.config.WarmupMs)
	log.Printf("   Threads: %d", runner.config.Threads)
	log.Printf("   Query: %s", runner.config.Query)
	log.Printf("   Output: %s", runner.config.OutputFile)
	log.Printf("   Run Timestamp: %s", runner.config.RunTimestamp)
	
	if err := runner.Run(); err != nil {
		log.Fatalf("❌ Analytics runner failed: %v", err)
	}
	
	log.Println("✅ Analytics runner completed successfully")
}

// NewSimpleAnalyticsRunner creates a new runner with configuration from environment variables
func NewSimpleAnalyticsRunner() (*SimpleAnalyticsRunner, error) {
	config := Configuration{
		DurationMs:              getRequiredLongEnv("BENCHMARK_DURATION_MS"),
		WarmupMs:                getRequiredLongEnv("BENCHMARK_WARMUP_MS"),
		Threads:                 getRequiredIntEnv("BENCHMARK_THREADS"),
		RequestIntervalMs:       getRequiredLongEnv("BENCHMARK_REQUEST_INTERVAL_MS"),
		ProgressReportIntervalMs: getRequiredLongEnv("BENCHMARK_PROGRESS_INTERVAL_MS"),
		
		ConnectionString:     getRequiredEnv("CLUSTER_CONNECTION_STRING"),
		Username:             getRequiredEnv("CLUSTER_USERNAME"),
		Password:             getRequiredEnv("CLUSTER_PASSWORD"),
		AnalyticsTimeoutS:    getRequiredIntEnv("BENCHMARK_ANALYTICS_TIMEOUT_S"),
		ConnectionTimeoutS:   getRequiredIntEnv("BENCHMARK_CONNECTION_TIMEOUT_S"),
		
		Query:        getRequiredEnv("BENCHMARK_QUERY"),
		QueryName:    getRequiredEnv("BENCHMARK_QUERY_NAME"),
		OutputFile:   getRequiredEnv("BENCHMARK_OUTPUT_FILE"),
		RunTimestamp: getRequiredEnv("BENCHMARK_RUN_TIMESTAMP"),
		SDKType:      getRequiredEnv("BENCHMARK_SDK_TYPE"),
	}
	
	return &SimpleAnalyticsRunner{
		config:          config,
		sequenceCounter: 0,
	}, nil
}

// Run executes the performance test
func (r *SimpleAnalyticsRunner) Run() error {
	// Create SDK handler
	handler, err := r.createSDKHandler()
	if err != nil {
		return fmt.Errorf("failed to create SDK handler: %w", err)
	}
	defer handler.Close()
	
	// Run warmup
	if err := r.runWarmup(handler); err != nil {
		return fmt.Errorf("warmup failed: %w", err)
	}
	
	// Run performance test
	if err := r.runPerformanceTest(handler); err != nil {
		return fmt.Errorf("performance test failed: %w", err)
	}
	
	return nil
}

// createSDKHandler creates appropriate SDK handler based on configuration
func (r *SimpleAnalyticsRunner) createSDKHandler() (AnalyticsSDKHandler, error) {
	switch r.config.SDKType {
	case "operational":
		return NewOperationalSDKHandler(r.config)
	case "enterprise":
		return NewEnterpriseSDKHandler(r.config)
	default:
		return nil, fmt.Errorf("unknown SDK type: %s", r.config.SDKType)
	}
}

// runWarmup performs JIT warmup
func (r *SimpleAnalyticsRunner) runWarmup(handler AnalyticsSDKHandler) error {
	log.Printf("🔥 Starting warmup for %dms...", r.config.WarmupMs)
	
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(r.config.WarmupMs)*time.Millisecond)
	defer cancel()
	
	var wg sync.WaitGroup
	for i := 0; i < r.config.Threads; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				select {
				case <-ctx.Done():
					return
				default:
					seq := atomic.AddInt64(&r.sequenceCounter, 1)
					handler.ExecuteQuery(r.config.Query, "warmup", int(seq))
					// Suppress warmup errors
				}
			}
		}()
	}
	
	wg.Wait()
	log.Println("✅ Warmup complete")
	return nil
}

// runPerformanceTest executes the main performance test
func (r *SimpleAnalyticsRunner) runPerformanceTest(handler AnalyticsSDKHandler) error {
	log.Printf("📊 Starting performance measurement for %dms", r.config.DurationMs)
	
	var requestCount, successCount int64
	
	// ✅ FIXED: Reset sequence counter for actual test (separate from warmup)
	atomic.StoreInt64(&r.sequenceCounter, 0)
	
	// Create metrics writer
	writer := NewMetricsJSONWriter(r.config.OutputFile)
	writerCtx, writerCancel := context.WithCancel(context.Background())
	
	go writer.Start(writerCtx)
	
	startTime := time.Now()
	endTime := startTime.Add(time.Duration(r.config.DurationMs) * time.Millisecond)
	
	var wg sync.WaitGroup
	
	// Start worker threads
	for i := 0; i < r.config.Threads; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			nextExecutionTime := time.Now()
			
			for time.Now().Before(endTime) {
				atomic.AddInt64(&requestCount, 1)
				
				seq := atomic.AddInt64(&r.sequenceCounter, 1)
				result := handler.ExecuteQuery(r.config.Query, r.config.QueryName, int(seq))
				
				if result.Success {
					atomic.AddInt64(&successCount, 1)
				}
				
				writer.WriteResult(result)
				
				// Fixed coordinated omission timing
				nextExecutionTime = nextExecutionTime.Add(time.Duration(r.config.RequestIntervalMs) * time.Millisecond)
				sleepTime := time.Until(nextExecutionTime)
				if sleepTime > 0 {
					time.Sleep(sleepTime)
				}
			}
		}()
	}
	
	// Monitor progress
	go r.monitorProgress(startTime, endTime, &requestCount, &successCount)
	
	wg.Wait()
	
	// ✅ FIXED: Proper shutdown sequence
	log.Printf("All workers finished, shutting down metrics writer...")
	writerCancel() // Signal writer to stop accepting new writes
	writer.Wait()  // Wait for writer to finish processing all queued results
	
	// Final summary
	totalRequests := atomic.LoadInt64(&requestCount)
	totalSuccesses := atomic.LoadInt64(&successCount)
	successRate := float64(0)
	if totalRequests > 0 {
		successRate = (float64(totalSuccesses) * 100.0) / float64(totalRequests)
	}
	
	log.Printf("✅ %s SDK Test Complete:", handler.GetSDKType())
	log.Printf("   Total Requests: %d", totalRequests)
	log.Printf("   Success Rate: %.2f%%", successRate)
	log.Printf("   Results written: %d", writer.GetWrittenCount())
	log.Printf("   Raw data written to: %s", r.config.OutputFile)
	
	return nil
}

// monitorProgress logs progress during the test
func (r *SimpleAnalyticsRunner) monitorProgress(startTime, endTime time.Time, requestCount, successCount *int64) {
	ticker := time.NewTicker(time.Duration(r.config.ProgressReportIntervalMs) * time.Millisecond)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			if time.Now().After(endTime) {
				return
			}
			
			elapsed := time.Since(startTime).Seconds()
			requests := atomic.LoadInt64(requestCount)
			successes := atomic.LoadInt64(successCount)
			
			rps := float64(successes) / elapsed
			successRate := float64(0)
			if requests > 0 {
				successRate = (float64(successes) * 100.0) / float64(requests)
			}
			
			log.Printf("Progress - %ds elapsed | %d requests | %d successes | %.2f%% success | %.2f RPS",
				int(elapsed), requests, successes, successRate, rps)
		}
	}
}

// Helper functions for environment variables
func getRequiredEnv(name string) string {
	value := os.Getenv(name)
	if value == "" {
		log.Fatalf("Required environment variable not set: %s", name)
	}
	return value
}

func getRequiredLongEnv(name string) int64 {
	value := getRequiredEnv(name)
	result, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		log.Fatalf("Invalid long value for %s: %s", name, value)
	}
	return result
}

func getRequiredIntEnv(name string) int {
	value := getRequiredEnv(name)
	result, err := strconv.Atoi(value)
	if err != nil {
		log.Fatalf("Invalid int value for %s: %s", name, value)
	}
	return result
} 