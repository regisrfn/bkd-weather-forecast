"""
Unit tests for settings.py
Tests configuration loading and environment variables
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from unittest.mock import patch


class TestSettings:
    """Tests for Settings configuration"""
    
    @patch.dict(os.environ, {
        'AWS_REGION': 'us-east-1',
        'CACHE_TABLE_NAME': 'test-weather-cache',
        'CACHE_TTL_SECONDS': '1800',
        'CACHE_ENABLED': 'true',
        'CORS_ORIGIN': 'https://test.example.com'
    })
    def test_settings_from_environment(self):
        """Test settings loaded from environment variables"""
        # Need to reload module to pick up new env vars
        import importlib
        from shared.config import settings
        importlib.reload(settings)
        
        assert settings.AWS_REGION == 'us-east-1'
        assert settings.CACHE_TABLE_NAME == 'test-weather-cache'
        assert settings.CACHE_TTL_SECONDS == 1800
        assert settings.CACHE_ENABLED == True
        assert settings.CORS_ORIGIN == 'https://test.example.com'
    
    def test_settings_constants(self):
        """Test that constants are defined"""
        from shared.config import settings
        
        assert hasattr(settings, 'OPENMETEO_BASE_URL')
        assert settings.OPENMETEO_BASE_URL == 'https://api.open-meteo.com/v1'
        
        assert hasattr(settings, 'CENTER_CITY_ID')
        assert settings.CENTER_CITY_ID == '3543204'
        
        assert hasattr(settings, 'MIN_RADIUS')
        assert settings.MIN_RADIUS == 10
        
        assert hasattr(settings, 'MAX_RADIUS')
        assert settings.MAX_RADIUS == 150
        
        assert hasattr(settings, 'DEFAULT_RADIUS')
        assert settings.DEFAULT_RADIUS == 50
    
    @patch.dict(os.environ, {'CACHE_ENABLED': 'false'}, clear=False)
    def test_cache_disabled(self):
        """Test cache can be disabled via environment"""
        import importlib
        from shared.config import settings
        importlib.reload(settings)
        
        assert settings.CACHE_ENABLED == False
    
    @patch.dict(os.environ, {'CACHE_ENABLED': '0'}, clear=False)
    def test_cache_disabled_with_zero(self):
        """Test cache disabled with 0 value"""
        import importlib
        from shared.config import settings
        importlib.reload(settings)
        
        assert settings.CACHE_ENABLED == False
    
    @patch.dict(os.environ, {'CACHE_ENABLED': 'yes'}, clear=False)
    def test_cache_enabled_with_yes(self):
        """Test cache enabled with 'yes' value"""
        import importlib
        from shared.config import settings
        importlib.reload(settings)
        
        assert settings.CACHE_ENABLED == True
    
    @patch.dict(os.environ, {}, clear=True)
    def test_settings_default_values(self):
        """Test settings with default values when env vars not set"""
        import importlib
        from shared.config import settings
        importlib.reload(settings)
        
        # Should have default values
        assert settings.AWS_REGION == 'sa-east-1'
        assert settings.CACHE_TABLE_NAME == 'weather-forecast-cache-prod'
        assert settings.CACHE_TTL_SECONDS == 10800
        assert settings.CACHE_ENABLED == True
        assert settings.CORS_ORIGIN == '*'
