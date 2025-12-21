"""
Exception Handler Service
Centraliza tratamento de exceções com logging estruturado
"""
import json
from aws_lambda_powertools.event_handler import Response

from domain.exceptions import (
    CityNotFoundException,
    CoordinatesNotFoundException,
    InvalidRadiusException,
    InvalidDateTimeException,
    WeatherDataNotFoundException,
    GeoDataNotFoundException,
    GeoProviderException,
)
from shared.config.logger_config import logger as app_logger

class ExceptionHandlerService:
    """
    Service para centralizar tratamento de exceções da aplicação
    Responsável por converter exceções em respostas HTTP apropriadas
    """
    logger = app_logger

    def __init__(self, logger=app_logger):
        # Permite injeção de logger compartilhado para manter contexto de correlação
        if logger:
            ExceptionHandlerService.logger = logger

    @staticmethod
    def handle_city_not_found(ex: CityNotFoundException) -> Response:
        """Handle 404 - City not found"""
        ExceptionHandlerService.logger.warning("City not found", error=str(ex), details=ex.details)
        return Response(
            status_code=404,
            content_type="application/json",
            body=json.dumps({
                "type": "CityNotFoundException",
                "error": "City not found",
                "message": str(ex),
                "details": ex.details
            })
        )
    
    @staticmethod
    def handle_coordinates_not_found(ex: CoordinatesNotFoundException) -> Response:
        """Handle 404 - Coordinates not found"""
        ExceptionHandlerService.logger.warning("Coordinates not found", error=str(ex), details=ex.details)
        return Response(
            status_code=404,
            content_type="application/json",
            body=json.dumps({
                "type": "CoordinatesNotFoundException",
                "error": "Coordinates not found",
                "message": str(ex),
                "details": ex.details
            })
        )
    
    @staticmethod
    def handle_invalid_radius(ex: InvalidRadiusException) -> Response:
        """Handle 400 - Invalid radius"""
        ExceptionHandlerService.logger.warning("Invalid radius", error=str(ex), details=ex.details)
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({
                "type": "InvalidRadiusException",
                "error": "Invalid radius",
                "message": str(ex),
                "details": ex.details
            })
        )
    
    @staticmethod
    def handle_invalid_datetime(ex: InvalidDateTimeException) -> Response:
        """Handle 400 - Invalid datetime format"""
        ExceptionHandlerService.logger.warning("Invalid datetime", error=str(ex), details=ex.details)
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({
                "type": "InvalidDateTimeException",
                "error": "Invalid datetime",
                "message": str(ex),
                "details": ex.details
            })
        )
    
    @staticmethod
    def handle_weather_data_not_found(ex: WeatherDataNotFoundException) -> Response:
        """Handle 404 - Weather data not available"""
        ExceptionHandlerService.logger.warning("Weather data not found", error=str(ex), details=ex.details)
        return Response(
            status_code=404,
            content_type="application/json",
            body=json.dumps({
                "error": "Weather data not found",
                "message": str(ex),
                "details": ex.details
            })
        )

    @staticmethod
    def handle_geo_data_not_found(ex: GeoDataNotFoundException) -> Response:
        """Handle 404 - Geo data not available"""
        ExceptionHandlerService.logger.warning("Geo data not found", error=str(ex), details=ex.details)
        return Response(
            status_code=404,
            content_type="application/json",
            body=json.dumps({
                "type": "GeoDataNotFoundException",
                "error": "Geo data not found",
                "message": str(ex),
                "details": ex.details
            })
        )

    @staticmethod
    def handle_geo_provider_error(ex: GeoProviderException) -> Response:
        """Handle 502 - Upstream IBGE error"""
        ExceptionHandlerService.logger.error("IBGE provider error", error=str(ex), details=ex.details, exc_info=True)
        return Response(
            status_code=502,
            content_type="application/json",
            body=json.dumps({
                "type": "GeoProviderException",
                "error": "IBGE provider error",
                "message": str(ex),
                "details": ex.details
            })
        )
    
    @staticmethod
    def handle_value_error(ex: ValueError) -> Response:
        """Handle 400 - Validation errors (ValueError)"""
        ExceptionHandlerService.logger.warning("Validation error", error=str(ex))
        return Response(
            status_code=400,
            content_type="application/json",
            body=json.dumps({
                "type": "ValidationError",
                "error": "Validation error",
                "message": str(ex)
            })
        )
    
    @staticmethod
    def handle_unexpected_error(ex: Exception) -> Response:
        """Handle 500 - Unexpected errors"""
        ExceptionHandlerService.logger.error("Unexpected error", error=str(ex), exc_info=True)
        return Response(
            status_code=500,
            content_type="application/json",
            body=json.dumps({
                "error": "Internal server error",
                "message": "An unexpected error occurred"
            })
        )
