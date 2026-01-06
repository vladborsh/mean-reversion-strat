import pandas as pd
import numpy as np

class Indicators:
    @staticmethod
    def bollinger_bands(df, window=20, num_std=2):
        close = df['close']
        ma = close.rolling(window).mean()
        std = close.rolling(window).std()
        upper = ma + num_std * std
        lower = ma - num_std * std
        return ma, upper, lower

    @staticmethod
    def vwap_bands(df, window=20, num_std=2):
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).rolling(window).sum() / df['volume'].rolling(window).sum()
        std = typical_price.rolling(window).std()
        upper = vwap + num_std * std
        lower = vwap - num_std * std
        return vwap, upper, lower

    @staticmethod
    def vwap_daily_reset(df: pd.DataFrame, num_std: float = 1.0, anchor_period: str = 'day') -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate VWAP with configurable anchor period reset and standard deviation bands.
        
        This implementation provides VWAP that resets at the start of each anchor period:
        - VWAP resets based on the specified anchor period (day/week/month/year)
        - Uses typical price (HLC/3) for volume weighting
        - Calculates expanding standard deviation of price deviations within each period
        - Returns VWAP with upper and lower bands based on standard deviation
        
        Args:
            df: DataFrame with OHLCV data and datetime index
            num_std: Number of standard deviations for bands
            anchor_period: Reset period - 'day', 'week', 'month', or 'year'
            
        Returns:
            tuple: (vwap, vwap_upper, vwap_lower) as pandas Series
            
        Raises:
            ValueError: If required columns are missing, data is empty, or invalid anchor_period
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        
        required_cols = {'high', 'low', 'close', 'volume'}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")
        
        valid_periods = {'day', 'week', 'month', 'year'}
        if anchor_period not in valid_periods:
            raise ValueError(f"Invalid anchor_period '{anchor_period}'. Must be one of: {valid_periods}")
        
        # Calculate typical price using vectorized operations
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        volume_weighted_price = typical_price * df['volume']
        
        # Create grouping key based on anchor period
        def _get_period_key(timestamp):
            """Generate grouping key based on anchor period."""
            if anchor_period == 'day':
                return timestamp.date()
            elif anchor_period == 'week':
                # Use ISO week (Monday as start of week)
                return f"{timestamp.isocalendar().year}-W{timestamp.isocalendar().week:02d}"
            elif anchor_period == 'month':
                return f"{timestamp.year}-{timestamp.month:02d}"
            elif anchor_period == 'year':
                return timestamp.year
        
        period_groups = df.index.to_series().apply(_get_period_key)
        
        def _calculate_period_vwap(group_data: pd.DataFrame) -> pd.DataFrame:
            """Calculate VWAP and bands for a single period's data."""
            group_idx = group_data.index
            tp = typical_price.loc[group_idx]
            vol = df['volume'].loc[group_idx]
            vwp = volume_weighted_price.loc[group_idx]
            
            # Calculate cumulative sums for VWAP
            cum_volume = vol.cumsum()
            cum_vwp = vwp.cumsum()
            
            # Calculate VWAP
            vwap = cum_vwp / cum_volume
            
            # Calculate expanding standard deviation of deviations
            deviations = tp - vwap
            expanding_std = deviations.expanding(min_periods=1).std(ddof=0)
            
            # Calculate bands
            upper_band = vwap + (num_std * expanding_std)
            lower_band = vwap - (num_std * expanding_std)
            
            return pd.DataFrame({
                'vwap': vwap,
                'vwap_upper': upper_band,
                'vwap_lower': lower_band
            }, index=group_idx)
        
        # Apply calculation to each period and concatenate results
        period_results = []
        for period_key, group_indices in df.groupby(period_groups).groups.items():
            group_data = df.loc[group_indices]
            period_result = _calculate_period_vwap(group_data)
            period_results.append(period_result)
        
        # Combine all period results
        result_df = pd.concat(period_results).sort_index()
        
        # Handle edge case where std is NaN for first data point
        result_df['vwap_upper'] = result_df['vwap_upper'].fillna(result_df['vwap'])
        result_df['vwap_lower'] = result_df['vwap_lower'].fillna(result_df['vwap'])
        
        return (
            result_df['vwap'],
            result_df['vwap_upper'], 
            result_df['vwap_lower']
        )
    
    @staticmethod
    def vwap_daily_reset_forex_compatible(df: pd.DataFrame, num_std: float = 1.0, anchor_period: str = 'day') -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate VWAP with configurable anchor period reset, compatible with forex data.
        
        For forex data where volume might be zero or unavailable, this method:
        1. First tries standard VWAP calculation
        2. If volume is zero/unavailable, falls back to typical price moving average
        3. Uses price-based standard deviation for bands
        
        Args:
            df: DataFrame with OHLCV data and datetime index
            num_std: Number of standard deviations for bands
            anchor_period: Reset period - 'day', 'week', 'month', or 'year'
            
        Returns:
            tuple: (vwap, vwap_upper, vwap_lower) as pandas Series
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        
        required_cols = {'high', 'low', 'close'}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")
        
        valid_periods = {'day', 'week', 'month', 'year'}
        if anchor_period not in valid_periods:
            raise ValueError(f"Invalid anchor_period '{anchor_period}'. Must be one of: {valid_periods}")
        
        # Calculate typical price
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Check if volume data is usable
        has_volume = 'volume' in df.columns and (df['volume'] > 0).any()
        
        if has_volume:
            # Use standard VWAP calculation
            return Indicators.vwap_daily_reset(df, num_std, anchor_period)
        else:
            # Create grouping key based on anchor period
            def _get_period_key(timestamp):
                if anchor_period == 'day':
                    return timestamp.date()
                elif anchor_period == 'week':
                    return f"{timestamp.isocalendar().year}-W{timestamp.isocalendar().week:02d}"
                elif anchor_period == 'month':
                    return f"{timestamp.year}-{timestamp.month:02d}"
                elif anchor_period == 'year':
                    return timestamp.year
            
            period_groups = df.index.to_series().apply(_get_period_key)
            
            def _calculate_period_price_avg(group_data: pd.DataFrame) -> pd.DataFrame:
                """Calculate expanding typical price average for a single period."""
                group_idx = group_data.index
                tp = typical_price.loc[group_idx]
                
                # Calculate expanding mean (resets each period)
                expanding_avg = tp.expanding(min_periods=1).mean()
                
                # Calculate expanding standard deviation of deviations from the expanding average
                deviations = tp - expanding_avg
                expanding_std = deviations.expanding(min_periods=1).std(ddof=0)
                
                # Handle first point where std is NaN
                expanding_std = expanding_std.fillna(0)
                
                # Calculate bands
                upper_band = expanding_avg + (num_std * expanding_std)
                lower_band = expanding_avg - (num_std * expanding_std)
                
                return pd.DataFrame({
                    'vwap': expanding_avg,
                    'vwap_upper': upper_band,
                    'vwap_lower': lower_band
                }, index=group_idx)
            
            # Apply calculation to each period and concatenate results
            period_results = []
            for period_key, group_indices in df.groupby(period_groups).groups.items():
                group_data = df.loc[group_indices]
                period_result = _calculate_period_price_avg(group_data)
                period_results.append(period_result)
            
            # Combine all period results
            result_df = pd.concat(period_results).sort_index()
            
            # Handle edge cases
            result_df['vwap_upper'] = result_df['vwap_upper'].fillna(result_df['vwap'])
            result_df['vwap_lower'] = result_df['vwap_lower'].fillna(result_df['vwap'])
            
            return (
                result_df['vwap'],
                result_df['vwap_upper'], 
                result_df['vwap_lower']
            )
    
    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.Series:
        """
        Calculate RSI using Wilder's smoothing method.
        
        See docs/INDICATORS.md for detailed documentation.
        
        Args:
            df: DataFrame with price data
            period: RSI period (default: 14)
            column: Column name (default: 'close')
            
        Returns:
            pd.Series: RSI values (0-100)
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty")
        
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        if period < 2:
            raise ValueError(f"Period must be at least 2, got {period}")
        
        # Get price series
        prices = df[column].copy()
        
        # Calculate price changes
        delta = prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)
        
        # Calculate initial averages using simple mean for first period
        avg_gain = gains.rolling(window=period, min_periods=period).mean()
        avg_loss = losses.rolling(window=period, min_periods=period).mean()
        
        # Apply Wilder's smoothing for subsequent values
        # Wilder's smoothing: new_avg = (prev_avg * (period - 1) + current_value) / period
        for i in range(period, len(df)):
            avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gains.iloc[i]) / period
            avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + losses.iloc[i]) / period
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        # Handle edge cases: when avg_loss=0 RSI=100, when avg_gain=0 RSI=0
        rsi = rsi.where(avg_loss != 0, 100.0)
        rsi = rsi.where(avg_gain != 0, 0.0)
        
        return rsi
