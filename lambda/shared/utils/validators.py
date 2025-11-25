"""
Validators Utility
Input validation with domain exceptions
"""
from domain.exceptions import InvalidRadiusException


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
        if not RadiusValidator.MIN_RADIUS <= radius <= RadiusValidator.MAX_RADIUS:
            raise InvalidRadiusException(
                f"Radius must be between {RadiusValidator.MIN_RADIUS} and {RadiusValidator.MAX_RADIUS} km",
                details={"radius": radius, "min": RadiusValidator.MIN_RADIUS, "max": RadiusValidator.MAX_RADIUS}
            )
        return radius


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
        if not city_id or not city_id.strip():
            raise ValueError("City ID cannot be empty")
        
        # City IDs should be numeric strings
        if not city_id.isdigit():
            raise ValueError(f"Invalid city ID format: {city_id}")
        
        return city_id.strip()
