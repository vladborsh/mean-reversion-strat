"""
Asia Session Sweep Detector for DE40 (DAX Index)

Strategy Logic:
1. Define Asia session: 3:00 AM - 7:00 AM UTC (Tokyo/Sydney overlap)
2. Calculate session high/low from all 5-minute candles in that range
3. Signal timing window: 8:30 AM - 9:30 AM UTC (European market open)
4. Long signal: Price breaks below session low + last candle is bullish (close > open) - rejection
5. Short signal: Price breaks above session high + last candle is bearish (close < open) - rejection

This strategy aims to capture liquidity sweeps during the transition from Asia to Europe sessions.
"""

import logging
from datetime import datetime, timezone, time
from typing import Dict, Optional, List, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class AsiaSessionSweepDetector:
    """
    Detects session sweep signals based on configurable session high/low breaks.
    
    Can be used for any asset with customizable session ranges.
    """
    
    def __init__(self, 
                 session_start: str = "03:00",
                 session_end: str = "07:00",
                 signal_window_start: str = "08:30",
                 signal_window_end: str = "09:00"):
        """
        Initialize the Asia Session Sweep Detector.
        
        This detector only identifies signal conditions without calculating
        entry prices, stop losses, or take profits.
        
        Args:
            session_start: Session start time in HH:MM format (default: "03:00")
            session_end: Session end time in HH:MM format (default: "07:00")
            signal_window_start: Signal window start time in HH:MM format (default: "08:30")
            signal_window_end: Signal window end time in HH:MM format (default: "09:00")
        """
        # Parse time strings
        self.session_start = self._parse_time(session_start)
        self.session_end = self._parse_time(session_end)
        self.signal_window_start = self._parse_time(signal_window_start)
        self.signal_window_end = self._parse_time(signal_window_end)
        
        logger.info(
            f"AsiaSessionSweepDetector initialized: "
            f"session={session_start}-{session_end}, "
            f"signals={signal_window_start}-{signal_window_end}"
        )
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format."""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid time format '{time_str}': {e}")
            raise ValueError(f"Time must be in HH:MM format, got: {time_str}")
    
    def detect_signals(self, data: pd.DataFrame, symbol: str = 'DE40') -> Dict:
        """
        Detect session sweep signals from OHLCV data.
        
        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                  Timestamps should be UTC timezone-aware
            symbol: Trading symbol (default: 'DE40')
        
        Returns:
            Dictionary containing signal information:
            {
                'signal_type': 'long' | 'short' | 'no_signal' | 'error',
                'direction': 'BUY' | 'SELL' | 'HOLD',
                'current_price': float,
                'session_high': float,
                'session_low': float,
                'reason': str,
                'timestamp': datetime,
                'symbol': str
            }
        """
        try:
            # Validate data
            if data is None or data.empty:
                return self._create_error_signal(symbol, "Empty data provided")
            
            required_cols = ['timestamp', 'open', 'high', 'low', 'close']
            if not all(col in data.columns for col in required_cols):
                return self._create_error_signal(symbol, f"Missing required columns. Need: {required_cols}")
            
            # Ensure timestamp is datetime
            if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                data = data.copy()
                data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Ensure timezone awareness (assume UTC if naive)
            if data['timestamp'].dt.tz is None:
                data = data.copy()
                data['timestamp'] = data['timestamp'].dt.tz_localize('UTC')
            else:
                data = data.copy()
                data['timestamp'] = data['timestamp'].dt.tz_convert('UTC')
            
            # Sort by timestamp
            data = data.sort_values('timestamp').reset_index(drop=True)
            
            # Get the last candle (most recent)
            last_candle = data.iloc[-1]
            last_timestamp = last_candle['timestamp']
            last_time = last_timestamp.time()
            
            # Check if we have enough data for previous candle analysis
            if len(data) < 2:
                reason = "Insufficient data: need at least 2 candles"
                return self._create_no_signal(symbol, reason, last_timestamp)
            
            # Check if we're in the signal timing window
            if not self._is_signal_window(last_time):
                reason = f"Outside signal window (8:30-9:00 UTC). Current time: {last_time}"
                return self._create_no_signal(symbol, reason, last_timestamp)
            
            # Get today's date for session filtering
            current_date = last_timestamp.date()
            
            # Extract session candles for today
            session_candles = self._get_session_candles(data, current_date)
            
            if session_candles.empty:
                reason = f"No session data found for {current_date}"
                logger.warning(reason)
                return self._create_no_signal(symbol, reason, last_timestamp)
            
            # Calculate session high/low
            session_high = session_candles['high'].max()
            session_low = session_candles['low'].min()

            # Check for signals
            current_price = last_candle['close']
            current_open = last_candle['open']
            is_bearish = current_price < current_open
            is_bullish = current_price > current_open
            
            # Get the previous candle (second-to-last)
            prev_candle = data.iloc[-2]
            prev_close = prev_candle['close']
            prev_open = prev_candle['open']
            prev_is_bearish = prev_close < prev_open
            prev_is_bullish = prev_close > prev_open
            
            # Long signal: Price below session low + bullish candle (rejection) + previous candle was bearish
            if current_price < session_low and is_bullish and prev_is_bearish:
                logger.info(
                    f"Long signal detected: Price {current_price:.2f} < Session Low {session_low:.2f}, "
                    f"Bullish candle (close > open) - rejection, previous candle was bearish"
                )
                return self._create_long_signal(
                    symbol=symbol,
                    current_price=current_price,
                    session_high=session_high,
                    session_low=session_low,
                    timestamp=last_timestamp
                )
            
            # Short signal: Price above session high + bearish candle (rejection) + previous candle was bullish
            elif current_price > session_high and is_bearish and prev_is_bullish:
                logger.info(
                    f"Short signal detected: Price {current_price:.2f} > Session High {session_high:.2f}, "
                    f"Bearish candle (close < open) - rejection, previous candle was bullish"
                )
                return self._create_short_signal(
                    symbol=symbol,
                    current_price=current_price,
                    session_high=session_high,
                    session_low=session_low,
                    timestamp=last_timestamp
                )
            
            # No signal
            else:
                reason = "Signal conditions not met"
                logger.debug(f"No signal: {reason}")
                return self._create_no_signal(symbol, reason, last_timestamp, 
                                               session_high, session_low)
        
        except Exception as e:
            error_msg = f"Error detecting signals: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._create_error_signal(symbol, error_msg)
    
    def _is_signal_window(self, current_time: time) -> bool:
        """Check if current time is within signal window."""
        return self.signal_window_start <= current_time <= self.signal_window_end
    
    def _is_session(self, current_time: time) -> bool:
        """Check if current time is within the tracking session."""
        return self.session_start <= current_time < self.session_end
    
    def _get_session_candles(self, data: pd.DataFrame, target_date) -> pd.DataFrame:
        """
        Extract candles from the configured session for a specific date.
        
        Args:
            data: Full OHLCV DataFrame
            target_date: Date to extract session from
        
        Returns:
            DataFrame containing only session candles
        """
        # Filter for target date
        data_today = data[data['timestamp'].dt.date == target_date].copy()
        
        # Filter for session hours
        session_candles = data_today[
            data_today['timestamp'].dt.time.between(
                self.session_start, 
                self.session_end,
                inclusive='left'  # Include start, exclude end
            )
        ]
        
        return session_candles
    
    def _create_long_signal(self, symbol: str, current_price: float, 
                           session_high: float, session_low: float,
                           timestamp: datetime) -> Dict:
        """Create a long (BUY) signal indicating rejection from session low."""
        return {
            'signal_type': 'long',
            'direction': 'BUY',
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'session_high': round(session_high, 2),
            'session_low': round(session_low, 2),
            'reason': f"Price broke below session low ({session_low:.2f}), bullish reversal candle",
            'timestamp': timestamp,
            'strategy': 'session_sweep'
        }
    
    def _create_short_signal(self, symbol: str, current_price: float,
                            session_high: float, session_low: float,
                            timestamp: datetime) -> Dict:
        """Create a short (SELL) signal indicating rejection from session high."""
        return {
            'signal_type': 'short',
            'direction': 'SELL',
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'session_high': round(session_high, 2),
            'session_low': round(session_low, 2),
            'reason': f"Price broke above session high ({session_high:.2f}), bearish reversal candle",
            'timestamp': timestamp,
            'strategy': 'session_sweep'
        }
    
    def _create_no_signal(self, symbol: str, reason: str, timestamp: datetime,
                         session_high: Optional[float] = None,
                         session_low: Optional[float] = None) -> Dict:
        """Create a no-signal response."""
        result = {
            'signal_type': 'no_signal',
            'direction': 'HOLD',
            'symbol': symbol,
            'reason': reason,
            'timestamp': timestamp,
            'strategy': 'session_sweep'
        }
        
        if session_high is not None:
            result['session_high'] = round(session_high, 2)
        if session_low is not None:
            result['session_low'] = round(session_low, 2)
        
        return result
    
    def _create_error_signal(self, symbol: str, error_message: str) -> Dict:
        """Create an error signal response."""
        return {
            'signal_type': 'error',
            'direction': 'HOLD',
            'symbol': symbol,
            'reason': error_message,
            'timestamp': datetime.now(timezone.utc),
            'strategy': 'session_sweep'
        }


# Helper function for easy integration
def create_session_sweep_detector(config: dict) -> AsiaSessionSweepDetector:
    """
    Factory function to create a Session Sweep Detector instance from config.
    
    Args:
        config: Configuration dictionary with keys:
                - session_start: Session start time (HH:MM)
                - session_end: Session end time (HH:MM)
                - signal_window_start: Signal window start time (HH:MM)
                - signal_window_end: Signal window end time (HH:MM)
    
    Returns:
        Configured AsiaSessionSweepDetector instance
    """
    return AsiaSessionSweepDetector(
        session_start=config.get('session_start', '03:00'),
        session_end=config.get('session_end', '07:00'),
        signal_window_start=config.get('signal_window_start', '08:30'),
        signal_window_end=config.get('signal_window_end', '09:00')
    )
