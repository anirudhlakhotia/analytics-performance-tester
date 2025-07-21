package main

// AnalyticsSDKHandler defines the interface for SDK handlers
type AnalyticsSDKHandler interface {
	ExecuteQuery(query, queryName string, sequenceNumber int) *QueryExecutionMetrics
	GetSDKType() string
	Close() error
}