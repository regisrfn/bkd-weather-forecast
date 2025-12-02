"""
Validators Utility
Input validation with domain exceptions
"""
from typing import Any, Type
from domain.exceptions import InvalidRadiusException


class GenericValidator:
    """Validador genérico para reduzir duplicação de código"""
    
    @staticmethod
    def validate_range(
        value: float,
        min_val: float,
        max_val: float,
        param_name: str,
        exception_class: Type[Exception] = ValueError
    ) -> float:
        """
        Valida se valor numérico está dentro do range
        
        Args:
            value: Valor a validar
            min_val: Valor mínimo permitido
            max_val: Valor máximo permitido
            param_name: Nome do parâmetro (para mensagem de erro)
            exception_class: Classe de exceção a lançar
        
        Returns:
            Valor validado
        
        Raises:
            exception_class: Se valor fora do range
        """
        if not (min_val <= value <= max_val):
            # Tenta criar exceção com details se suportado
            try:
                raise exception_class(
                    f"{param_name} must be between {min_val} and {max_val}",
                    details={
                        param_name: value,
                        "min": min_val,
                        "max": max_val
                    }
                )
            except TypeError:
                # Fallback: exceção sem details
                raise exception_class(
                    f"{param_name} must be between {min_val} and {max_val}"
                )
        return value
    
    @staticmethod
    def validate_not_empty(
        value: str,
        param_name: str,
        exception_class: Type[Exception] = ValueError
    ) -> str:
        """
        Valida se string não está vazia
        
        Args:
            value: String a validar
            param_name: Nome do parâmetro (para mensagem de erro)
            exception_class: Classe de exceção a lançar
        
        Returns:
            String validada e trimmed
        
        Raises:
            exception_class: Se string vazia
        """
        if not value or not value.strip():
            raise exception_class(f"{param_name} cannot be empty")
        return value.strip()
    
    @staticmethod
    def validate_numeric_string(
        value: str,
        param_name: str,
        exception_class: Type[Exception] = ValueError
    ) -> str:
        """
        Valida se string é numérica
        
        Args:
            value: String a validar
            param_name: Nome do parâmetro
            exception_class: Classe de exceção a lançar
        
        Returns:
            String validada
        
        Raises:
            exception_class: Se não for numérica
        """
        trimmed = GenericValidator.validate_not_empty(value, param_name, exception_class)
        if not trimmed.isdigit():
            raise exception_class(f"Invalid {param_name} format: {value}")
        return trimmed


class RadiusValidator:
    """Validate radius parameter"""
    
    MIN_RADIUS = 1.0  # km
    MAX_RADIUS = 500.0  # km
    
    @staticmethod
    def validate(radius: float) -> float:
        """
        Validate radius is within acceptable range
        
        Args:
            radius: Radius in kilometers
        
        Returns:
            The validated radius
        
        Raises:
            InvalidRadiusException: If radius is out of range
        """
        return GenericValidator.validate_range(
            value=radius,
            min_val=RadiusValidator.MIN_RADIUS,
            max_val=RadiusValidator.MAX_RADIUS,
            param_name="radius",
            exception_class=InvalidRadiusException
        )


class CityIdValidator:
    """Validate city ID parameter"""
    
    @staticmethod
    def validate(city_id: str) -> str:
        """
        Validate city ID format (basic validation)
        
        Args:
            city_id: City ID string
        
        Returns:
            The validated city ID
        
        Raises:
            ValueError: If city_id is empty or invalid format
        """
        return GenericValidator.validate_numeric_string(
            value=city_id,
            param_name="city_id",
            exception_class=ValueError
        )
