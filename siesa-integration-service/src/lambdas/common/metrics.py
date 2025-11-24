"""
CloudWatch Metrics Publisher
Publishes custom metrics for monitoring integration performance
"""

import boto3
from datetime import datetime
from typing import Dict, Optional
import logging

# Use standard logging for metrics to avoid circular dependencies
logger = logging.getLogger(__name__)


class MetricsPublisher:
    """Publisher for CloudWatch custom metrics"""
    
    def __init__(self, namespace='SiesaIntegration'):
        self.cloudwatch = boto3.client('cloudwatch')
        self.namespace = namespace
    
    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'Count',
        dimensions: Optional[Dict[str, str]] = None
    ):
        """
        Publish a custom metric to CloudWatch
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement (Count, Seconds, etc.)
            dimensions: Optional dimensions for filtering
        """
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Published metric: {metric_name}={value} {unit}")
            
        except Exception as e:
            # Don't break flow on metrics errors
            logger.warning(f"Failed to publish metric {metric_name}: {str(e)}")
    
    def put_sync_duration(self, client_id: str, duration_seconds: float):
        """
        Publish sync duration metric
        
        Args:
            client_id: Client identifier
            duration_seconds: Duration in seconds
        """
        self.put_metric(
            'SyncDuration',
            duration_seconds,
            unit='Seconds',
            dimensions={'ClientId': client_id}
        )
    
    def put_records_processed(self, client_id: str, count: int, success: bool):
        """
        Publish records processed metric
        
        Args:
            client_id: Client identifier
            count: Number of records
            success: Whether processing was successful
        """
        self.put_metric(
            'RecordsProcessed',
            count,
            dimensions={
                'ClientId': client_id,
                'Status': 'Success' if success else 'Failed'
            }
        )
    
    def put_api_call_duration(self, client_id: str, api_name: str, duration_seconds: float):
        """
        Publish API call duration metric
        
        Args:
            client_id: Client identifier
            api_name: Name of the API (Siesa, Kong, etc.)
            duration_seconds: Duration in seconds
        """
        self.put_metric(
            'APICallDuration',
            duration_seconds,
            unit='Seconds',
            dimensions={
                'ClientId': client_id,
                'API': api_name
            }
        )
    
    def put_error_count(self, client_id: str, error_type: str):
        """
        Publish error count metric
        
        Args:
            client_id: Client identifier
            error_type: Type of error
        """
        self.put_metric(
            'ErrorCount',
            1,
            dimensions={
                'ClientId': client_id,
                'ErrorType': error_type
            }
        )
    
    def put_circuit_breaker_state(self, client_id: str, api_name: str, state: str):
        """
        Publish circuit breaker state metric
        
        Args:
            client_id: Client identifier
            api_name: Name of the API
            state: Circuit breaker state (OPEN, CLOSED, HALF_OPEN)
        """
        # Convert state to numeric value for CloudWatch
        state_values = {
            'CLOSED': 0,
            'HALF_OPEN': 1,
            'OPEN': 2
        }
        
        self.put_metric(
            'CircuitBreakerState',
            state_values.get(state, 0),
            dimensions={
                'ClientId': client_id,
                'API': api_name
            }
        )
    
    def put_rate_limit_delay(self, client_id: str, api_name: str, delay_seconds: float):
        """
        Publish rate limit delay metric
        
        Args:
            client_id: Client identifier
            api_name: Name of the API
            delay_seconds: Delay applied in seconds
        """
        self.put_metric(
            'RateLimitDelay',
            delay_seconds,
            unit='Seconds',
            dimensions={
                'ClientId': client_id,
                'API': api_name
            }
        )
    
    def put_validation_errors(self, client_id: str, error_count: int):
        """
        Publish validation errors metric
        
        Args:
            client_id: Client identifier
            error_count: Number of validation errors
        """
        self.put_metric(
            'ValidationErrors',
            error_count,
            dimensions={'ClientId': client_id}
        )


# Singleton instance
_metrics_publisher = None


def get_metrics_publisher() -> MetricsPublisher:
    """
    Get singleton metrics publisher instance
    
    Returns:
        MetricsPublisher instance
    """
    global _metrics_publisher
    if _metrics_publisher is None:
        _metrics_publisher = MetricsPublisher()
    return _metrics_publisher
