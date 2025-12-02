"""
Testes para BaseAlertService e serviços derivados
"""
import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.services.base_alert_service import BaseAlertService
from domain.services.wind_alert_service import WindAlertService, WindAlertInput
from domain.services.visibility_alert_service import VisibilityAlertService, VisibilityAlertInput
from domain.services.temperature_alert_service import TemperatureAlertService, TemperatureAlertInput
from domain.alerts.primitives import AlertSeverity


class TestBaseAlertService:
    """Testes para classe base de alertas"""
    
    def test_create_alert(self):
        """Testa criação de alerta via factory method"""
        timestamp = datetime.now(tz=ZoneInfo("America/Sao_Paulo"))
        
        alert = BaseAlertService.create_alert(
            code="TEST_ALERT",
            severity=AlertSeverity.WARNING,
            description="Test alert description",
            timestamp=timestamp,
            details={"test_value": 42.5}
        )
        
        assert alert.code == "TEST_ALERT"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.description == "Test alert description"
        assert alert.timestamp == timestamp
        assert alert.details["test_value"] == 42.5
    
    def test_round_details(self):
        """Testa arredondamento de valores em details"""
        details = {
            "float_value": 42.567,
            "int_value": 10,
            "string_value": "test"
        }
        
        rounded = BaseAlertService.round_details(details, precision=1)
        
        assert rounded["float_value"] == 42.6
        assert rounded["int_value"] == 10
        assert rounded["string_value"] == "test"


class TestWindAlertService:
    """Testes para serviço de alertas de vento"""
    
    def test_strong_wind_alert(self):
        """Testa geração de alerta de vento forte"""
        data = WindAlertInput(
            wind_speed=55.0,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = WindAlertService.generate_alerts(data)
        
        assert len(alerts) == 1
        assert alerts[0].code == "STRONG_WIND"
        assert alerts[0].severity == AlertSeverity.ALERT
        assert "ALERTA" in alerts[0].description
    
    def test_moderate_wind_alert(self):
        """Testa geração de alerta de vento moderado"""
        data = WindAlertInput(
            wind_speed=35.0,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = WindAlertService.generate_alerts(data)
        
        assert len(alerts) == 1
        assert alerts[0].code == "MODERATE_WIND"
        assert alerts[0].severity == AlertSeverity.INFO
    
    def test_no_wind_alert(self):
        """Testa que vento fraco não gera alerta"""
        data = WindAlertInput(
            wind_speed=20.0,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = WindAlertService.generate_alerts(data)
        
        assert len(alerts) == 0


class TestVisibilityAlertService:
    """Testes para serviço de alertas de visibilidade"""
    
    def test_very_low_visibility_alert(self):
        """Testa alerta de visibilidade muito reduzida"""
        data = VisibilityAlertInput(
            visibility_m=500.0,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = VisibilityAlertService.generate_alerts(data)
        
        assert len(alerts) == 1
        assert alerts[0].code == "LOW_VISIBILITY"
        assert alerts[0].severity == AlertSeverity.ALERT
    
    def test_low_visibility_warning(self):
        """Testa warning de visibilidade reduzida"""
        data = VisibilityAlertInput(
            visibility_m=2000.0,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = VisibilityAlertService.generate_alerts(data)
        
        assert len(alerts) == 1
        assert alerts[0].code == "LOW_VISIBILITY"
        assert alerts[0].severity == AlertSeverity.WARNING


class TestTemperatureAlertService:
    """Testes para serviço de alertas de temperatura"""
    
    def test_very_cold_alert(self):
        """Testa alerta de frio intenso"""
        data = TemperatureAlertInput(
            temperature_c=5.0,
            weather_code=800,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = TemperatureAlertService.generate_alerts(data)
        
        assert len(alerts) == 1
        assert alerts[0].code == "VERY_COLD"
        assert alerts[0].severity == AlertSeverity.DANGER
    
    def test_cold_alert(self):
        """Testa alerta de frio"""
        data = TemperatureAlertInput(
            temperature_c=10.0,
            weather_code=800,
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = TemperatureAlertService.generate_alerts(data)
        
        assert len(alerts) == 1
        assert alerts[0].code == "COLD"
        assert alerts[0].severity == AlertSeverity.ALERT
    
    def test_snow_alert(self):
        """Testa alerta de neve"""
        data = TemperatureAlertInput(
            temperature_c=2.0,
            weather_code=600,  # Snow code
            forecast_time=datetime.now(tz=ZoneInfo("UTC"))
        )
        
        alerts = TemperatureAlertService.generate_alerts(data)
        
        # Deve gerar dois alertas: neve + frio intenso
        assert len(alerts) == 2
        codes = {alert.code for alert in alerts}
        assert "SNOW" in codes
        assert "VERY_COLD" in codes
