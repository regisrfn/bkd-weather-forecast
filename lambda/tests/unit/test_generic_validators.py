"""
Testes para GenericValidator
"""
import pytest

from shared.utils.validators import GenericValidator, RadiusValidator, CityIdValidator
from domain.exceptions import InvalidRadiusException


class TestGenericValidator:
    """Testes para validador genérico"""
    
    def test_validate_range_valid(self):
        """Testa validação de range com valor válido"""
        result = GenericValidator.validate_range(
            value=50.0,
            min_val=0.0,
            max_val=100.0,
            param_name="test_param"
        )
        assert result == 50.0
    
    def test_validate_range_below_min(self):
        """Testa validação de range com valor abaixo do mínimo"""
        with pytest.raises(ValueError, match="test_param must be between"):
            GenericValidator.validate_range(
                value=-10.0,
                min_val=0.0,
                max_val=100.0,
                param_name="test_param"
            )
    
    def test_validate_range_above_max(self):
        """Testa validação de range com valor acima do máximo"""
        with pytest.raises(ValueError, match="test_param must be between"):
            GenericValidator.validate_range(
                value=150.0,
                min_val=0.0,
                max_val=100.0,
                param_name="test_param"
            )
    
    def test_validate_range_custom_exception(self):
        """Testa validação com exceção customizada"""
        with pytest.raises(InvalidRadiusException):
            GenericValidator.validate_range(
                value=600.0,
                min_val=1.0,
                max_val=500.0,
                param_name="radius",
                exception_class=InvalidRadiusException
            )
    
    def test_validate_not_empty_valid(self):
        """Testa validação de string não vazia"""
        result = GenericValidator.validate_not_empty(
            value="  test  ",
            param_name="test_param"
        )
        assert result == "test"
    
    def test_validate_not_empty_empty_string(self):
        """Testa validação de string vazia"""
        with pytest.raises(ValueError, match="test_param cannot be empty"):
            GenericValidator.validate_not_empty(
                value="",
                param_name="test_param"
            )
    
    def test_validate_not_empty_whitespace(self):
        """Testa validação de string com apenas espaços"""
        with pytest.raises(ValueError, match="test_param cannot be empty"):
            GenericValidator.validate_not_empty(
                value="   ",
                param_name="test_param"
            )
    
    def test_validate_numeric_string_valid(self):
        """Testa validação de string numérica"""
        result = GenericValidator.validate_numeric_string(
            value="12345",
            param_name="city_id"
        )
        assert result == "12345"
    
    def test_validate_numeric_string_invalid(self):
        """Testa validação de string não numérica"""
        with pytest.raises(ValueError, match="Invalid city_id format"):
            GenericValidator.validate_numeric_string(
                value="abc123",
                param_name="city_id"
            )


class TestRadiusValidator:
    """Testes para validador de raio"""
    
    def test_valid_radius(self):
        """Testa validação de raio válido"""
        assert RadiusValidator.validate(50.0) == 50.0
    
    def test_radius_at_min_boundary(self):
        """Testa raio no limite mínimo"""
        assert RadiusValidator.validate(1.0) == 1.0
    
    def test_radius_at_max_boundary(self):
        """Testa raio no limite máximo"""
        assert RadiusValidator.validate(500.0) == 500.0
    
    def test_radius_below_min(self):
        """Testa raio abaixo do mínimo"""
        with pytest.raises(InvalidRadiusException):
            RadiusValidator.validate(0.5)
    
    def test_radius_above_max(self):
        """Testa raio acima do máximo"""
        with pytest.raises(InvalidRadiusException):
            RadiusValidator.validate(600.0)


class TestCityIdValidator:
    """Testes para validador de ID de cidade"""
    
    def test_valid_city_id(self):
        """Testa validação de ID válido"""
        assert CityIdValidator.validate("3531803") == "3531803"
    
    def test_city_id_with_whitespace(self):
        """Testa ID com espaços (deve fazer trim)"""
        assert CityIdValidator.validate("  3531803  ") == "3531803"
    
    def test_empty_city_id(self):
        """Testa ID vazio"""
        with pytest.raises(ValueError, match="city_id cannot be empty"):
            CityIdValidator.validate("")
    
    def test_non_numeric_city_id(self):
        """Testa ID não numérico"""
        with pytest.raises(ValueError, match="Invalid city_id format"):
            CityIdValidator.validate("abc123")
    
    def test_city_id_with_special_chars(self):
        """Testa ID com caracteres especiais"""
        with pytest.raises(ValueError, match="Invalid city_id format"):
            CityIdValidator.validate("3531-803")
