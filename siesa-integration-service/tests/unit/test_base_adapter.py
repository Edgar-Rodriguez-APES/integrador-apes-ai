"""
Unit tests for Base Product Adapter
Tests the process_batch method which orchestrates validation and loading
"""
import pytest
from typing import Dict, List, Any, Tuple

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from loader.adapters.base_adapter import ProductAdapter


# ============================================================================
# Test Implementation of ProductAdapter
# ============================================================================

class TestProductAdapter(ProductAdapter):
    """Concrete implementation for testing"""
    
    def __init__(self, credentials: Dict[str, Any], config: Dict[str, Any], 
                 should_fail_validation: bool = False,
                 should_fail_load: bool = False):
        super().__init__(credentials, config)
        self.should_fail_validation = should_fail_validation
        self.should_fail_load = should_fail_load
        self.transform_called = False
        self.validate_called = False
        self.load_called = False
    
    def get_api_client(self):
        """Mock API client"""
        return None
    
    def transform_products(self, canonical_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform products - just pass through with a marker"""
        self.transform_called = True
        return [{'transformed': True, **p} for p in canonical_products]
    
    def validate_product(self, product: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate product"""
        self.validate_called = True
        
        if self.should_fail_validation:
            return False, "Validation failed for testing"
        
        # Check required fields
        if 'id' not in product:
            return False, "Missing required field: id"
        
        if 'name' not in product:
            return False, "Missing required field: name"
        
        return True, ""
    
    def load_batch(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Load batch"""
        self.load_called = True
        
        if self.should_fail_load:
            raise Exception("Load failed for testing")
        
        return {
            'records_processed': len(products),
            'records_success': len(products),
            'records_failed': 0
        }


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def valid_products():
    """Valid canonical products"""
    return [
        {'id': 'PROD001', 'name': 'Product 1', 'sku': 'SKU001'},
        {'id': 'PROD002', 'name': 'Product 2', 'sku': 'SKU002'},
        {'id': 'PROD003', 'name': 'Product 3', 'sku': 'SKU003'}
    ]


@pytest.fixture
def mixed_products():
    """Mix of valid and invalid products"""
    return [
        {'id': 'PROD001', 'name': 'Product 1'},  # Valid
        {'name': 'Product 2'},  # Invalid: missing id
        {'id': 'PROD003'},  # Invalid: missing name
        {'id': 'PROD004', 'name': 'Product 4'}  # Valid
    ]


# ============================================================================
# TESTS
# ============================================================================

class TestBaseAdapterProcessBatch:
    """Tests for process_batch method"""
    
    def test_process_batch_all_valid(self, valid_products):
        """Test processing batch with all valid products"""
        adapter = TestProductAdapter({}, {})
        
        result = adapter.process_batch(valid_products, batch_size=10)
        
        # Verify all methods were called
        assert adapter.transform_called
        assert adapter.validate_called
        assert adapter.load_called
        
        # Verify results
        assert result['total_input'] == 3
        assert result['total_valid'] == 3
        assert result['total_processed'] == 3
        assert result['total_success'] == 3
        assert result['total_failed'] == 0
        assert len(result['validation_errors']) == 0
        assert len(result['batch_results']) == 1  # One batch
    
    def test_process_batch_with_validation_errors(self, mixed_products):
        """Test processing batch with validation errors"""
        adapter = TestProductAdapter({}, {})
        
        result = adapter.process_batch(mixed_products, batch_size=10)
        
        # Verify results
        assert result['total_input'] == 4
        assert result['total_valid'] == 2  # Only 2 valid
        assert result['total_processed'] == 2
        assert result['total_success'] == 2
        assert result['total_failed'] == 2  # 2 validation errors
        assert len(result['validation_errors']) == 2
        
        # Check validation error details
        errors = result['validation_errors']
        assert any('id' in e['error'] for e in errors)
        assert any('name' in e['error'] for e in errors)
    
    def test_process_batch_multiple_batches(self, valid_products):
        """Test processing with multiple batches"""
        # Create larger dataset
        large_dataset = valid_products * 10  # 30 products
        
        adapter = TestProductAdapter({}, {})
        
        result = adapter.process_batch(large_dataset, batch_size=10)
        
        # Verify results
        assert result['total_input'] == 30
        assert result['total_valid'] == 30
        assert result['total_processed'] == 30
        assert result['total_success'] == 30
        assert result['total_failed'] == 0
        assert len(result['batch_results']) == 3  # 3 batches of 10
        
        # Verify each batch
        for batch_result in result['batch_results']:
            assert batch_result['processed'] == 10
            assert batch_result['success'] == 10
            assert batch_result['failed'] == 0
    
    def test_process_batch_load_failure(self, valid_products):
        """Test processing when load fails"""
        adapter = TestProductAdapter({}, {}, should_fail_load=True)
        
        result = adapter.process_batch(valid_products, batch_size=10)
        
        # Verify results
        assert result['total_input'] == 3
        assert result['total_valid'] == 3
        assert result['total_success'] == 0  # Load failed
        assert result['total_failed'] == 3
        assert len(result['batch_results']) == 1
        
        # Check batch result has error
        batch_result = result['batch_results'][0]
        assert batch_result['success'] == 0
        assert batch_result['failed'] == 3
        assert 'error' in batch_result
    
    def test_process_batch_empty_input(self):
        """Test processing empty input"""
        adapter = TestProductAdapter({}, {})
        
        result = adapter.process_batch([], batch_size=10)
        
        # Verify results
        assert result['total_input'] == 0
        assert result['total_valid'] == 0
        assert result['total_processed'] == 0
        assert result['total_success'] == 0
        assert result['total_failed'] == 0
        assert len(result['validation_errors']) == 0
        assert len(result['batch_results']) == 0
    
    def test_process_batch_all_invalid(self):
        """Test processing when all products are invalid"""
        invalid_products = [
            {'name': 'Product 1'},  # Missing id
            {'id': 'PROD002'},  # Missing name
            {}  # Missing both
        ]
        
        adapter = TestProductAdapter({}, {})
        
        result = adapter.process_batch(invalid_products, batch_size=10)
        
        # Verify results
        assert result['total_input'] == 3
        assert result['total_valid'] == 0
        assert result['total_processed'] == 0
        assert result['total_success'] == 0
        assert result['total_failed'] == 3
        assert len(result['validation_errors']) == 3
        assert len(result['batch_results']) == 0  # No batches loaded
    
    def test_process_batch_small_batch_size(self, valid_products):
        """Test processing with small batch size"""
        adapter = TestProductAdapter({}, {})
        
        result = adapter.process_batch(valid_products, batch_size=1)
        
        # Verify results
        assert result['total_input'] == 3
        assert result['total_success'] == 3
        assert len(result['batch_results']) == 3  # 3 batches of 1
        
        # Each batch should have 1 product
        for batch_result in result['batch_results']:
            assert batch_result['processed'] == 1
            assert batch_result['success'] == 1
    
    def test_process_batch_transformation_applied(self, valid_products):
        """Test that transformation is applied to products"""
        adapter = TestProductAdapter({}, {})
        
        # We can't directly inspect transformed products, but we can verify
        # the transformation was called and products were processed
        result = adapter.process_batch(valid_products, batch_size=10)
        
        assert adapter.transform_called
        assert result['total_success'] == 3
    
    def test_process_batch_partial_batch_failure(self):
        """Test processing when some batches fail"""
        # Create a custom adapter that fails on second batch
        class PartialFailAdapter(TestProductAdapter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.batch_count = 0
            
            def load_batch(self, products):
                self.batch_count += 1
                if self.batch_count == 2:
                    raise Exception("Second batch failed")
                return super().load_batch(products)
        
        products = [
            {'id': f'PROD{i:03d}', 'name': f'Product {i}'}
            for i in range(1, 21)  # 20 products
        ]
        
        adapter = PartialFailAdapter({}, {})
        result = adapter.process_batch(products, batch_size=10)
        
        # First batch succeeds, second fails
        assert result['total_input'] == 20
        assert result['total_valid'] == 20
        assert result['total_success'] == 10  # Only first batch
        assert result['total_failed'] == 10  # Second batch failed
        assert len(result['batch_results']) == 2
        
        # Check individual batch results
        assert result['batch_results'][0]['success'] == 10
        assert result['batch_results'][1]['failed'] == 10


class TestBaseAdapterAbstractMethods:
    """Test that abstract methods must be implemented"""
    
    def test_cannot_instantiate_base_adapter(self):
        """Test that ProductAdapter cannot be instantiated directly"""
        with pytest.raises(TypeError):
            ProductAdapter({}, {})
    
    def test_concrete_adapter_has_all_methods(self):
        """Test that concrete adapter implements all required methods"""
        adapter = TestProductAdapter({}, {})
        
        # Verify all abstract methods are implemented
        assert hasattr(adapter, 'get_api_client')
        assert hasattr(adapter, 'transform_products')
        assert hasattr(adapter, 'validate_product')
        assert hasattr(adapter, 'load_batch')
        assert hasattr(adapter, 'process_batch')
        
        # Verify they are callable
        assert callable(adapter.get_api_client)
        assert callable(adapter.transform_products)
        assert callable(adapter.validate_product)
        assert callable(adapter.load_batch)
        assert callable(adapter.process_batch)
