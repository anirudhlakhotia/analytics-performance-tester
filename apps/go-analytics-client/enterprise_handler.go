package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	cbanalytics "github.com/couchbase/gocbanalytics"
)

// EnterpriseSDKHandler handles enterprise SDK operations
type EnterpriseSDKHandler struct {
	cluster        *cbanalytics.Cluster
	queryTimeout   time.Duration
}

// NewEnterpriseSDKHandler creates a new enterprise SDK handler
func NewEnterpriseSDKHandler(config Configuration) (*EnterpriseSDKHandler, error) {
	// Parse host from connection string
	host := strings.Replace(config.ConnectionString, "couchbase://", "", 1)
	host = strings.Split(host, ":")[0]
	analyticsURL := fmt.Sprintf("http://%s:8095", host)
	
	// Create credential
	credential := cbanalytics.NewBasicAuthCredential(config.Username, config.Password)
	
	// Create cluster options
	opts := cbanalytics.NewClusterOptions().
		SetTimeoutOptions(cbanalytics.NewTimeoutOptions().
			SetQueryTimeout(time.Duration(config.AnalyticsTimeoutS) * time.Second).
			SetConnectTimeout(time.Duration(config.ConnectionTimeoutS) * time.Second))
	
	// Connect to cluster
	cluster, err := cbanalytics.NewCluster(analyticsURL, credential, opts)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to analytics cluster: %w", err)
	}
	
	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(config.ConnectionTimeoutS)*time.Second)
	defer cancel()
	
	testResult, err := cluster.ExecuteQuery(ctx, "SELECT 1 as test")
	if err != nil {
		cluster.Close()
		return nil, fmt.Errorf("failed to test analytics connection: %w", err)
	}
	
	// Consume the result to complete the test
	for testResult.NextRow() != nil {
		// Just consume rows
	}
	
	if err := testResult.Err(); err != nil {
		cluster.Close()
		return nil, fmt.Errorf("failed to test analytics connection: %w", err)
	}
	
	log.Println("✅ Enterprise SDK connected successfully")
	
	return &EnterpriseSDKHandler{
		cluster:        cluster,
		queryTimeout:   time.Duration(config.AnalyticsTimeoutS) * time.Second,
	}, nil
}

// ExecuteQuery executes a query using the enterprise SDK
func (h *EnterpriseSDKHandler) ExecuteQuery(query, queryName string, sequenceNumber int) *QueryExecutionMetrics {
	absoluteStartTimeMs := time.Now().UnixMilli()
	startTime := time.Now()

	if sequenceNumber <= 10 || sequenceNumber%1000 == 0 {
		log.Printf("Executing enterprise analytics query #%d", sequenceNumber)
	}
	
	// ✅ FIXED: Use configured timeout
	ctx, cancel := context.WithTimeout(context.Background(), h.queryTimeout)
	defer cancel()
	
	result, err := h.cluster.ExecuteQuery(ctx, query)
	
	if err != nil {
		endTime := time.Now() // Capture end time for errors
		log.Printf("Enterprise analytics query #%d failed: %v", sequenceNumber, err)
		return NewQueryExecutionMetrics(
			startTime, endTime, false, err.Error(), 0,
			"enterprise", queryName, sequenceNumber, absoluteStartTimeMs,
		)
	}
	
	// Count rows
	rowCount := 0
	for row := result.NextRow(); row != nil; row = result.NextRow() {
		rowCount++
		var data interface{}
		row.ContentAs(&data)
	}
	
	// ✅ FIXED: Capture end time AFTER row processing
	endTime := time.Now()
	
	if err := result.Err(); err != nil {
		log.Printf("Enterprise analytics query #%d row iteration failed: %v", sequenceNumber, err)
		return NewQueryExecutionMetrics(
			startTime, endTime, false, err.Error(), rowCount,
			"enterprise", queryName, sequenceNumber, absoluteStartTimeMs,
		)
	}
	
	return NewQueryExecutionMetrics(
		startTime, endTime, true, "", rowCount,
		"enterprise", queryName, sequenceNumber, absoluteStartTimeMs,
	)
}

// GetSDKType returns the SDK type
func (h *EnterpriseSDKHandler) GetSDKType() string {
	return "enterprise"
}

// Close closes the SDK handler
func (h *EnterpriseSDKHandler) Close() error {
	if h.cluster != nil {
		return h.cluster.Close()
	}
	return nil
} 