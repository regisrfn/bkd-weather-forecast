"""
Testes Unitários - DateTimeParser
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import pytest
from datetime import datetime, date, time
from zoneinfo import ZoneInfo

from shared.utils.datetime_parser import DateTimeParser
from domain.exceptions import InvalidDateTimeException


class TestDateTimeParser:
    """Testes para DateTimeParser"""
    
    def test_from_query_params_both_date_and_time(self):
        """Testa parsing com data e hora"""
        result = DateTimeParser.from_query_params("2025-11-27", "15:30")
        
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 27
        assert result.hour == 15
        assert result.minute == 30
        assert result.tzinfo == ZoneInfo("America/Sao_Paulo")
    
    def test_from_query_params_only_date(self):
        """Testa parsing com apenas data (usa meio-dia)"""
        result = DateTimeParser.from_query_params("2025-11-27", None)
        
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 27
        assert result.hour == 12  # Default: meio-dia
        assert result.minute == 0
    
    def test_from_query_params_only_time(self):
        """Testa parsing com apenas hora (usa hoje)"""
        result = DateTimeParser.from_query_params(None, "15:30")
        
        assert isinstance(result, datetime)
        assert result.date() == date.today()
        assert result.hour == 15
        assert result.minute == 30
    
    def test_from_query_params_both_none(self):
        """Testa parsing com ambos None (retorna None)"""
        result = DateTimeParser.from_query_params(None, None)
        
        assert result is None
    
    def test_from_query_params_custom_timezone(self):
        """Testa parsing com timezone customizado"""
        result = DateTimeParser.from_query_params(
            "2025-11-27",
            "15:30",
            timezone="UTC"
        )
        
        assert isinstance(result, datetime)
        assert result.tzinfo == ZoneInfo("UTC")
    
    def test_from_query_params_invalid_date_format(self):
        """Testa exceção com formato de data inválido"""
        with pytest.raises(InvalidDateTimeException) as exc_info:
            DateTimeParser.from_query_params("27/11/2025", "15:30")
        
        assert "Invalid date/time format" in str(exc_info.value)
        assert exc_info.value.details["date"] == "27/11/2025"
    
    def test_from_query_params_invalid_time_format(self):
        """Testa exceção com formato de hora inválido"""
        with pytest.raises(InvalidDateTimeException) as exc_info:
            DateTimeParser.from_query_params("2025-11-27", "25:70")
        
        assert "Invalid date/time format" in str(exc_info.value)
    
    def test_from_query_params_invalid_date_value(self):
        """Testa exceção com valor de data inválido"""
        with pytest.raises(InvalidDateTimeException):
            DateTimeParser.from_query_params("2025-13-40", "15:30")
    
    def test_from_query_params_empty_strings(self):
        """Testa comportamento com strings vazias"""
        # String vazia para date é tratada como None
        result = DateTimeParser.from_query_params("", "15:30")
        # Deve usar data de hoje
        assert result is not None
        assert result.hour == 15
        assert result.minute == 30
    
    def test_from_query_params_midnight(self):
        """Testa parsing de meia-noite"""
        result = DateTimeParser.from_query_params("2025-11-27", "00:00")
        
        assert result.hour == 0
        assert result.minute == 0
    
    def test_from_query_params_end_of_day(self):
        """Testa parsing de final do dia"""
        result = DateTimeParser.from_query_params("2025-11-27", "23:59")
        
        assert result.hour == 23
        assert result.minute == 59
    
    def test_from_query_params_leap_year(self):
        """Testa parsing de data em ano bissexto"""
        result = DateTimeParser.from_query_params("2024-02-29", "12:00")
        
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29
    
    def test_from_query_params_non_leap_year_invalid(self):
        """Testa exceção com 29 de fevereiro em ano não bissexto"""
        with pytest.raises(InvalidDateTimeException):
            DateTimeParser.from_query_params("2025-02-29", "12:00")
    
    def test_from_query_params_different_timezones(self):
        """Testa parsing em diferentes timezones"""
        # São Paulo
        sp_result = DateTimeParser.from_query_params(
            "2025-11-27", "15:30", "America/Sao_Paulo"
        )
        
        # UTC
        utc_result = DateTimeParser.from_query_params(
            "2025-11-27", "15:30", "UTC"
        )
        
        # Tokyo
        tokyo_result = DateTimeParser.from_query_params(
            "2025-11-27", "15:30", "Asia/Tokyo"
        )
        
        assert sp_result.tzinfo == ZoneInfo("America/Sao_Paulo")
        assert utc_result.tzinfo == ZoneInfo("UTC")
        assert tokyo_result.tzinfo == ZoneInfo("Asia/Tokyo")
    
    def test_from_query_params_whitespace_handling(self):
        """Testa que não aceita espaços extras"""
        with pytest.raises(InvalidDateTimeException):
            DateTimeParser.from_query_params(" 2025-11-27 ", "15:30")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
