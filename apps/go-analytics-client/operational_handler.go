package main

import (
	"fmt"
	"log"
	"time"

	"github.com/couchbase/gocb/v2"
)

// OperationalSDKHandler handles operational SDK operations
type OperationalSDKHandler struct {
	cluster *gocb.Cluster
}

// NewOperationalSDKHandler creates a new operational SDK handler
func NewOperationalSDKHandler(config Configuration) (*OperationalSDKHandler, error) {
	// Create cluster options
	opts := gocb.ClusterOptions{
		Username: config.Username,
		Password: config.Password,
		TimeoutsConfig: gocb.TimeoutsConfig{
			AnalyticsTimeout:  time.Duration(config.AnalyticsTimeoutS) * time.Second,
			ConnectTimeout:    time.Duration(config.ConnectionTimeoutS) * time.Second,
		},
	}
	
	// Connect to cluster
	cluster, err := gocb.Connect(config.ConnectionString, opts)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to cluster: %w", err)
	}
	
	// Wait until ready
	err = cluster.WaitUntilReady(time.Duration(config.ConnectionTimeoutS)*time.Second, nil)
	if err != nil {
		cluster.Close(nil)
		return nil, fmt.Errorf("cluster not ready: %w", err)
	}
	
	log.Println("✅ Operational SDK connected successfully")
	
	return &OperationalSDKHandler{
		cluster: cluster,
	}, nil
}

// ExecuteQuery executes a query using the operational SDK
func (h *OperationalSDKHandler) ExecuteQuery(query, queryName string, sequenceNumber int) *QueryExecutionMetrics {
	absoluteStartTimeMs := time.Now().UnixMilli()
	startTime := time.Now()
	
	if sequenceNumber <= 10 || sequenceNumber%1000 == 0 {
		log.Printf("Executing operational analytics query #%d", sequenceNumber)
	}
	
	result, err := h.cluster.AnalyticsQuery(query, nil)
	
	if err != nil {
		endTime := time.Now() // Capture end time for errors
		log.Printf("Operational analytics query #%d failed after %v: %v",
			sequenceNumber, endTime.Sub(startTime), err)
		
		return NewQueryExecutionMetrics(
			startTime, endTime, false, err.Error(), 0,
			"operational", queryName, sequenceNumber, absoluteStartTimeMs,
		)
	}
	
	// Count rows
	rowCount := 0
	for result.Next() {
		rowCount++
		var row interface{}
		result.Row(&row)
	}
	
	// ✅ FIXED: Capture end time AFTER row processing
	endTime := time.Now()
	
	if err := result.Err(); err != nil {
		log.Printf("Operational analytics query #%d row iteration failed: %v", sequenceNumber, err)
		return NewQueryExecutionMetrics(
			startTime, endTime, false, err.Error(), rowCount,
			"operational", queryName, sequenceNumber, absoluteStartTimeMs,
		)
	}
	
	result.Close()
	
	return NewQueryExecutionMetrics(
		startTime, endTime, true, "", rowCount,
		"operational", queryName, sequenceNumber, absoluteStartTimeMs,
	)
}

// GetSDKType returns the SDK type
func (h *OperationalSDKHandler) GetSDKType() string {
	return "operational"
}

// Close closes the SDK handler
func (h *OperationalSDKHandler) Close() error {
	if h.cluster != nil {
		return h.cluster.Close(nil)
	}
	return nil
} 