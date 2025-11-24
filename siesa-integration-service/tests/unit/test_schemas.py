import pytest
from pydantic import ValidationError
from src.lambdas.common.schemas import SiesaProduct, CanonicalProduct


class TestSiesaProduct:
    """Tests for SiesaProduct schema"""
    
    def test_valid_product(self):
        """Test valid Siesa product"""
        product = SiesaProduct(
            f_codigo="PROD001",
            f_nombre="Test Product",
            f_codigo_externo="EXT001",
            f_referencia="REF001",
            f_ean="1234567890123"
        )
        
        assert product.f_codigo == "PROD001"
        assert product.f_nombre == "Test Product"
        assert product.f_codigo_externo == "EXT001"
    
    def test_required_fields_only(self):
        """Test Siesa product with only required fields"""
        product = SiesaProduct(
            f_codigo="PROD001",
            f_nombre="Test Product"
        )
        
        assert product.f_codigo == "PROD001"
        assert product.f_nombre == "Test Product"
        assert product.f_codigo_externo is None
        assert product.f_referencia is None
        assert product.f_ean is None
    
    def test_missing_required_field(self):
        """Test that missing required fields raise validation error"""
        with pytest.raises(ValidationError):
            SiesaProduct(f_codigo="PROD001")
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed"""
        product = SiesaProduct(
            f_codigo="PROD001",
            f_nombre="Test Product",
            extra_field="extra_value"
        )
        
        assert product.f_codigo == "PROD001"
        assert hasattr(product, 'extra_field')


class TestCanonicalProduct:
    """Tests for CanonicalProduct schema"""
    
    def test_valid_product(self):
        """Test valid canonical product"""
        product = CanonicalProduct(
            id="PROD001",
            external_id="EXT001",
            name="Test Product",
            sku="SKU001",
            ean="1234567890123",
            stock_quantity=100
        )
        
        assert product.id == "PROD001"
        assert product.external_id == "EXT001"
        assert product.name == "Test Product"
        assert product.sku == "SKU001"
        assert product.ean == "1234567890123"
        assert product.stock_quantity == 100
    
    def test_required_fields_only(self):
        """Test canonical product with only required fields"""
        product = CanonicalProduct(
            id="PROD001",
            external_id="EXT001",
            name="Test Product",
            sku="SKU001"
        )
        
        assert product.id == "PROD001"
        assert product.ean is None
        assert product.stock_quantity == 0
    
    def test_id_length_validation(self):
        """Test that ID length is validated"""
        # Too short
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="",
                external_id="EXT001",
                name="Test Product",
                sku="SKU001"
            )
        
        # Too long
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="A" * 101,
                external_id="EXT001",
                name="Test Product",
                sku="SKU001"
            )
    
    def test_name_length_validation(self):
        """Test that name length is validated"""
        # Too short
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="PROD001",
                external_id="EXT001",
                name="",
                sku="SKU001"
            )
        
        # Too long
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="PROD001",
                external_id="EXT001",
                name="A" * 501,
                sku="SKU001"
            )
    
    def test_ean_format_validation(self):
        """Test that EAN format is validated"""
        # Valid 13-digit EAN
        product = CanonicalProduct(
            id="PROD001",
            external_id="EXT001",
            name="Test Product",
            sku="SKU001",
            ean="1234567890123"
        )
        assert product.ean == "1234567890123"
        
        # Invalid EAN (not 13 digits)
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="PROD001",
                external_id="EXT001",
                name="Test Product",
                sku="SKU001",
                ean="12345"
            )
        
        # Invalid EAN (contains letters)
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="PROD001",
                external_id="EXT001",
                name="Test Product",
                sku="SKU001",
                ean="123456789012A"
            )
    
    def test_stock_quantity_validation(self):
        """Test that stock quantity is validated"""
        # Valid positive quantity
        product = CanonicalProduct(
            id="PROD001",
            external_id="EXT001",
            name="Test Product",
            sku="SKU001",
            stock_quantity=100
        )
        assert product.stock_quantity == 100
        
        # Negative quantity not allowed
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="PROD001",
                external_id="EXT001",
                name="Test Product",
                sku="SKU001",
                stock_quantity=-10
            )
    
    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed"""
        product = CanonicalProduct(
            id="PROD001",
            external_id="EXT001",
            name="Test Product",
            sku="SKU001",
            custom_field="custom_value"
        )
        
        assert product.id == "PROD001"
        assert hasattr(product, 'custom_field')
    
    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error"""
        with pytest.raises(ValidationError):
            CanonicalProduct(
                id="PROD001",
                name="Test Product"
            )
    
    def test_json_serialization(self):
        """Test that product can be serialized to JSON"""
        product = CanonicalProduct(
            id="PROD001",
            external_id="EXT001",
            name="Test Product",
            sku="SKU001",
            ean="1234567890123",
            stock_quantity=100
        )
        
        json_data = product.dict()
        
        assert json_data['id'] == "PROD001"
        assert json_data['external_id'] == "EXT001"
        assert json_data['name'] == "Test Product"
        assert json_data['sku'] == "SKU001"
        assert json_data['ean'] == "1234567890123"
        assert json_data['stock_quantity'] == 100
