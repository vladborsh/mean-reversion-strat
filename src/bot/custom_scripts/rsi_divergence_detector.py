"""
RSI Divergence Helper - Use within other detectors for confirmation.

NOT a standalone detector. Use to add RSI divergence confirmation to your
existing trading strategies (VWAP, session sweeps, etc.).

See docs/INDICATORS.md for comprehensive documentation and integration examples.
"""

import logging
from datetime import datetime, timezone, time
from typing import Dict, Optional
import pandas as pd
from src.indicators import Indicators
from src.bot.custom_scripts.divergence_utils import (
    detect_bullish_divergence,
    detect_bearish_divergence,
    get_divergence_summary
)

logger = logging.getLogger(__name__)


class RSIDivergenceHelper:
    """
    RSI divergence analysis helper for use within other detectors.
    
    NOT a standalone detector. See docs/INDICATORS.md for usage examples.
    """
    
    def __init__(self,
                 rsi_period: int = 14,
                 divergence_lookback: int = 14,
                 rsi_oversold: float = 30.0,
                 rsi_overbought: float = 70.0):
        """Initialize RSI Divergence Helper."""
        self.rsi_period = rsi_period
        self.divergence_lookback = divergence_lookback
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        
        logger.debug(
            f"RSIDivergenceHelper initialized: "
            f"rsi_period={rsi_period}, lookback={divergence_lookback}, "
            f"zones={rsi_oversold}/{rsi_overbought}"
        )
    
    def analyze_divergence(self, data: pd.DataFrame, detect_regular: bool = True, 
                          detect_hidden: bool = False) -> Dict:
        """
        Analyze RSI divergences for use as confirmation filter.
        
        See docs/INDICATORS.md for return structure and usage examples.
        """
        try:
            # Validate input
            if data.empty or len(data) < self.rsi_period + self.divergence_lookback * 2:
                return self._empty_result('Insufficient data')
            
            # Calculate RSI
            rsi = Indicators.rsi(data, period=self.rsi_period)
            
            if rsi.isna().all():
                return self._empty_result('RSI calculation failed')
            
            # Get current values
            current_rsi = float(rsi.iloc[-1])
            is_oversold = current_rsi < self.rsi_oversold
            is_overbought = current_rsi > self.rsi_overbought
            
            # Initialize result
            result = {
                'bullish_regular': None,
                'bearish_regular': None,
                'bullish_hidden': None,
                'bearish_hidden': None,
                'rsi_current': current_rsi,
                'rsi_oversold': is_oversold,
                'rsi_overbought': is_overbought,
                'has_bullish_signal': False,
                'has_bearish_signal': False,
                'summary': ''
            }
            
            # Detect regular divergences
            if detect_regular:
                bullish_regular = detect_bullish_divergence(
                    data, rsi, 
                    lookback=self.divergence_lookback,
                    divergence_type='regular'
                )
                if bullish_regular['detected']:
                    result['bullish_regular'] = bullish_regular
                    result['has_bullish_signal'] = True
                
                bearish_regular = detect_bearish_divergence(
                    data, rsi,
                    lookback=self.divergence_lookback,
                    divergence_type='regular'
                )
                if bearish_regular['detected']:
                    result['bearish_regular'] = bearish_regular
                    result['has_bearish_signal'] = True
            
            # Detect hidden divergences
            if detect_hidden:
                bullish_hidden = detect_bullish_divergence(
                    data, rsi,
                    lookback=self.divergence_lookback,
                    divergence_type='hidden'
                )
                if bullish_hidden['detected']:
                    result['bullish_hidden'] = bullish_hidden
                    result['has_bullish_signal'] = True
                
                bearish_hidden = detect_bearish_divergence(
                    data, rsi,
                    lookback=self.divergence_lookback,
                    divergence_type='hidden'
                )
                if bearish_hidden['detected']:
                    result['bearish_hidden'] = bearish_hidden
                    result['has_bearish_signal'] = True
            
            # Build summary
            result['summary'] = self._build_summary(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing RSI divergence: {e}", exc_info=True)
            return self._empty_result(f'Error: {str(e)}')
    
    def _empty_result(self, reason: str = '') -> Dict:
        """Return empty result structure."""
        return {
            'bullish_regular': None,
            'bearish_regular': None,
            'bullish_hidden': None,
            'bearish_hidden': None,
            'rsi_current': None,
            'rsi_oversold': False,
            'rsi_overbought': False,
            'has_bullish_signal': False,
            'has_bearish_signal': False,
            'summary': reason
        }
    
    def _build_summary(self, result: Dict) -> str:
        """Build human-readable summary."""
        parts = []
        
        if result['bullish_regular']:
            parts.append('Regular Bullish Divergence')
        if result['bearish_regular']:
            parts.append('Regular Bearish Divergence')
        if result['bullish_hidden']:
            parts.append('Hidden Bullish Divergence')
        if result['bearish_hidden']:
            parts.append('Hidden Bearish Divergence')
        
        if not parts:
            return f"No divergence | RSI: {result['rsi_current']:.1f}"
        
        rsi_zone = ''
        if result['rsi_oversold']:
            rsi_zone = ' (oversold)'
        elif result['rsi_overbought']:
            rsi_zone = ' (overbought)'
        
        return f"{', '.join(parts)} | RSI: {result['rsi_current']:.1f}{rsi_zone}"
