"""
Trading hours and datetime helper functions for financial markets.

This module contains pure functions for handling trading hours, weekend detection,
and datetime adjustments for forex and other financial markets.
"""

from datetime import datetime, timedelta
from typing import Optional

try:
    # Try relative import (when used as package)
    from .trading_hours_config import (
        get_sunday_open_hour,
        get_daily_open_hour,
        get_friday_close_hour,
        get_daily_close_hour
    )
except ImportError:
    # Fall back to absolute import (when used directly)
    from trading_hours_config import (
        get_sunday_open_hour,
        get_daily_open_hour,
        get_friday_close_hour,
        get_daily_close_hour
    )


def format_trading_session_info(date: datetime, asset_type: str = 'forex') -> str:
    """Get formatted string with trading session information"""
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekday = weekday_names[date.weekday()]
    
    status = "TRADING" if is_trading_hour(date, asset_type) and not is_weekend(date, asset_type) else "CLOSED"
    
    if is_weekend(date, asset_type):
        next_open = get_next_valid_time(date, asset_type)
        return f"{weekday} {date.strftime('%H:%M')} UTC - WEEKEND (next open: {next_open.strftime('%a %H:%M')})"
    elif not is_trading_hour(date, asset_type):
        next_open = get_next_valid_time(date, asset_type)
        return f"{weekday} {date.strftime('%H:%M')} UTC - {status} (next open: {next_open.strftime('%a %H:%M')})"
    else:
        return f"{weekday} {date.strftime('%H:%M')} UTC - {status}"


def is_weekend(date: datetime, asset_type: str = 'forex') -> bool:
    """Check if the date is a weekend (Saturday or Sunday before market open)"""
    weekday = date.weekday()  # Monday = 0, Sunday = 6
    hour = date.hour
    
    # Get Sunday opening hour from config
    sunday_open_hour = get_sunday_open_hour(asset_type)
    
    if weekday == 5:  # Saturday
        return True
    if weekday == 6 and hour < sunday_open_hour:  # Sunday before market opens
        return True
    
    return False


def is_trading_hour(date: datetime, asset_type: str = 'forex') -> bool:
    """
    Check if the datetime is within trading hours
    Forex/USA Indices: Sunday 22:00 UTC to Friday 21:00 UTC
    EU Indices: Sunday 23:00 UTC to Friday 21:00 UTC (daily reopening at 22:00 UTC)
    """
    weekday = date.weekday()  # Monday = 0, Sunday = 6
    hour = date.hour
    
    # Get trading hours from config
    sunday_open_hour = get_sunday_open_hour(asset_type)
    daily_open_hour = get_daily_open_hour(asset_type)
    friday_close_hour = get_friday_close_hour(asset_type)
    daily_close_hour = get_daily_close_hour(asset_type)
    
    # Market closes at configured hour on Friday
    if weekday == 4 and hour >= friday_close_hour:  # Friday >= close time
        return False
    
    # Saturday is always closed
    if weekday == 5:  # Saturday
        return False
    
    # Sunday before market opens (use Sunday-specific opening hour)
    if weekday == 6 and hour < sunday_open_hour:
        return False
    
    # Daily closure (Mon-Fri), but not Sunday opening
    if weekday != 6 and daily_close_hour <= hour < daily_open_hour:
        return False
    
    return True


def get_next_valid_time(current_time: datetime, asset_type: str = 'forex') -> datetime:
    """
    Get the next valid trading time based on current time
    Skips weekends and non-trading hours
    """
    new_time = current_time.replace()
    
    # Get trading hours from config
    sunday_open_hour = get_sunday_open_hour(asset_type)
    daily_open_hour = get_daily_open_hour(asset_type)
    friday_close_hour = get_friday_close_hour(asset_type)
    
    while not is_trading_hour(new_time, asset_type) or is_weekend(new_time, asset_type):
        weekday = new_time.weekday()
        hour = new_time.hour
        
        if weekday == 4 and hour >= friday_close_hour:  # Friday after market closing
            # Move to Sunday opening (use Sunday-specific hour)
            days_to_add = 2
            new_time = new_time.replace(hour=sunday_open_hour, minute=0, second=0, microsecond=0)
            new_time += timedelta(days=days_to_add)
        elif weekday == 5:  # Saturday
            # Move to Sunday opening (use Sunday-specific hour)
            days_to_add = 1
            new_time = new_time.replace(hour=sunday_open_hour, minute=0, second=0, microsecond=0)
            new_time += timedelta(days=days_to_add)
        elif weekday == 6 and hour < sunday_open_hour:  # Sunday before market opens
            # Set to Sunday opening hour
            new_time = new_time.replace(hour=sunday_open_hour, minute=0, second=0, microsecond=0)
        elif not is_trading_hour(new_time, asset_type):  # Non-trading hours on weekdays
            # For weekdays (Mon-Fri), daily closure is configured, so move to next day opening
            # We're in the closure window, so go to next day
            new_time = new_time.replace(hour=daily_open_hour, minute=0, second=0, microsecond=0)
            new_time += timedelta(days=1)
        else:
            break  # Valid trading time found
    
    return new_time


def adjust_end_time(start_time: datetime, duration_days: int, asset_type: str = 'forex') -> datetime:
    """
    Adjust end time to ensure it doesn't fall on non-trading periods
    """
    end_time = start_time + timedelta(days=duration_days)
    
    # Get trading hours from config
    sunday_open_hour = get_sunday_open_hour(asset_type)
    daily_open_hour = get_daily_open_hour(asset_type)
    friday_close_hour = get_friday_close_hour(asset_type)
    daily_close_hour = get_daily_close_hour(asset_type)
    
    if is_weekend(end_time, asset_type) or not is_trading_hour(end_time, asset_type):
        weekday = end_time.weekday()
        hour = end_time.hour
        
        if weekday == 4 and hour >= friday_close_hour:  # Friday after close time
            # Set to Friday just before close
            end_time = end_time.replace(hour=friday_close_hour - 1, minute=59, second=59, microsecond=999000)
        elif weekday == 5:  # Saturday
            # Go back to Friday just before close
            end_time = end_time.replace(hour=friday_close_hour - 1, minute=59, second=59, microsecond=999000)
            end_time -= timedelta(days=1)
        elif weekday == 6 and hour < sunday_open_hour:  # Sunday before market opens
            # Go back to Friday just before close
            end_time = end_time.replace(hour=friday_close_hour - 1, minute=59, second=59, microsecond=999000)
            end_time -= timedelta(days=2)
        elif weekday != 6 and daily_close_hour <= hour < daily_open_hour:  # Daily closure period (Mon-Fri)
            # Set to just before daily close same day
            end_time = end_time.replace(hour=daily_close_hour - 1, minute=59, second=59, microsecond=999000)
    
    return end_time


def get_last_valid_time(current_time: datetime, asset_type: str = 'forex') -> datetime:
    """
    Get the most recent valid trading time before current_time
    """
    check_time = current_time.replace()
    
    # Get trading hours from config
    sunday_open_hour = get_sunday_open_hour(asset_type)
    daily_open_hour = get_daily_open_hour(asset_type)
    friday_close_hour = get_friday_close_hour(asset_type)
    daily_close_hour = get_daily_close_hour(asset_type)
    
    while not is_trading_hour(check_time, asset_type) or is_weekend(check_time, asset_type):
        weekday = check_time.weekday()
        hour = check_time.hour
        
        if weekday == 5:  # Saturday
            # Go back to Friday just before close
            check_time = check_time.replace(hour=friday_close_hour - 1, minute=59, second=59, microsecond=999000)
            check_time -= timedelta(days=1)
        elif weekday == 6 and hour < sunday_open_hour:  # Sunday before market opens
            # Go back to Friday just before close
            check_time = check_time.replace(hour=friday_close_hour - 1, minute=59, second=59, microsecond=999000)
            check_time -= timedelta(days=2)
        elif weekday != 6 and daily_close_hour <= hour < daily_open_hour:  # Daily closure period (Mon-Fri)
            # Set to just before daily close same day
            check_time = check_time.replace(hour=daily_close_hour - 1, minute=59, second=59, microsecond=999000)
        else:
            # Go back one hour and try again
            check_time -= timedelta(hours=1)
    
    return check_time
