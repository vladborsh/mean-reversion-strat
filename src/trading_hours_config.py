"""
Trading hours configuration for different asset types.

This module centralizes all trading hours settings to make it easy to adjust
market opening/closing times for different asset classes.

HOW TO MODIFY TRADING HOURS:
-----------------------------
To change trading hours for any asset type, simply edit the values in the
TRADING_HOURS_CONFIG dictionary below. All times are in UTC (24-hour format).

Example: To change EU indices Sunday opening from 23:00 to 22:30:
    'eu_indices': {
        'sunday_open': 22.5,  # or use 22 for 22:00
        ...
    }

Note: Currently all times must be on the hour (integer values).
"""

# Market opening times (UTC)
TRADING_HOURS_CONFIG = {
    # Forex markets
    'forex': {
        'sunday_open': 22,      # Sunday 22:00 UTC
        'daily_open': 22,       # Daily reopening at 22:00 UTC (Mon-Fri)
        'friday_close': 21,     # Friday 21:00 UTC
        'daily_close': 21,      # Daily closure at 21:00 UTC (Mon-Fri)
    },
    
    # USA indices (S&P 500, NASDAQ, Dow Jones, etc.)
    'indices': {
        'sunday_open': 22,      # Sunday 22:00 UTC (same as forex)
        'daily_open': 22,       # Daily reopening at 22:00 UTC (Mon-Fri)
        'friday_close': 21,     # Friday 21:00 UTC
        'daily_close': 21,      # Daily closure at 21:00 UTC (Mon-Fri)
    },
    
    # European indices (DAX, FTSE, CAC40, etc.)
    'eu_indices': {
        'sunday_open': 23,      # Sunday 23:00 UTC (1 hour later than forex/USA)
        'daily_open': 22,       # Daily reopening at 22:00 UTC (Mon-Fri, same as others)
        'friday_close': 21,     # Friday 21:00 UTC
        'daily_close': 21,      # Daily closure at 21:00 UTC (Mon-Fri)
    },
    
    # Alternative name for EU indices
    'european_indices': {
        'sunday_open': 23,      # Sunday 23:00 UTC
        'daily_open': 22,       # Daily reopening at 22:00 UTC (Mon-Fri)
        'friday_close': 21,     # Friday 21:00 UTC
        'daily_close': 21,      # Daily closure at 21:00 UTC (Mon-Fri)
    },
    
    # Cryptocurrencies (24/7 trading, but respecting standard hours for consistency)
    'crypto': {
        'sunday_open': 22,      # Sunday 22:00 UTC
        'daily_open': 22,       # Daily reopening at 22:00 UTC (Mon-Fri)
        'friday_close': 21,     # Friday 21:00 UTC
        'daily_close': 21,      # Daily closure at 21:00 UTC (Mon-Fri)
    },
    
    # Commodities / Precious metals
    'commodities': {
        'sunday_open': 22,      # Sunday 22:00 UTC
        'daily_open': 22,       # Daily reopening at 22:00 UTC (Mon-Fri)
        'friday_close': 21,     # Friday 21:00 UTC
        'daily_close': 21,      # Daily closure at 21:00 UTC (Mon-Fri)
    },
}


def get_trading_hours(asset_type: str = 'forex') -> dict:
    """
    Get trading hours configuration for a specific asset type.
    
    Args:
        asset_type: Asset type ('forex', 'indices', 'eu_indices', 'crypto', 'commodities')
    
    Returns:
        Dictionary with trading hours configuration
    """
    return TRADING_HOURS_CONFIG.get(asset_type, TRADING_HOURS_CONFIG['forex'])


def get_sunday_open_hour(asset_type: str = 'forex') -> int:
    """Get Sunday opening hour for an asset type."""
    config = get_trading_hours(asset_type)
    return config['sunday_open']


def get_daily_open_hour(asset_type: str = 'forex') -> int:
    """Get daily reopening hour (Mon-Fri) for an asset type."""
    config = get_trading_hours(asset_type)
    return config['daily_open']


def get_friday_close_hour(asset_type: str = 'forex') -> int:
    """Get Friday closing hour for an asset type."""
    config = get_trading_hours(asset_type)
    return config['friday_close']


def get_daily_close_hour(asset_type: str = 'forex') -> int:
    """Get daily closure hour (Mon-Fri) for an asset type."""
    config = get_trading_hours(asset_type)
    return config['daily_close']
