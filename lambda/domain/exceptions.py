"""
Domain Exceptions - Business Rule Violations
Clean Architecture: Domain layer exceptions
"""


class DomainException(Exception):
    """Base exception for all domain-level errors"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CityNotFoundException(DomainException):
    """Raised when a city is not found in the repository"""
    pass


class CoordinatesNotFoundException(DomainException):
    """Raised when a city doesn't have coordinates"""
    pass


class InvalidRadiusException(DomainException):
    """Raised when radius is outside valid range"""
    pass


class InvalidDateTimeException(DomainException):
    """Raised when date/time parameters are invalid"""
    pass


class WeatherDataNotFoundException(DomainException):
    """Raised when weather data is not available"""
    pass


class GeoDataNotFoundException(DomainException):
    """Raised when IBGE geo data is not available"""
    pass


class GeoProviderException(DomainException):
    """Raised when IBGE provider fails unexpectedly"""
    pass
