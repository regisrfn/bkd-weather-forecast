"""
DateTime Parser Utility
Shared utility for parsing datetime from query parameters
"""
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from typing import Optional

from domain.exceptions import InvalidDateTimeException


class DateTimeParser:
    """Parse datetime from API query parameters"""
    
    DEFAULT_TIMEZONE = "America/Sao_Paulo"
    
    @staticmethod
    def from_query_params(
        date_str: Optional[str] = None,
        time_str: Optional[str] = None,
        timezone: str = DEFAULT_TIMEZONE
    ) -> Optional[datetime]:
        """
        Parse datetime from query string parameters
        
        Args:
            date_str: Date in YYYY-MM-DD format (optional)
            time_str: Time in HH:MM format (optional)
            timezone: Timezone name (default: America/Sao_Paulo)
        
        Returns:
            Parsed datetime with timezone or None if both params are None
        
        Raises:
            InvalidDateTimeException: If format is invalid
        
        Examples:
            >>> DateTimeParser.from_query_params("2025-11-25", "14:30")
            datetime(2025, 11, 25, 14, 30, tzinfo=ZoneInfo('America/Sao_Paulo'))
            
            >>> DateTimeParser.from_query_params("2025-11-25")  # Uses 12:00
            datetime(2025, 11, 25, 12, 0, tzinfo=ZoneInfo('America/Sao_Paulo'))
            
            >>> DateTimeParser.from_query_params(time_str="14:30")  # Uses today
            datetime(2025, 11, 25, 14, 30, tzinfo=ZoneInfo('America/Sao_Paulo'))
        """
        # If both are None, return None (use current time)
        if date_str is None and time_str is None:
            return None
        
        try:
            tz = ZoneInfo(timezone)
            
            # Parse date
            if date_str:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                # Use today if only time provided
                parsed_date = date.today()
            
            # Parse time
            if time_str:
                parsed_time = datetime.strptime(time_str, "%H:%M").time()
            else:
                # Use noon if only date provided
                parsed_time = time(12, 0)
            
            # Combine date and time with timezone
            return datetime.combine(parsed_date, parsed_time, tzinfo=tz)
        
        except ValueError as e:
            raise InvalidDateTimeException(
                f"Invalid date/time format. Use date=YYYY-MM-DD and time=HH:MM. Error: {str(e)}",
                details={"date": date_str, "time": time_str}
            )
