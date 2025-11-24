import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime
from src.lambdas.common.metrics import MetricsPublisher, get_metrics_publisher


class TestMetricsPublisher:
    """Tests for MetricsPublisher class"""
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_init(self, mock_boto_client):
        """Test MetricsPublisher initialization"""
        publisher = MetricsPublisher(namespace='TestNamespace')
        
        assert publisher.namespace == 'TestNamespace'
        mock_boto_client.assert_called_once_with('cloudwatch')
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_metric_basic(self, mock_boto_client):
        """Test basic metric publishing"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_metric('TestMetric', 100)
        
        # Verify CloudWatch API was called
        mock_cw.put_metric_data.assert_called_once()
        call_args = mock_cw.put_metric_data.call_args
        
        assert call_args[1]['Namespace'] == 'SiesaIntegration'
        metric_data = call_args[1]['MetricData'][0]
        assert metric_data['MetricName'] == 'TestMetric'
        assert metric_data['Value'] == 100
        assert metric_data['Unit'] == 'Count'
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_metric_with_dimensions(self, mock_boto_client):
        """Test metric publishing with dimensions"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_metric(
            'TestMetric',
            50,
            unit='Seconds',
            dimensions={'ClientId': 'client1', 'Status': 'Success'}
        )
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['Unit'] == 'Seconds'
        assert len(metric_data['Dimensions']) == 2
        assert {'Name': 'ClientId', 'Value': 'client1'} in metric_data['Dimensions']
        assert {'Name': 'Status', 'Value': 'Success'} in metric_data['Dimensions']
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_metric_error_handling(self, mock_boto_client):
        """Test that metric errors don't break flow"""
        mock_cw = Mock()
        mock_cw.put_metric_data.side_effect = Exception("CloudWatch error")
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        
        # Should not raise exception
        publisher.put_metric('TestMetric', 100)
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_sync_duration(self, mock_boto_client):
        """Test sync duration metric"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_sync_duration('client1', 45.5)
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'SyncDuration'
        assert metric_data['Value'] == 45.5
        assert metric_data['Unit'] == 'Seconds'
        assert {'Name': 'ClientId', 'Value': 'client1'} in metric_data['Dimensions']
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_records_processed_success(self, mock_boto_client):
        """Test records processed metric for success"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_records_processed('client1', 100, True)
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'RecordsProcessed'
        assert metric_data['Value'] == 100
        assert {'Name': 'ClientId', 'Value': 'client1'} in metric_data['Dimensions']
        assert {'Name': 'Status', 'Value': 'Success'} in metric_data['Dimensions']
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_records_processed_failure(self, mock_boto_client):
        """Test records processed metric for failure"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_records_processed('client1', 10, False)
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert {'Name': 'Status', 'Value': 'Failed'} in metric_data['Dimensions']
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_api_call_duration(self, mock_boto_client):
        """Test API call duration metric"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_api_call_duration('client1', 'Siesa', 2.5)
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'APICallDuration'
        assert metric_data['Value'] == 2.5
        assert metric_data['Unit'] == 'Seconds'
        assert {'Name': 'API', 'Value': 'Siesa'} in metric_data['Dimensions']
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_error_count(self, mock_boto_client):
        """Test error count metric"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_error_count('client1', 'ValueError')
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'ErrorCount'
        assert metric_data['Value'] == 1
        assert {'Name': 'ErrorType', 'Value': 'ValueError'} in metric_data['Dimensions']
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_circuit_breaker_state(self, mock_boto_client):
        """Test circuit breaker state metric"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        
        # Test CLOSED state
        publisher.put_circuit_breaker_state('client1', 'Siesa', 'CLOSED')
        metric_data = mock_cw.put_metric_data.call_args[1]['MetricData'][0]
        assert metric_data['Value'] == 0
        
        # Test HALF_OPEN state
        publisher.put_circuit_breaker_state('client1', 'Siesa', 'HALF_OPEN')
        metric_data = mock_cw.put_metric_data.call_args[1]['MetricData'][0]
        assert metric_data['Value'] == 1
        
        # Test OPEN state
        publisher.put_circuit_breaker_state('client1', 'Siesa', 'OPEN')
        metric_data = mock_cw.put_metric_data.call_args[1]['MetricData'][0]
        assert metric_data['Value'] == 2
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_rate_limit_delay(self, mock_boto_client):
        """Test rate limit delay metric"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_rate_limit_delay('client1', 'Kong', 0.5)
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'RateLimitDelay'
        assert metric_data['Value'] == 0.5
        assert metric_data['Unit'] == 'Seconds'
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_put_validation_errors(self, mock_boto_client):
        """Test validation errors metric"""
        mock_cw = Mock()
        mock_boto_client.return_value = mock_cw
        
        publisher = MetricsPublisher()
        publisher.put_validation_errors('client1', 5)
        
        call_args = mock_cw.put_metric_data.call_args
        metric_data = call_args[1]['MetricData'][0]
        
        assert metric_data['MetricName'] == 'ValidationErrors'
        assert metric_data['Value'] == 5


class TestGetMetricsPublisher:
    """Tests for get_metrics_publisher singleton"""
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_singleton_pattern(self, mock_boto_client):
        """Test that get_metrics_publisher returns singleton"""
        # Reset singleton
        import src.lambdas.common.metrics as metrics_module
        metrics_module._metrics_publisher = None
        
        publisher1 = get_metrics_publisher()
        publisher2 = get_metrics_publisher()
        
        assert publisher1 is publisher2
    
    @patch('src.lambdas.common.metrics.boto3.client')
    def test_returns_metrics_publisher(self, mock_boto_client):
        """Test that get_metrics_publisher returns MetricsPublisher instance"""
        publisher = get_metrics_publisher()
        
        assert isinstance(publisher, MetricsPublisher)
