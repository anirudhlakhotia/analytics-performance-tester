package main

import (
	"time"
)

// QueryExecutionMetrics represents metrics for a single query execution
type QueryExecutionMetrics struct {
	StartTime           int64   `json:"start_time"`
	EndTime             int64   `json:"end_time"`
	Success             bool    `json:"success"`
	ErrorMessage        string  `json:"error_message,omitempty"`
	RowCount            int     `json:"row_count"`
	SDKType             string  `json:"sdk_type"`
	QueryName           string  `json:"query_name"`
	DurationNanos       int64   `json:"duration_nanos"`
	DurationMs          float64 `json:"duration_ms"`
	AbsoluteStartTimeMs int64   `json:"absolute_start_time_ms"`
	AbsoluteEndTimeMs   int64   `json:"absolute_end_time_ms"`
	SequenceNumber      int     `json:"sequence_number"`
	Timestamp           int64   `json:"timestamp"`
}

// NewQueryExecutionMetrics creates a new metrics instance
func NewQueryExecutionMetrics(
	startTime, endTime time.Time,
	success bool,
	errorMessage string,
	rowCount int,
	sdkType, queryName string,
	sequenceNumber int,
	absoluteStartTimeMs int64,
) *QueryExecutionMetrics {
	durationNanos := endTime.Sub(startTime).Nanoseconds()
	absoluteEndTimeMs := absoluteStartTimeMs + (durationNanos / 1_000_000)
	
	return &QueryExecutionMetrics{
		StartTime:           startTime.UnixNano(),
		EndTime:             endTime.UnixNano(),
		Success:             success,
		ErrorMessage:        errorMessage,
		RowCount:            rowCount,
		SDKType:             sdkType,
		QueryName:           queryName,
		DurationNanos:       durationNanos,
		DurationMs:          float64(durationNanos) / 1_000_000.0,
		AbsoluteStartTimeMs: absoluteStartTimeMs,
		AbsoluteEndTimeMs:   absoluteEndTimeMs,
		SequenceNumber:      sequenceNumber,
		Timestamp:           absoluteStartTimeMs,
	}
} 