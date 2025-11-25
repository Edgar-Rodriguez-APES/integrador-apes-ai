"""
Integration tests for complete ETL workflow
Tests the end-to-end flow: Extract → Transform → Load
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from moto import mock_dynamodb, mock_s3, mock_secretsmanager
import boto3

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from extractor.handler import lambda_handler as extractor_handler
from transformer.handler import lambda_handler as transformer_handler
from loader.handler import lambda_handler as loader_handler


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto"""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def dynamodb_setup(aws_credentials):
    """Setup DynamoDB tables for testing"""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create clients table
        table = dynamodb.create_table(
            TableName='siesa-integration-config-dev',
            KeySchema=[
                {'AttributeName': 'tenantId', 'KeyType': 'HASH'},
                {'AttributeName': 'configType', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'tenantId', 'AttributeType': 'S'},
                {'AttributeName': 'configType', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test client configuration
        table.put_item(Item={
            'tenantId': 'test-client',
            'configType': 'PRODUCT_CONFIG',
            'enabled': 'true',
            'siesaConfig': {
                'baseUrl': 'https://api.siesa.com',
                'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:siesa-creds',
                'companyId': 'TEST_CO',
                'branchId': 'MAIN'
            },
            'productConfig': {
                'baseUrl': 'https://api.kong.com',
                'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:kong-creds',
                'type_id': 1,
                'group_id': 1,
                'customer_id': 1
            },
            'fieldMappings': {
                'f_codigo': 'sku',
                'f_descripcion': 'name',
                'f_ean': 'ean'
            }
        })
        
        yield dynamodb


@pytest.fixture
def s3_setup(aws_credentials):
    """Setup S3 buckets for testing"""
    with mock_s3():
        s3 = boto3.client('s3', region_name='us-east-1')
        
        # Create test bucket
        s3.create_bucket(Bucket='siesa-integration-data-dev')
        
        # Upload field mappings
        field_mappings = {
            'f_codigo': 'sku',
            'f_descripcion': 'name',
            'f_ean': 'ean',
            'f_precio': 'price',
            'f_stock': 'stock_quantity'
        }
        
        s3.put_object(
            Bucket='siesa-integration-data-dev',
            Key='config/field-mappings-kong.json',
            Body=json.dumps(field_mappings)
        )
        
        yield s3


@pytest.fixture
def secrets_setup(aws_credentials):
    """Setup Secrets Manager for testing"""
    with mock_secretsmanager():
        secrets = boto3.client('secretsmanager', region_name='us-east-1')
        
        # Create SIESA credentials
        secrets.create_secret(
            Name='arn:aws:secretsmanager:us-east-1:123456789012:secret:siesa-creds',
            SecretString=json.dumps({
                'username': 'siesa_user',
                'password': 'siesa_pass',
                'api_key': 'siesa_key'
            })
        )
        
        # Create Kong credentials
        secrets.create_secret(
            Name='arn:aws:secretsmanager:us-east-1:123456789012:secret:kong-creds',
            SecretString=json.dumps({
                'username': 'kong_user',
                'password': 'kong_pass',
                'baseUrl': 'https://api.kong.com'
            })
        )
        
        yield secrets


@pytest.fixture
def sample_siesa_products():
    """Sample products from SIESA API"""
    return [
        {
            'f_codigo': 'PROD001',
            'f_descripcion': 'Product 1',
            'f_ean': '1234567890123',
            'f_precio': 100.0,
            'f_stock': 50
        },
        {
            'f_codigo': 'PROD002',
            'f_descripcion': 'Product 2',
            'f_ean': '9876543210987',
            'f_precio': 200.0,
            'f_stock': 25
        }
    ]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestETLWorkflow:
    """Integration tests for complete ETL workflow"""
    
    @patch('extractor.handler.requests.Session.get')
    @patch('transformer.handler.s3')
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_full_etl_workflow_success(self, mock_kong_post, mock_s3, mock_siesa_get,
                                      dynamodb_setup, s3_setup, secrets_setup,
                                      sample_siesa_products):
        """
        Test complete ETL workflow: Extract → Transform → Load
        This is the happy path where everything works correctly
        """
        # Setup environment variables
        os.environ['CLIENTS_TABLE'] = 'siesa-integration-config-dev'
        os.environ['DATA_BUCKET'] = 'siesa-integration-data-dev'
        
        # Mock SIESA API response (Extractor)
        mock_siesa_response = Mock()
        mock_siesa_response.status_code = 200
        mock_siesa_response.json.return_value = {
            'success': True,
            'data': sample_siesa_products
        }
        mock_siesa_response.raise_for_status = Mock()
        mock_siesa_get.return_value = mock_siesa_response
        
        # Mock S3 for field mappings (Transformer)
        mock_s3_client = Mock()
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'f_codigo': 'sku',
                'f_descripcion': 'name',
                'f_ean': 'ean',
                'f_precio': 'price',
                'f_stock': 'stock_quantity'
            }).encode())
        }
        mock_s3.client.return_value = mock_s3_client
        
        # Mock Kong API responses (Loader)
        # Authentication
        mock_auth_response = Mock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {'auth_token': 'test_token'}
        mock_auth_response.raise_for_status = Mock()
        
        # SKU creation
        mock_sku_response = Mock()
        mock_sku_response.status_code = 200
        mock_sku_response.json.return_value = {'status': 'success', 'count': 2}
        mock_sku_response.raise_for_status = Mock()
        
        mock_kong_post.side_effect = [mock_auth_response, mock_sku_response]
        
        # ===== STEP 1: EXTRACT =====
        extract_event = {
            'client_id': 'test-client',
            'source_type': 'siesa'
        }
        
        extract_result = extractor_handler(extract_event, None)
        
        assert extract_result['client_id'] == 'test-client'
        assert extract_result['status'] == 'success'
        assert extract_result['records_extracted'] == 2
        assert len(extract_result['raw_products']) == 2
        
        # ===== STEP 2: TRANSFORM =====
        transform_event = {
            'client_id': 'test-client',
            'source_type': 'siesa',
            'raw_products': extract_result['raw_products'],
            'extraction_timestamp': extract_result['extraction_timestamp']
        }
        
        transform_result = transformer_handler(transform_event, None)
        
        assert transform_result['client_id'] == 'test-client'
        assert transform_result['status'] == 'success'
        assert transform_result['records_transformed'] == 2
        assert len(transform_result['canonical_products']) == 2
        
        # Verify transformation
        canonical_product = transform_result['canonical_products'][0]
        assert canonical_product['sku'] == 'PROD001'
        assert canonical_product['name'] == 'Product 1'
        assert canonical_product['ean'] == '1234567890123'
        
        # ===== STEP 3: LOAD =====
        load_event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'canonical_products': transform_result['canonical_products'],
            'extraction_timestamp': extract_result['extraction_timestamp'],
            'transformation_timestamp': transform_result['transformation_timestamp']
        }
        
        load_result = loader_handler(load_event, None)
        
        assert load_result['client_id'] == 'test-client'
        assert load_result['status'] == 'success'
        assert load_result['records_success'] == 2
        assert load_result['records_failed'] == 0
        
        # Verify end-to-end flow
        assert extract_result['records_extracted'] == transform_result['records_transformed']
        assert transform_result['records_transformed'] == load_result['records_success']
    
    @patch('extractor.handler.requests.Session.get')
    def test_etl_workflow_extraction_error(self, mock_siesa_get, dynamodb_setup, secrets_setup):
        """
        Test ETL workflow with extraction error
        Verifies error handling in the extraction phase
        """
        os.environ['CLIENTS_TABLE'] = 'siesa-integration-config-dev'
        
        # Mock SIESA API error
        mock_siesa_get.side_effect = Exception("SIESA API connection failed")
        
        extract_event = {
            'client_id': 'test-client',
            'source_type': 'siesa'
        }
        
        # Extraction should raise exception
        with pytest.raises(Exception, match="Extractor Lambda failed"):
            extractor_handler(extract_event, None)
    
    @patch('extractor.handler.requests.Session.get')
    @patch('transformer.handler.s3')
    def test_etl_workflow_transformation_error(self, mock_s3, mock_siesa_get,
                                               dynamodb_setup, s3_setup, secrets_setup,
                                               sample_siesa_products):
        """
        Test ETL workflow with transformation error
        Verifies error handling in the transformation phase
        """
        os.environ['CLIENTS_TABLE'] = 'siesa-integration-config-dev'
        os.environ['DATA_BUCKET'] = 'siesa-integration-data-dev'
        
        # Mock successful extraction
        mock_siesa_response = Mock()
        mock_siesa_response.status_code = 200
        mock_siesa_response.json.return_value = {
            'success': True,
            'data': sample_siesa_products
        }
        mock_siesa_response.raise_for_status = Mock()
        mock_siesa_get.return_value = mock_siesa_response
        
        # Extract successfully
        extract_event = {
            'client_id': 'test-client',
            'source_type': 'siesa'
        }
        extract_result = extractor_handler(extract_event, None)
        
        # Mock S3 error for field mappings
        mock_s3.client.side_effect = Exception("S3 access denied")
        
        # Transform should handle error
        transform_event = {
            'client_id': 'test-client',
            'source_type': 'siesa',
            'raw_products': extract_result['raw_products'],
            'extraction_timestamp': extract_result['extraction_timestamp']
        }
        
        with pytest.raises(Exception, match="Transformer Lambda failed"):
            transformer_handler(transform_event, None)
    
    @patch('extractor.handler.requests.Session.get')
    @patch('transformer.handler.s3')
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_etl_workflow_partial_load_failure(self, mock_kong_post, mock_s3, mock_siesa_get,
                                               dynamodb_setup, s3_setup, secrets_setup):
        """
        Test ETL workflow with partial load failure
        Some products load successfully, others fail validation
        """
        os.environ['CLIENTS_TABLE'] = 'siesa-integration-config-dev'
        os.environ['DATA_BUCKET'] = 'siesa-integration-data-dev'
        
        # Products with mixed validity
        mixed_products = [
            {
                'f_codigo': 'PROD001',
                'f_descripcion': 'Valid Product',
                'f_ean': '1234567890123'
            },
            {
                'f_codigo': 'PROD002',
                'f_descripcion': '',  # Invalid: empty name
                'f_ean': 'invalid'  # Invalid: bad EAN
            }
        ]
        
        # Mock SIESA API
        mock_siesa_response = Mock()
        mock_siesa_response.status_code = 200
        mock_siesa_response.json.return_value = {
            'success': True,
            'data': mixed_products
        }
        mock_siesa_response.raise_for_status = Mock()
        mock_siesa_get.return_value = mock_siesa_response
        
        # Mock S3
        mock_s3_client = Mock()
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'f_codigo': 'sku',
                'f_descripcion': 'name',
                'f_ean': 'ean'
            }).encode())
        }
        mock_s3.client.return_value = mock_s3_client
        
        # Mock Kong API
        mock_auth_response = Mock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {'auth_token': 'test_token'}
        mock_auth_response.raise_for_status = Mock()
        
        mock_sku_response = Mock()
        mock_sku_response.status_code = 200
        mock_sku_response.json.return_value = {'status': 'success', 'count': 1}
        mock_sku_response.raise_for_status = Mock()
        
        mock_kong_post.side_effect = [mock_auth_response, mock_sku_response]
        
        # Run full workflow
        extract_event = {'client_id': 'test-client', 'source_type': 'siesa'}
        extract_result = extractor_handler(extract_event, None)
        
        transform_event = {
            'client_id': 'test-client',
            'source_type': 'siesa',
            'raw_products': extract_result['raw_products'],
            'extraction_timestamp': extract_result['extraction_timestamp']
        }
        transform_result = transformer_handler(transform_event, None)
        
        load_event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'canonical_products': transform_result['canonical_products'],
            'extraction_timestamp': extract_result['extraction_timestamp'],
            'transformation_timestamp': transform_result['transformation_timestamp']
        }
        load_result = loader_handler(load_event, None)
        
        # Verify partial success
        assert load_result['status'] in ['partial', 'failed']
        assert load_result['records_success'] >= 0
        assert load_result['records_failed'] > 0
        assert len(load_result['failed_records']) > 0
    
    @patch('extractor.handler.requests.Session.get')
    @patch('transformer.handler.s3')
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_etl_workflow_large_dataset(self, mock_kong_post, mock_s3, mock_siesa_get,
                                       dynamodb_setup, s3_setup, secrets_setup):
        """
        Test ETL workflow with large dataset (100 products)
        Verifies batch processing and performance
        """
        os.environ['CLIENTS_TABLE'] = 'siesa-integration-config-dev'
        os.environ['DATA_BUCKET'] = 'siesa-integration-data-dev'
        os.environ['BATCH_SIZE'] = '50'  # Process in batches of 50
        
        # Generate large dataset
        large_dataset = [
            {
                'f_codigo': f'PROD{i:04d}',
                'f_descripcion': f'Product {i}',
                'f_ean': f'{1234567890000 + i:013d}',
                'f_precio': 100.0 + i,
                'f_stock': 50 + i
            }
            for i in range(1, 101)
        ]
        
        # Mock SIESA API
        mock_siesa_response = Mock()
        mock_siesa_response.status_code = 200
        mock_siesa_response.json.return_value = {
            'success': True,
            'data': large_dataset
        }
        mock_siesa_response.raise_for_status = Mock()
        mock_siesa_get.return_value = mock_siesa_response
        
        # Mock S3
        mock_s3_client = Mock()
        mock_s3_client.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'f_codigo': 'sku',
                'f_descripcion': 'name',
                'f_ean': 'ean',
                'f_precio': 'price',
                'f_stock': 'stock_quantity'
            }).encode())
        }
        mock_s3.client.return_value = mock_s3_client
        
        # Mock Kong API (will be called multiple times for batches)
        mock_auth_response = Mock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {'auth_token': 'test_token'}
        mock_auth_response.raise_for_status = Mock()
        
        mock_sku_response = Mock()
        mock_sku_response.status_code = 200
        mock_sku_response.json.return_value = {'status': 'success', 'count': 50}
        mock_sku_response.raise_for_status = Mock()
        
        # Auth + 2 batch calls (50 products each)
        mock_kong_post.side_effect = [
            mock_auth_response,
            mock_sku_response,
            mock_sku_response
        ]
        
        # Run full workflow
        extract_event = {'client_id': 'test-client', 'source_type': 'siesa'}
        extract_result = extractor_handler(extract_event, None)
        
        assert extract_result['records_extracted'] == 100
        
        transform_event = {
            'client_id': 'test-client',
            'source_type': 'siesa',
            'raw_products': extract_result['raw_products'],
            'extraction_timestamp': extract_result['extraction_timestamp']
        }
        transform_result = transformer_handler(transform_event, None)
        
        assert transform_result['records_transformed'] == 100
        
        load_event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'canonical_products': transform_result['canonical_products'],
            'extraction_timestamp': extract_result['extraction_timestamp'],
            'transformation_timestamp': transform_result['transformation_timestamp']
        }
        load_result = loader_handler(load_event, None)
        
        # Verify all 100 products were processed
        assert load_result['records_success'] == 100
        assert load_result['records_failed'] == 0
        assert load_result['status'] == 'success'
