"""
Market Regime Detection Module

This module implements comprehensive market regime detection to filter out unfavorable trading conditions.
It includes trend strength detection, volatility classification, and market condition filtering to improve
the mean reversion strategy's performance by avoiding trades during inappropriate market regimes.

Key Features:
- ADX-based trend strength detection
- Volatility regime classification (low/medium/high)
- Mean reversion suitability scoring
- Market condition filtering pipeline

Author: Trading Strategy System
Date: July 19, 2025
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Optional
from enum import Enum


class VolatilityRegime(Enum):
    """Volatility regime classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrendStrength(Enum):
    """Trend strength classification."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class MarketRegime(Enum):
    """Overall market regime classification."""
    MEAN_REVERTING = "mean_reverting"
    TRENDING = "trending"
    CHOPPY = "choppy"
    HIGH_VOLATILITY = "high_volatility"


class ADXIndicator(bt.Indicator):
    """
    Average Directional Index (ADX) implementation for trend strength detection.
    
    ADX measures the strength of a trend, regardless of direction:
    - ADX > 25: Strong trend
    - ADX 20-25: Moderate trend  
    - ADX < 20: Weak trend or ranging market
    """
    
    lines = ('adx', 'plus_di', 'minus_di')
    params = (('period', 14),)
    
    def __init__(self):
        self.high = self.data.high
        self.low = self.data.low
        self.close = self.data.close
        
        # Calculate True Range components
        self.tr1 = self.high - self.low
        self.tr2 = abs(self.high - self.close(-1))
        self.tr3 = abs(self.low - self.close(-1))
        
        # True Range
        self.tr = bt.Max(self.tr1, self.tr2, self.tr3)
        
        # Directional Movement
        self.plus_dm = bt.If(
            bt.And(self.high - self.high(-1) > self.low(-1) - self.low,
                   self.high - self.high(-1) > 0),
            self.high - self.high(-1),
            0
        )
        
        self.minus_dm = bt.If(
            bt.And(self.low(-1) - self.low > self.high - self.high(-1),
                   self.low(-1) - self.low > 0),
            self.low(-1) - self.low,
            0
        )
        
        # Smoothed values using Wilder's smoothing
        self.atr = bt.indicators.SmoothedMovingAverage(self.tr, period=self.p.period)
        self.plus_di_raw = bt.indicators.SmoothedMovingAverage(self.plus_dm, period=self.p.period)
        self.minus_di_raw = bt.indicators.SmoothedMovingAverage(self.minus_dm, period=self.p.period)
        
        # Directional Indicators
        self.lines.plus_di = 100 * self.plus_di_raw / self.atr
        self.lines.minus_di = 100 * self.minus_di_raw / self.atr
        
        # Directional Index
        self.di_diff = abs(self.lines.plus_di - self.lines.minus_di)
        self.di_sum = self.lines.plus_di + self.lines.minus_di
        
        self.dx = 100 * self.di_diff / self.di_sum
        
        # ADX (smoothed DX)
        self.lines.adx = bt.indicators.SmoothedMovingAverage(self.dx, period=self.p.period)


class VolatilityRegimeIndicator(bt.Indicator):
    """
    Volatility regime classification using ATR-based percentile ranking.
    
    Classifies current volatility relative to recent history:
    - Low: Bottom 33rd percentile
    - Medium: Middle 33rd percentile  
    - High: Top 33rd percentile
    """
    
    lines = ('volatility_percentile', 'regime_score')
    params = (('atr_period', 14), ('lookback_period', 100))
    
    def __init__(self):
        # ATR for volatility measurement
        self.atr = bt.indicators.AverageTrueRange(period=self.p.atr_period)
        
        # ATR as percentage of price for normalization
        self.atr_pct = (self.atr / self.data.close) * 100
        
    def next(self):
        # Calculate percentile ranking of current ATR
        if len(self.atr_pct) >= self.p.lookback_period:
            # Get recent ATR values
            recent_atr = [self.atr_pct[-i] for i in range(self.p.lookback_period)]
            current_atr = self.atr_pct[0]
            
            # Calculate percentile
            percentile = sum(1 for x in recent_atr if x <= current_atr) / len(recent_atr) * 100
            self.lines.volatility_percentile[0] = percentile
            
            # Convert to regime score (0-100, higher = more volatile)
            self.lines.regime_score[0] = percentile
        else:
            self.lines.volatility_percentile[0] = 50  # Default to medium
            self.lines.regime_score[0] = 50


class MarketRegimeDetector:
    """
    Comprehensive market regime detection system.
    
    Combines multiple indicators to classify market conditions and determine
    trading suitability for mean reversion strategies.
    """
    
    def __init__(self, 
                 adx_period: int = 14,
                 volatility_period: int = 14,
                 volatility_lookback: int = 100,
                 correlation_period: int = 20):
        """
        Initialize market regime detector.
        
        Args:
            adx_period: Period for ADX calculation
            volatility_period: Period for ATR/volatility calculation
            volatility_lookback: Lookback period for volatility percentile
            correlation_period: Period for price correlation analysis
        """
        self.adx_period = adx_period
        self.volatility_period = volatility_period
        self.volatility_lookback = volatility_lookback
        self.correlation_period = correlation_period
        
        # Thresholds for regime classification
        self.adx_thresholds = {
            'strong_trend': 25,
            'moderate_trend': 20,
            'weak_trend': 15
        }
        
        self.volatility_thresholds = {
            'low': 33,
            'high': 67
        }
    
    def get_trend_strength(self, adx_value: float) -> TrendStrength:
        """Classify trend strength based on ADX value."""
        if adx_value >= self.adx_thresholds['strong_trend']:
            return TrendStrength.STRONG
        elif adx_value >= self.adx_thresholds['moderate_trend']:
            return TrendStrength.MODERATE
        else:
            return TrendStrength.WEAK
    
    def get_volatility_regime(self, volatility_percentile: float) -> VolatilityRegime:
        """Classify volatility regime based on percentile ranking."""
        if volatility_percentile <= self.volatility_thresholds['low']:
            return VolatilityRegime.LOW
        elif volatility_percentile >= self.volatility_thresholds['high']:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.MEDIUM
    
    def get_market_regime(self, 
                         adx_value: float, 
                         volatility_percentile: float,
                         plus_di: float = None,
                         minus_di: float = None) -> MarketRegime:
        """
        Determine overall market regime based on multiple factors.
        
        Args:
            adx_value: Current ADX value
            volatility_percentile: Current volatility percentile (0-100)
            plus_di: Positive directional indicator
            minus_di: Negative directional indicator
            
        Returns:
            MarketRegime classification
        """
        trend_strength = self.get_trend_strength(adx_value)
        volatility_regime = self.get_volatility_regime(volatility_percentile)
        
        # High volatility override
        if volatility_regime == VolatilityRegime.HIGH:
            return MarketRegime.HIGH_VOLATILITY
        
        # Strong trending markets
        if trend_strength == TrendStrength.STRONG:
            return MarketRegime.TRENDING
        
        # Weak trend with low volatility = good for mean reversion
        if (trend_strength == TrendStrength.WEAK and 
            volatility_regime == VolatilityRegime.LOW):
            return MarketRegime.MEAN_REVERTING
        
        # Default to choppy for everything else
        return MarketRegime.CHOPPY
    
    def is_suitable_for_mean_reversion(self, 
                                     adx_value: float,
                                     volatility_percentile: float,
                                     plus_di: float = None,
                                     minus_di: float = None) -> Tuple[bool, str]:
        """
        Determine if current market conditions are suitable for mean reversion trading.
        
        Args:
            adx_value: Current ADX value
            volatility_percentile: Current volatility percentile
            plus_di: Positive directional indicator
            minus_di: Negative directional indicator
            
        Returns:
            Tuple of (is_suitable: bool, reason: str)
        """
        regime = self.get_market_regime(adx_value, volatility_percentile, plus_di, minus_di)
        trend_strength = self.get_trend_strength(adx_value)
        volatility_regime = self.get_volatility_regime(volatility_percentile)
        
        # Ideal conditions: Mean reverting regime
        if regime == MarketRegime.MEAN_REVERTING:
            return True, f"Ideal: Weak trend (ADX={adx_value:.1f}) + Low volatility ({volatility_percentile:.0f}%ile)"
        
        # Good conditions: Weak trend with medium volatility
        if (trend_strength == TrendStrength.WEAK and 
            volatility_regime == VolatilityRegime.MEDIUM):
            return True, f"Good: Weak trend (ADX={adx_value:.1f}) + Medium volatility ({volatility_percentile:.0f}%ile)"
        
        # Poor conditions
        if regime == MarketRegime.TRENDING:
            return False, f"Avoid: Strong trend (ADX={adx_value:.1f}) - mean reversion unlikely"
        
        if regime == MarketRegime.HIGH_VOLATILITY:
            return False, f"Avoid: High volatility ({volatility_percentile:.0f}%ile) - unstable conditions"
        
        # Marginal conditions: choppy markets
        return False, f"Marginal: Choppy conditions (ADX={adx_value:.1f}, Vol={volatility_percentile:.0f}%ile)"
    
    def get_regime_score(self, 
                        adx_value: float,
                        volatility_percentile: float) -> float:
        """
        Calculate a numerical score (0-100) for mean reversion suitability.
        
        Higher scores indicate better conditions for mean reversion.
        
        Args:
            adx_value: Current ADX value
            volatility_percentile: Current volatility percentile
            
        Returns:
            Score from 0 (worst) to 100 (best) for mean reversion
        """
        # Start with base score
        score = 50
        
        # ADX component (lower ADX = better for mean reversion)
        if adx_value <= 15:
            score += 30  # Excellent
        elif adx_value <= 20:
            score += 20  # Good
        elif adx_value <= 25:
            score += 5   # Marginal
        else:
            score -= 20  # Poor
        
        # Volatility component (lower-medium volatility preferred)
        if volatility_percentile <= 25:
            score += 20  # Low volatility - excellent
        elif volatility_percentile <= 50:
            score += 10  # Medium-low volatility - good
        elif volatility_percentile <= 75:
            score -= 5   # Medium-high volatility - marginal
        else:
            score -= 25  # High volatility - poor
        
        # Ensure score stays in 0-100 range
        return max(0, min(100, score))


class MarketRegimeFilter(bt.Indicator):
    """
    Backtrader indicator that combines ADX and volatility for regime filtering.
    
    This indicator can be used directly in strategies to filter trades based on
    market regime suitability for mean reversion.
    """
    
    lines = ('regime_score', 'is_suitable', 'adx', 'volatility_percentile')
    params = (
        ('adx_period', 14),
        ('volatility_period', 14),
        ('volatility_lookback', 100),
        ('min_score_threshold', 60),  # Minimum score to allow trading
    )
    
    def __init__(self):
        # Initialize component indicators
        self.adx_indicator = ADXIndicator(period=self.p.adx_period)
        self.volatility_indicator = VolatilityRegimeIndicator(
            atr_period=self.p.volatility_period,
            lookback_period=self.p.volatility_lookback
        )
        
        # Initialize regime detector
        self.detector = MarketRegimeDetector(
            adx_period=self.p.adx_period,
            volatility_period=self.p.volatility_period,
            volatility_lookback=self.p.volatility_lookback
        )
        
        # Store current regime info
        self.current_regime = None
        self.regime_reason = ""
    
    def next(self):
        # Get current indicator values
        adx_val = self.adx_indicator.adx[0]
        vol_percentile = self.volatility_indicator.volatility_percentile[0]
        
        # Store in lines for external access
        self.lines.adx[0] = adx_val
        self.lines.volatility_percentile[0] = vol_percentile
        
        # Check if we have enough data
        if (len(self.adx_indicator.adx) == 0 or 
            len(self.volatility_indicator.volatility_percentile) == 0 or
            adx_val == adx_val != adx_val):  # Check for NaN
            self.lines.regime_score[0] = 0
            self.lines.is_suitable[0] = 0
            return
        
        # Calculate regime score
        score = self.detector.get_regime_score(adx_val, vol_percentile)
        self.lines.regime_score[0] = score
        
        # Determine if suitable for trading
        is_suitable, reason = self.detector.is_suitable_for_mean_reversion(
            adx_val, vol_percentile,
            self.adx_indicator.plus_di[0],
            self.adx_indicator.minus_di[0]
        )
        
        # Store results
        self.lines.is_suitable[0] = 1 if is_suitable else 0
        self.current_regime = self.detector.get_market_regime(adx_val, vol_percentile)
        self.regime_reason = reason
        
        # Optional: Additional threshold check
        if score < self.p.min_score_threshold:
            self.lines.is_suitable[0] = 0
    
    def get_regime_info(self) -> Dict:
        """Get current regime information for logging/debugging."""
        if len(self.lines.regime_score) == 0:
            return {'regime': 'unknown', 'score': 0, 'reason': 'insufficient data'}
            
        return {
            'regime': self.current_regime.value if self.current_regime else 'unknown',
            'score': self.lines.regime_score[0],
            'is_suitable': bool(self.lines.is_suitable[0]),
            'reason': self.regime_reason,
            'adx': self.lines.adx[0],
            'volatility_percentile': self.lines.volatility_percentile[0]
        }
