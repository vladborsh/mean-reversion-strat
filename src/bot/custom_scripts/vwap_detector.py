"""
VWAP Detector for GOLD

Strategy Logic:
1. Calculate VWAP with standard deviation bands (daily reset)
2. Signal timing window: 13:00 - 15:00 UTC
3. Short signal: 
   - Price breaks above VWAP upper band 
   - Last candle is bearish (close < open) 
   - Previous candle was bullish
   - Highest high of last 3 candles is the highest in last 3 hours
4. Long signal: 
   - Price breaks below VWAP lower band 
   - Last candle is bullish (close > open) 
   - Previous candle was bearish
   - Lowest low of last 3 candles is the lowest in last 3 hours

This strategy aims to capture mean reversion from VWAP extremes with reversal candle 
confirmation and 3-hour price extreme validation.
"""

import logging
from datetime import datetime, timezone, time
from typing import Dict, Optional
import pandas as pd
from src.indicators import Indicators

logger = logging.getLogger(__name__)


class VWAPDetector:
    """
    Detects VWAP mean reversion signals with reversal candle confirmation.
    
    Uses VWAP with standard deviation bands to identify overbought/oversold conditions,
    then waits for reversal candle pattern before generating signals.
    """
    
    def __init__(self, 
                 num_std: float = 1.0,
                 signal_window_start: str = "13:00",
                 signal_window_end: str = "15:00",
                 anchor_period: str = "day"):
        """
        Initialize the VWAP Detector.
        
        This detector identifies signal conditions based on VWAP bands and reversal candles.
        
        Args:
            num_std: Number of standard deviations for VWAP bands (default: 1.0)
            signal_window_start: Signal window start time in HH:MM format (default: "13:00")
            signal_window_end: Signal window end time in HH:MM format (default: "15:00")
            anchor_period: VWAP reset period - 'day', 'week', 'month', or 'year' (default: "day")
        """
        self.num_std = num_std
        self.anchor_period = anchor_period
        
        # Parse time strings
        self.signal_window_start = self._parse_time(signal_window_start)
        self.signal_window_end = self._parse_time(signal_window_end)
        
        logger.info(
            f"VWAPDetector initialized: "
            f"num_std={num_std}, anchor_period={anchor_period}, "
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
    
    def detect_signals(self, data: pd.DataFrame, symbol: str = 'GOLD') -> Dict:
        """
        Detect VWAP mean reversion signals from OHLCV data.
        
        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                  Timestamps should be UTC timezone-aware
            symbol: Trading symbol (default: 'GOLD')
        
        Returns:
            Dictionary containing signal information:
            {
                'signal_type': 'long' | 'short' | 'no_signal' | 'error',
                'direction': 'BUY' | 'SELL' | 'HOLD',
                'current_price': float,
                'vwap': float,
                'vwap_upper': float,
                'vwap_lower': float,
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
            
            # Check if we have enough data for VWAP calculation and candle pattern analysis
            # Need at least 36 candles (3 hours at 5m) for the extreme check
            if len(data) < 36:
                reason = "Insufficient data: need at least 36 candles (3 hours)"
                return self._create_no_signal(symbol, reason, data.iloc[-1]['timestamp'])
            
            # Prepare data with datetime index
            df = data.copy()
            
            # Ensure timestamp is datetime
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Ensure timezone awareness (assume UTC if naive)
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            else:
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
            
            # Remove duplicate timestamps (keep last) before setting as index
            df = df.drop_duplicates(subset=['timestamp'], keep='last')
            
            # Set timestamp as index for VWAP calculation
            df = df.set_index('timestamp').sort_index()
            
            # Calculate VWAP with bands using forex-compatible method
            try:
                vwap, vwap_upper, vwap_lower = Indicators.vwap_daily_reset_forex_compatible(
                    df, 
                    num_std=self.num_std,
                    anchor_period=self.anchor_period
                )
            except Exception as e:
                error_msg = f"Error calculating VWAP: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return self._create_error_signal(symbol, error_msg)
            
            # Get the last candle (most recent)
            last_idx = df.index[-1]
            last_candle = df.iloc[-1]
            last_time = last_idx.time()
            
            # Get the previous candle (second-to-last)
            prev_idx = df.index[-2]
            prev_candle = df.iloc[-2]
            
            # Check if we're in the signal timing window
            if not self._is_signal_window(last_time):
                reason = f"Outside signal window (13:00-15:00 UTC). Current time: {last_time}"
                return self._create_no_signal(symbol, reason, last_idx)
            
            # Extract candle information
            current_price = last_candle['close']
            current_open = last_candle['open']
            is_bearish = current_price < current_open
            is_bullish = current_price > current_open
            
            prev_close = prev_candle['close']
            prev_open = prev_candle['open']
            prev_is_bearish = prev_close < prev_open
            prev_is_bullish = prev_close > prev_open
            
            # Get VWAP values for the last candle
            current_vwap = vwap.iloc[-1]
            current_vwap_upper = vwap_upper.iloc[-1]
            current_vwap_lower = vwap_lower.iloc[-1]
            
            # Check price extremes over last 3 hours (36 candles at 5m)
            last_3_hours_data = df.iloc[-36:]  # Last 3 hours
            last_3_candles_data = df.iloc[-3:]  # Last 3 candles
            
            # For long: lowest low of last 3 candles should be lowest in last 3 hours
            lowest_3_candles = last_3_candles_data['low'].min()
            lowest_3_hours = last_3_hours_data['low'].min()
            is_lowest_extreme = lowest_3_candles <= lowest_3_hours
            
            # For short: highest high of last 3 candles should be highest in last 3 hours
            highest_3_candles = last_3_candles_data['high'].max()
            highest_3_hours = last_3_hours_data['high'].max()
            is_highest_extreme = highest_3_candles >= highest_3_hours
            
            # Short signal: Price above VWAP upper + bearish candle (reversal) + previous candle was bullish + at highest extreme
            if current_price > current_vwap_upper and is_bearish and prev_is_bullish and is_highest_extreme:
                logger.info(
                    f"Short signal detected: Price {current_price:.2f} > VWAP Upper {current_vwap_upper:.2f}, "
                    f"Bearish reversal candle, previous bullish, at 3h high ({highest_3_candles:.2f})"
                )
                return self._create_short_signal(
                    symbol=symbol,
                    current_price=current_price,
                    vwap=current_vwap,
                    vwap_upper=current_vwap_upper,
                    vwap_lower=current_vwap_lower,
                    timestamp=last_idx
                )
            
            # Long signal: Price below VWAP lower + bullish candle (reversal) + previous candle was bearish + at lowest extreme
            elif current_price < current_vwap_lower and is_bullish and prev_is_bearish and is_lowest_extreme:
                logger.info(
                    f"Long signal detected: Price {current_price:.2f} < VWAP Lower {current_vwap_lower:.2f}, "
                    f"Bullish reversal candle, previous bearish, at 3h low ({lowest_3_candles:.2f})"
                )
                return self._create_long_signal(
                    symbol=symbol,
                    current_price=current_price,
                    vwap=current_vwap,
                    vwap_upper=current_vwap_upper,
                    vwap_lower=current_vwap_lower,
                    timestamp=last_idx
                )
            
            # No signal
            else:
                reason = "Signal conditions not met"
                logger.debug(f"No signal: {reason}")
                return self._create_no_signal(
                    symbol, reason, last_idx, 
                    current_vwap, current_vwap_upper, current_vwap_lower
                )
        
        except Exception as e:
            error_msg = f"Error detecting signals: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._create_error_signal(symbol, error_msg)
    
    def _is_signal_window(self, current_time: time) -> bool:
        """Check if current time is within signal window."""
        return self.signal_window_start <= current_time <= self.signal_window_end
    
    def _create_long_signal(self, symbol: str, current_price: float, 
                           vwap: float, vwap_upper: float, vwap_lower: float,
                           timestamp: datetime) -> Dict:
        """Create a long (BUY) signal indicating reversal from VWAP lower band."""
        return {
            'signal_type': 'long',
            'direction': 'BUY',
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'vwap': round(vwap, 2),
            'vwap_upper': round(vwap_upper, 2),
            'vwap_lower': round(vwap_lower, 2),
            'reason': f"Price below VWAP lower ({vwap_lower:.2f}), bullish reversal candle",
            'timestamp': timestamp,
            'strategy': 'vwap'
        }
    
    def _create_short_signal(self, symbol: str, current_price: float,
                            vwap: float, vwap_upper: float, vwap_lower: float,
                            timestamp: datetime) -> Dict:
        """Create a short (SELL) signal indicating reversal from VWAP upper band."""
        return {
            'signal_type': 'short',
            'direction': 'SELL',
            'symbol': symbol,
            'current_price': round(current_price, 2),
            'vwap': round(vwap, 2),
            'vwap_upper': round(vwap_upper, 2),
            'vwap_lower': round(vwap_lower, 2),
            'reason': f"Price above VWAP upper ({vwap_upper:.2f}), bearish reversal candle",
            'timestamp': timestamp,
            'strategy': 'vwap'
        }
    
    def _create_no_signal(self, symbol: str, reason: str, timestamp: datetime,
                         vwap: Optional[float] = None,
                         vwap_upper: Optional[float] = None,
                         vwap_lower: Optional[float] = None) -> Dict:
        """Create a no-signal response."""
        result = {
            'signal_type': 'no_signal',
            'direction': 'HOLD',
            'symbol': symbol,
            'reason': reason,
            'timestamp': timestamp,
            'strategy': 'vwap'
        }
        
        if vwap is not None:
            result['vwap'] = round(vwap, 2)
        if vwap_upper is not None:
            result['vwap_upper'] = round(vwap_upper, 2)
        if vwap_lower is not None:
            result['vwap_lower'] = round(vwap_lower, 2)
        
        return result
    
    def _create_error_signal(self, symbol: str, error_message: str) -> Dict:
        """Create an error signal response."""
        return {
            'signal_type': 'error',
            'direction': 'HOLD',
            'symbol': symbol,
            'reason': error_message,
            'timestamp': datetime.now(timezone.utc),
            'strategy': 'vwap'
        }


# Helper function for easy integration
def create_vwap_detector(config: dict) -> VWAPDetector:
    """
    Factory function to create a VWAP Detector instance from config.
    
    Args:
        config: Configuration dictionary with keys:
                - num_std: Number of standard deviations for bands (default: 1.0)
                - signal_window_start: Signal window start time (HH:MM)
                - signal_window_end: Signal window end time (HH:MM)
                - anchor_period: VWAP reset period (default: 'day')
    
    Returns:
        Configured VWAPDetector instance
    """
    return VWAPDetector(
        num_std=config.get('num_std', 1.0),
        signal_window_start=config.get('signal_window_start', '13:00'),
        signal_window_end=config.get('signal_window_end', '15:00'),
        anchor_period=config.get('anchor_period', 'day')
    )
