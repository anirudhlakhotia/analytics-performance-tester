"""
SDK Handler Interface and Implementations

Provides abstraction over operational and enterprise analytics SDKs.
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional
from urllib.parse import urlparse

from metrics import QueryExecutionMetrics

logger = logging.getLogger(__name__)


class AnalyticsSDKHandler(ABC):
    """Interface for SDK handlers"""
    
    @abstractmethod
    def execute_query(self, query: str, query_name: str, sequence_number: int) -> QueryExecutionMetrics:
        """Execute a query and return metrics"""
        pass
    
    @abstractmethod
    def get_sdk_type(self) -> str:
        """Return the SDK type identifier"""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the SDK handler and cleanup resources"""
        pass


class OperationalSDKHandler(AnalyticsSDKHandler):
    """Handler for operational SDK operations"""
    
    def __init__(self, config):
        from couchbase.cluster import Cluster
        from couchbase.options import ClusterOptions, ClusterTimeoutOptions
        from couchbase.auth import PasswordAuthenticator
        
        # Add the escape-hatch so the operational SDK can talk to Enterprise-Analytics
        conn_str = config.connection_string
        if "allow_enterprise_analytics=" not in conn_str:
            separator = "&" if "?" in conn_str else "?"
            conn_str += f"{separator}allow_enterprise_analytics=true"
        
        logger.info("########################################################")
        logger.info(f"Using connection string: {conn_str}")
        logger.info("########################################################")
        
        # Create cluster options
        timeout_opts = ClusterTimeoutOptions(
            analytics_timeout=timedelta(seconds=config.analytics_timeout_s),
            connect_timeout=timedelta(seconds=config.connection_timeout_s)
        )
        
        cluster_opts = ClusterOptions(
            authenticator=PasswordAuthenticator(config.username, config.password),
            timeout_options=timeout_opts
        )
        
        # Connect to cluster using static method
        self.cluster = Cluster.connect(conn_str, cluster_opts)
        
        # Wait until ready
        self.cluster.wait_until_ready(timedelta(seconds=config.connection_timeout_s))
        
        logger.info("✅ Operational SDK connected successfully")
        
        # Sleep for 15 seconds (matching Go implementation)
        time.sleep(15)
    
    def execute_query(self, query: str, query_name: str, sequence_number: int) -> QueryExecutionMetrics:
        absolute_start_time_ms = int(time.time() * 1000)
        start_time = time.perf_counter()
        
        if sequence_number <= 10 or sequence_number % 1000 == 0:
            logger.info(f"Executing operational analytics query #{sequence_number}")
        
        try:
            result = self.cluster.analytics_query(query)
            
            # Count rows
            row_count = 0
            for row in result.rows():
                row_count += 1
            
            # Capture end time AFTER row processing
            end_time = time.perf_counter()
            
            return QueryExecutionMetrics(
                start_time, end_time, True, "", row_count,
                "operational", query_name, sequence_number, absolute_start_time_ms
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            error_msg = str(e)
            logger.info(f"Operational analytics query #{sequence_number} failed after "
                       f"{(end_time - start_time) * 1000:.2f}ms: {error_msg}")
            
            return QueryExecutionMetrics(
                start_time, end_time, False, error_msg, 0,
                "operational", query_name, sequence_number, absolute_start_time_ms
            )
    
    def get_sdk_type(self) -> str:
        return "operational"
    
    def close(self) -> None:
        if hasattr(self, 'cluster') and self.cluster:
            self.cluster.close()


class EnterpriseSDKHandler(AnalyticsSDKHandler):
    """Handler for enterprise SDK operations"""
    
    def __init__(self, config):
        from couchbase_analytics.cluster import Cluster
        from couchbase_analytics.credential import Credential
        from couchbase_analytics.options import ClusterOptions, TimeoutOptions
        
        # Parse host from connection string
        parsed = urlparse(config.connection_string.replace("couchbase://", "http://"))
        host = parsed.hostname
        analytics_url = f"http://{host}:8095"
        
        # Create credential
        credential = Credential.from_username_and_password(config.username, config.password)
        
        # Create cluster options
        timeout_opts = TimeoutOptions(
            query_timeout=timedelta(seconds=config.analytics_timeout_s),
            connect_timeout=timedelta(seconds=config.connection_timeout_s)
        )
        
        cluster_opts = ClusterOptions(timeout_options=timeout_opts)
        
        # Connect to cluster using static method
        self.cluster = Cluster.create_instance(analytics_url, credential, cluster_opts)
        
        # Test connection
        test_result = self.cluster.execute_query("SELECT 1 as test")
        # Consume the result to complete the test
        for row in test_result.rows():
            pass  # Just consume rows
        
        logger.info("✅ Enterprise SDK connected successfully")
    
    def execute_query(self, query: str, query_name: str, sequence_number: int) -> QueryExecutionMetrics:
        absolute_start_time_ms = int(time.time() * 1000)
        start_time = time.perf_counter()
        
        if sequence_number <= 10 or sequence_number % 1000 == 0:
            logger.info(f"Executing enterprise analytics query #{sequence_number}")
        
        try:
            result = self.cluster.execute_query(query)
            
            # Count rows
            row_count = 0
            for row in result.rows():
                row_count += 1
            
            # Capture end time AFTER row processing
            end_time = time.perf_counter()
            
            return QueryExecutionMetrics(
                start_time, end_time, True, "", row_count,
                "enterprise", query_name, sequence_number, absolute_start_time_ms
            )
            
        except Exception as e:
            end_time = time.perf_counter()
            error_msg = str(e)
            logger.info(f"Enterprise analytics query #{sequence_number} failed: {error_msg}")
            
            return QueryExecutionMetrics(
                start_time, end_time, False, error_msg, 0,
                "enterprise", query_name, sequence_number, absolute_start_time_ms
            )
    
    def get_sdk_type(self) -> str:
        return "enterprise"
    
    def close(self) -> None:
        if hasattr(self, 'cluster') and self.cluster:
            self.cluster.shutdown()


def create_sdk_handler(config) -> AnalyticsSDKHandler:
    """Create appropriate SDK handler based on configuration"""
    if config.sdk_type == "operational":
        return OperationalSDKHandler(config)
    elif config.sdk_type == "enterprise":
        return EnterpriseSDKHandler(config)
    else:
        raise ValueError(f"Unknown SDK type: {config.sdk_type}") 