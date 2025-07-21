package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sync"
	"sync/atomic"
)

// MetricsJSONWriter writes metrics to JSON file
type MetricsJSONWriter struct {
	outputFile   string
	resultChan   chan *QueryExecutionMetrics
	writtenCount int64
	done         chan struct{}
	wg           sync.WaitGroup
}

// NewMetricsJSONWriter creates a new metrics writer
func NewMetricsJSONWriter(outputFile string) *MetricsJSONWriter {
	return &MetricsJSONWriter{
		outputFile: outputFile,
		resultChan: make(chan *QueryExecutionMetrics, 1000),
		done:       make(chan struct{}),
	}
}

// WriteResult queues a result for writing
func (w *MetricsJSONWriter) WriteResult(metrics *QueryExecutionMetrics) {
	select {
	case w.resultChan <- metrics:
	case <-w.done:
		log.Printf("Warning: Attempted to write to closed metrics writer")
	default:
		log.Printf("Warning: Metrics writer queue full, dropping result")
	}
}

// Start begins the writer goroutine
func (w *MetricsJSONWriter) Start(ctx context.Context) {
	w.wg.Add(1)
	defer w.wg.Done()
	
	if err := os.MkdirAll(filepath.Dir(w.outputFile), 0755); err != nil {
		log.Printf("Failed to create output directory: %v", err)
		return
	}
	
	log.Printf("MetricsJSONWriter starting for file: %s", w.outputFile)
	
	file, err := os.Create(w.outputFile)
	if err != nil {
		log.Printf("Failed to create output file: %v", err)
		return
	}
	defer file.Close()
	
	encoder := json.NewEncoder(file)
	
	for {
		select {
		case <-ctx.Done():
			log.Printf("MetricsJSONWriter shutting down, draining remaining results...")
			close(w.done) 
			
			drained := 0
			for {
				select {
				case result := <-w.resultChan:
					if err := encoder.Encode(result); err != nil {
						log.Printf("Failed to encode result during shutdown: %v", err)
					} else {
						atomic.AddInt64(&w.writtenCount, 1)
						drained++
					}
				default:
					log.Printf("MetricsJSONWriter completed. Total results written: %d (drained %d during shutdown)",
						atomic.LoadInt64(&w.writtenCount), drained)
					return
				}
			}
			
		case result := <-w.resultChan:
			if err := encoder.Encode(result); err != nil {
				log.Printf("Failed to encode result: %v", err)
			} else {
				count := atomic.AddInt64(&w.writtenCount, 1)
				if count <= 5 || count%500 == 0 {
					log.Printf("Wrote result #%d", count)
				}
			}
		}
	}
}

func (w *MetricsJSONWriter) Wait() {
	w.wg.Wait()
}

func (w *MetricsJSONWriter) GetWrittenCount() int64 {
	return atomic.LoadInt64(&w.writtenCount)
}

func (w *MetricsJSONWriter) GetQueueSize() int {
	return len(w.resultChan)
} 