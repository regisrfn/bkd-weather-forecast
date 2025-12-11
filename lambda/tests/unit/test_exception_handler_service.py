"""
Testes para ExceptionHandlerService
Garante cobertura completa do tratamento de exceções
"""
import json
import pytest
from infrastructure.adapters.input.exception_handler_service import ExceptionHandlerService
from domain.exceptions import (
    CityNotFoundException,
    CoordinatesNotFoundException,
    InvalidRadiusException,
    InvalidDateTimeException,
    WeatherDataNotFoundException,
    GeoDataNotFoundException,
    GeoProviderException
)


class TestExceptionHandlerService:
    """Testes para o serviço de tratamento de exceções"""
    
    def test_handle_city_not_found(self):
        """REGRA: CityNotFoundException deve retornar 404 com detalhes"""
        ex = CityNotFoundException(
            message="City with ID 999999 not found",
            details={"attempted_id": "999999"}
        )
        response = ExceptionHandlerService.handle_city_not_found(ex)
        
        assert response.status_code == 404
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["type"] == "CityNotFoundException"
        assert body["error"] == "City not found"
        assert "999999" in body["message"]
        assert body["details"] == {"attempted_id": "999999"}
    
    def test_handle_coordinates_not_found(self):
        """REGRA: CoordinatesNotFoundException deve retornar 404"""
        ex = CoordinatesNotFoundException(
            message="Coordinates not found for city Ribeirão Preto (3451682)",
            details={"city_id": "3451682", "city_name": "Ribeirão Preto", "reason": "coordinates_missing"}
        )
        response = ExceptionHandlerService.handle_coordinates_not_found(ex)
        
        assert response.status_code == 404
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["type"] == "CoordinatesNotFoundException"
        assert body["error"] == "Coordinates not found"
        assert "Ribeirão Preto" in body["message"]
        assert body["details"]["reason"] == "coordinates_missing"
    
    def test_handle_invalid_radius(self):
        """REGRA: InvalidRadiusException deve retornar 400"""
        ex = InvalidRadiusException(
            message="Invalid radius -5: must be between 1 and 500",
            details={"provided": -5, "min": 1, "max": 500}
        )
        response = ExceptionHandlerService.handle_invalid_radius(ex)
        
        assert response.status_code == 400
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["type"] == "InvalidRadiusException"
        assert body["error"] == "Invalid radius"
        assert "-5" in body["message"]
        assert body["details"]["provided"] == -5
    
    def test_handle_invalid_datetime(self):
        """REGRA: InvalidDateTimeException deve retornar 400"""
        ex = InvalidDateTimeException(
            message="Invalid date format: invalid-date",
            details={"format": "YYYY-MM-DD", "provided": "invalid-date"}
        )
        response = ExceptionHandlerService.handle_invalid_datetime(ex)
        
        assert response.status_code == 400
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["type"] == "InvalidDateTimeException"
        assert body["error"] == "Invalid datetime"
        assert "invalid-date" in body["message"]
    
    def test_handle_weather_data_not_found(self):
        """REGRA: WeatherDataNotFoundException deve retornar 404"""
        ex = WeatherDataNotFoundException(
            message="Weather data not found for city 3451682",
            details={"city_id": "3451682", "provider": "OpenMeteo", "status": "unavailable"}
        )
        response = ExceptionHandlerService.handle_weather_data_not_found(ex)
        
        assert response.status_code == 404
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["error"] == "Weather data not found"
        assert "3451682" in body["message"]
        assert body["details"]["provider"] == "OpenMeteo"
    
    def test_handle_value_error(self):
        """REGRA: ValueError deve retornar 400 com mensagem de validação"""
        ex = ValueError("Invalid parameter format")
        response = ExceptionHandlerService.handle_value_error(ex)
        
        assert response.status_code == 400
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["type"] == "ValidationError"
        assert body["error"] == "Validation error"
        assert body["message"] == "Invalid parameter format"
    
    def test_handle_unexpected_error(self):
        """REGRA: Exceções inesperadas devem retornar 500 sem expor detalhes"""
        ex = RuntimeError("Internal system failure")
        response = ExceptionHandlerService.handle_unexpected_error(ex)
        
        assert response.status_code == 500
        assert response.content_type == "application/json"
        
        body = json.loads(response.body)
        assert body["error"] == "Internal server error"
        assert body["message"] == "An unexpected error occurred"
        # Não deve expor detalhes internos ao cliente
        assert "RuntimeError" not in body["message"]
        assert "Internal system failure" not in body["message"]
    
    def test_handle_city_not_found_with_empty_details(self):
        """EDGE CASE: CityNotFoundException sem details"""
        ex = CityNotFoundException(message="City with ID 000000 not found", details={})
        response = ExceptionHandlerService.handle_city_not_found(ex)
        
        assert response.status_code == 404
        body = json.loads(response.body)
        assert body["details"] == {}
    
    def test_handle_invalid_radius_boundary_values(self):
        """EDGE CASE: InvalidRadiusException com valores nos limites"""
        ex = InvalidRadiusException(
            message="Invalid radius 0: below minimum",
            details={"radius": 0, "reason": "below_minimum"}
        )
        response = ExceptionHandlerService.handle_invalid_radius(ex)
        
        assert response.status_code == 400
        body = json.loads(response.body)
        assert body["details"]["reason"] == "below_minimum"
    
    def test_handle_value_error_with_special_characters(self):
        """EDGE CASE: ValueError com caracteres especiais na mensagem"""
        ex = ValueError("Parameter 'cidade' inválido: caracter não permitido '@#$'")
        response = ExceptionHandlerService.handle_value_error(ex)
        
        assert response.status_code == 400
        body = json.loads(response.body)
        # JSON deve estar bem formatado mesmo com caracteres especiais
        assert "cidade" in body["message"]
        assert "@#$" in body["message"]
    
    def test_response_content_type_is_always_json(self):
        """REGRA: Todas as respostas devem ter Content-Type application/json"""
        exceptions = [
            (CityNotFoundException(message="City 123 not found", details={}), 
             ExceptionHandlerService.handle_city_not_found),
            (InvalidRadiusException(message="Invalid radius", details={}),
             ExceptionHandlerService.handle_invalid_radius),
            (ValueError("test"),
             ExceptionHandlerService.handle_value_error),
            (Exception("test"),
             ExceptionHandlerService.handle_unexpected_error)
        ]
        
        for exception, handler in exceptions:
            response = handler(exception)
            assert response.content_type == "application/json", \
                f"Handler {handler.__name__} não retornou JSON"
    
    def test_response_body_is_valid_json(self):
        """REGRA: Todas as respostas devem ter body JSON válido"""
        ex = CityNotFoundException(message="City 123 not found", details={"test": "value"})
        response = ExceptionHandlerService.handle_city_not_found(ex)
        
        # Não deve lançar exceção ao parsear
        body = json.loads(response.body)
        assert isinstance(body, dict)
        assert "error" in body or "type" in body
    
    def test_handle_weather_data_not_found_missing_provider(self):
        """EDGE CASE: WeatherDataNotFoundException sem provider nos details"""
        ex = WeatherDataNotFoundException(
            message="Weather data not found for city 3451682",
            details={"city_id": "3451682", "reason": "timeout"}
        )
        response = ExceptionHandlerService.handle_weather_data_not_found(ex)
        
        assert response.status_code == 404
        body = json.loads(response.body)
        assert body["details"]["reason"] == "timeout"
        assert "provider" not in body["details"]

    def test_handle_geo_data_not_found(self):
        """REGRA: GeoDataNotFoundException deve retornar 404"""
        ex = GeoDataNotFoundException(
            message="Geo data not found",
            details={"city_id": "1234567"}
        )
        response = ExceptionHandlerService.handle_geo_data_not_found(ex)

        assert response.status_code == 404
        assert response.content_type == "application/json"

        body = json.loads(response.body)
        assert body["type"] == "GeoDataNotFoundException"
        assert body["error"] == "Geo data not found"
        assert body["details"]["city_id"] == "1234567"

    def test_handle_geo_provider_error(self):
        """REGRA: GeoProviderException deve retornar 502"""
        ex = GeoProviderException(
            message="IBGE service unavailable",
            details={"status": 503, "provider": "IBGE"}
        )
        response = ExceptionHandlerService.handle_geo_provider_error(ex)

        assert response.status_code == 502
        assert response.content_type == "application/json"

        body = json.loads(response.body)
        assert body["type"] == "GeoProviderException"
        assert body["error"] == "IBGE provider error"
        assert body["details"]["status"] == 503
