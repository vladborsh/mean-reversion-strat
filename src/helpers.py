"""
Trading hours and datetime helper functions for financial markets.

This module contains pure functions for handling trading hours, weekend detection,
and datetime adjustments for forex and other financial markets.
"""

from datetime import datetime, timedelta
from typing import Optional


def format_trading_session_info(date: datetime) -> str:
    """Get formatted string with trading session information"""
    weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekday = weekday_names[date.weekday()]
    
    status = "TRADING" if is_trading_hour(date) and not is_weekend(date) else "CLOSED"
    
    if is_weekend(date):
        next_open = get_next_valid_time(date)
        return f"{weekday} {date.strftime('%H:%M')} UTC - WEEKEND (next open: {next_open.strftime('%a %H:%M')})"
    elif not is_trading_hour(date):
        next_open = get_next_valid_time(date)
        return f"{weekday} {date.strftime('%H:%M')} UTC - {status} (next open: {next_open.strftime('%a %H:%M')})"
    else:
        return f"{weekday} {date.strftime('%H:%M')} UTC - {status}"


def is_weekend(date: datetime) -> bool:
    """Check if the date is a weekend (Saturday or Sunday before 22:00)"""
    weekday = date.weekday()  # Monday = 0, Sunday = 6
    hour = date.hour
    
    if weekday == 5:  # Saturday
        return True
    if weekday == 6 and hour < 22:  # Sunday before 22:00
        return True
    
    return False


def is_trading_hour(date: datetime) -> bool:
    """
    Check if the datetime is within trading hours for forex markets
    Forex markets are open from Sunday 22:00 UTC to Friday 21:00 UTC
    """
    weekday = date.weekday()  # Monday = 0, Sunday = 6
    hour = date.hour
    
    # Market closes at 21:00 UTC on Friday
    if weekday == 4 and hour >= 21:  # Friday >= 21:00
        return False
    
    # Saturday is always closed
    if weekday == 5:  # Saturday
        return False
    
    # Sunday before 22:00 is closed
    if weekday == 6 and hour < 22:  # Sunday before 22:00
        return False
    
    # Market has a brief closure between 21:00 and 22:00 UTC daily (except Sunday opening)
    if 21 <= hour < 22 and not (weekday == 6 and hour >= 22):
        return False
    
    return True


def get_next_valid_time(current_time: datetime) -> datetime:
    """
    Get the next valid trading time based on current time
    Skips weekends and non-trading hours
    """
    new_time = current_time.replace()
    
    while not is_trading_hour(new_time) or is_weekend(new_time):
        weekday = new_time.weekday()
        hour = new_time.hour
        
        if weekday == 4 and hour >= 21:  # Friday after market closing
            # Move to Sunday 22:00 UTC
            days_to_add = 2
            new_time = new_time.replace(hour=22, minute=0, second=0, microsecond=0)
            new_time += timedelta(days=days_to_add)
        elif weekday == 5:  # Saturday
            # Move to Sunday 22:00 UTC
            days_to_add = 1
            new_time = new_time.replace(hour=22, minute=0, second=0, microsecond=0)
            new_time += timedelta(days=days_to_add)
        elif weekday == 6 and hour < 22:  # Sunday before market opens
            # Set to 22:00 UTC same day
            new_time = new_time.replace(hour=22, minute=0, second=0, microsecond=0)
        elif not is_trading_hour(new_time):  # Non-trading hours on weekdays
            if hour < 22:
                # Move to 22:00 same day
                new_time = new_time.replace(hour=22, minute=0, second=0, microsecond=0)
            else:
                # Move to next day 22:00
                new_time = new_time.replace(hour=22, minute=0, second=0, microsecond=0)
                new_time += timedelta(days=1)
        else:
            break  # Valid trading time found
    
    return new_time


def adjust_end_time(start_time: datetime, duration_days: int) -> datetime:
    """
    Adjust end time to ensure it doesn't fall on non-trading periods
    """
    end_time = start_time + timedelta(days=duration_days)
    
    if is_weekend(end_time) or not is_trading_hour(end_time):
        weekday = end_time.weekday()
        hour = end_time.hour
        
        if weekday == 4 and hour >= 21:  # Friday after 21:00
            # Set to Friday 20:59:59
            end_time = end_time.replace(hour=20, minute=59, second=59, microsecond=999000)
        elif weekday == 5:  # Saturday
            # Go back to Friday 20:59:59
            end_time = end_time.replace(hour=20, minute=59, second=59, microsecond=999000)
            end_time -= timedelta(days=1)
        elif weekday == 6 and hour < 22:  # Sunday before 22:00
            # Go back to Friday 20:59:59
            end_time = end_time.replace(hour=20, minute=59, second=59, microsecond=999000)
            end_time -= timedelta(days=2)
        elif 21 <= hour < 22:  # Daily closure period
            # Set to 20:59:59 same day
            end_time = end_time.replace(hour=20, minute=59, second=59, microsecond=999000)
    
    return end_time


def get_last_valid_time(current_time: datetime) -> datetime:
    """
    Get the most recent valid trading time before current_time
    """
    check_time = current_time.replace()
    
    while not is_trading_hour(check_time) or is_weekend(check_time):
        weekday = check_time.weekday()
        hour = check_time.hour
        
        if weekday == 5:  # Saturday
            # Go back to Friday 20:59:59
            check_time = check_time.replace(hour=20, minute=59, second=59, microsecond=999000)
            check_time -= timedelta(days=1)
        elif weekday == 6 and hour < 22:  # Sunday before 22:00
            # Go back to Friday 20:59:59
            check_time = check_time.replace(hour=20, minute=59, second=59, microsecond=999000)
            check_time -= timedelta(days=2)
        elif 21 <= hour < 22:  # Daily closure period
            # Set to 20:59:59 same day
            check_time = check_time.replace(hour=20, minute=59, second=59, microsecond=999000)
        else:
            # Go back one hour and try again
            check_time -= timedelta(hours=1)
    
    return check_time
