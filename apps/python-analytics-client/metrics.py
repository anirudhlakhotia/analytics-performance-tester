"""
Query Execution Metrics

Data structure for tracking query performance metrics.
"""

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryExecutionMetrics:
    """Metrics for a single query execution"""
    
    start_time: float
    end_time: float
    success: bool
    error_message: str
    row_count: int
    sdk_type: str
    query_name: str
    sequence_number: int
    absolute_start_time_ms: int
    
    def __post_init__(self):
        """Calculate derived metrics after initialization"""
        self.duration_nanos = int((self.end_time - self.start_time) * 1_000_000_000)
        self.duration_ms = (self.end_time - self.start_time) * 1000.0
        self.absolute_end_time_ms = self.absolute_start_time_ms + int(self.duration_ms)
        self.timestamp = self.absolute_start_time_ms
        
        # Convert to nanoseconds since epoch for compatibility with Go/Java
        self.start_time_ns = int(self.start_time * 1_000_000_000)
        self.end_time_ns = int(self.end_time * 1_000_000_000)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "start_time": self.start_time_ns,
            "end_time": self.end_time_ns,
            "success": self.success,
            "error_message": self.error_message if self.error_message else "",
            "row_count": self.row_count,
            "sdk_type": self.sdk_type,
            "query_name": self.query_name,
            "duration_nanos": self.duration_nanos,
            "duration_ms": self.duration_ms,
            "absolute_start_time_ms": self.absolute_start_time_ms,
            "absolute_end_time_ms": self.absolute_end_time_ms,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp
        } 