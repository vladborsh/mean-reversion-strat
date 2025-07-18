import yfinance as yf
import pandas as pd
import time
import requests
from datetime import datetime, timedelta

try:
    import ccxt
except ImportError:
    ccxt = None

try:
    from alpha_vantage.foreignexchange import ForeignExchange
    from alpha_vantage.timeseries import TimeSeries
except ImportError:
    ForeignExchange = None
    TimeSeries = None

try:
    from .capital_com_fetcher import CapitalComDataFetcher, create_capital_com_fetcher
except ImportError:
    CapitalComDataFetcher = None
    create_capital_com_fetcher = None

from .data_cache import get_global_cache

class DataFetcher:
    def __init__(self, source, symbol, timeframe='1h', exchange='binance', api_key=None, use_cache=True):
        self.source = source.lower()
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = exchange
        self.api_key = api_key
        self.use_cache = use_cache
        self.cache = get_global_cache() if use_cache else None
        
        # Define provider priorities for different asset types and timeframes
        # Capital.com is now the primary provider for forex and indices
        self.provider_priorities = {
            'forex': {
                '5m': ['capital_com', 'yfinance', 'alpha_vantage'],
                '15m': ['capital_com', 'yfinance', 'alpha_vantage'],
                '1h': ['capital_com', 'yfinance', 'alpha_vantage'],
                '4h': ['capital_com', 'yfinance', 'alpha_vantage'],  
                '1d': ['capital_com', 'alpha_vantage', 'yfinance']
            },
            'crypto': {
                '5m': ['ccxt', 'yfinance'],
                '15m': ['ccxt', 'yfinance'],
                '1h': ['ccxt', 'yfinance'],
                '4h': ['ccxt', 'yfinance'],
                '1d': ['ccxt', 'yfinance']
            },
            'indices': {
                '5m': ['capital_com', 'alpha_vantage', 'yfinance'],
                '15m': ['capital_com', 'alpha_vantage', 'yfinance'],
                '1h': ['capital_com', 'alpha_vantage', 'yfinance'],
                '4h': ['capital_com', 'alpha_vantage', 'yfinance'],
                '1d': ['capital_com', 'alpha_vantage', 'yfinance']
            }
        }
        
        if self.source == 'crypto' and ccxt is None:
            print('Warning: ccxt not available for crypto data fetching')
        if self.source == 'forex' and ForeignExchange is None:
            print('Warning: alpha_vantage not available for forex data fetching')
        if (self.source in ['forex', 'indices']) and CapitalComDataFetcher is None:
            print('Warning: Capital.com fetcher not available for forex/indices data fetching')

    def fetch(self, years=3):
        """Fetch data using multiple providers with fallback strategy and caching"""
        
        # Try to get data from cache first
        if self.use_cache and self.cache:
            print(f"🔍 Checking cache for {years} years of {self.timeframe} {self.source} data for {self.symbol}")
            cached_data = self.cache.get(
                source=self.source,
                symbol=self.symbol, 
                timeframe=self.timeframe,
                years=years,
                additional_params={'exchange': self.exchange} if self.source == 'crypto' else None
            )
            
            if cached_data is not None:
                print(f"📦 Cache hit! Using cached data ({len(cached_data)} rows)")
                return cached_data
            else:
                print("📦 Cache miss - fetching fresh data")
        
        providers = self.provider_priorities.get(self.source, {}).get(self.timeframe, ['yfinance'])
        
        print(f"Attempting to fetch {years} years of {self.timeframe} {self.source} data for {self.symbol}")
        print(f"Provider priority order: {providers}")
        
        last_error = None
        for provider in providers:
            try:
                print(f"\n🔄 Trying provider: {provider}")
                
                if provider == 'yfinance':
                    result = self._fetch_yfinance(years)
                elif provider == 'alpha_vantage':
                    result = self._fetch_alpha_vantage(years)
                elif provider == 'ccxt':
                    result = self._fetch_ccxt(years)
                elif provider == 'capital_com':
                    result = self._fetch_capital_com(years)
                elif provider == 'fxcm_rest':
                    result = self._fetch_fxcm_rest(years)
                else:
                    print(f"Unknown provider: {provider}")
                    continue
                
                if result is not None and not result.empty:
                    print(f"✅ Successfully fetched data using {provider}")
                    
                    # Cache the successfully fetched data
                    if self.use_cache and self.cache:
                        print(f"💾 Caching data for future use")
                        self.cache.set(
                            source=self.source,
                            symbol=self.symbol,
                            timeframe=self.timeframe,
                            years=years,
                            data=result,
                            additional_params={'exchange': self.exchange} if self.source == 'crypto' else None,
                            metadata={'provider': provider, 'fetch_time': datetime.now().isoformat()}
                        )
                    
                    return result
                else:
                    print(f"❌ {provider} returned no data")
                    
            except Exception as e:
                print(f"❌ {provider} failed: {e}")
                last_error = e
                continue
        
        # If all providers fail, raise the last error
        raise ValueError(f"All data providers failed. Last error: {last_error}")

    def clear_cache(self):
        """Clear cached data for this fetcher's configuration"""
        if self.cache:
            print("🗑️  Clearing cache...")
            self.cache.clear()
            print("✅ Cache cleared")
        else:
            print("❌ No cache configured")
    
    def get_cache_info(self):
        """Get information about cached data"""
        if self.cache:
            return self.cache.get_cache_info()
        else:
            return {"error": "No cache configured"}
    
    def invalidate_cache_for_symbol(self, years=None):
        """
        Invalidate cache for current symbol and timeframe
        
        Args:
            years (int, optional): Specific years to invalidate. If None, tries common values.
        """
        if not self.cache:
            print("❌ No cache configured")
            return
        
        # Try to invalidate common year values if not specified
        years_to_try = [years] if years else [1, 2, 3, 5]
        
        for y in years_to_try:
            cache_key = self.cache._generate_cache_key(
                source=self.source,
                symbol=self.symbol,
                timeframe=self.timeframe,
                years=y,
                additional_params={'exchange': self.exchange} if self.source == 'crypto' else None
            )
            cache_file = self.cache._get_cache_file_path(cache_key)
            
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    print(f"🗑️  Invalidated cache for {self.symbol} ({y} years)")
                except Exception as e:
                    print(f"❌ Error invalidating cache: {e}")

    @classmethod
    def get_global_cache_info(cls):
        """Get information about the global cache"""
        cache = get_global_cache()
        return cache.get_cache_info()
    
    @classmethod  
    def clear_global_cache(cls, max_age_days=30):
        """Clear old files from the global cache"""
        cache = get_global_cache()
        cache.clear(max_age_days)

    def _fetch_capital_com(self, years):
        """Fetch data from Capital.com API"""
        if CapitalComDataFetcher is None:
            raise ImportError("Capital.com fetcher not available")
        
        try:
            # Create Capital.com fetcher instance
            fetcher = create_capital_com_fetcher()
            if fetcher is None:
                raise ValueError("Could not create Capital.com fetcher - check environment variables")
            
            # Use context manager to ensure session cleanup
            with fetcher:
                result = fetcher.fetch_historical_data(
                    symbol=self.symbol,
                    asset_type=self.source,
                    timeframe=self.timeframe,
                    years=years
                )
                
                if result is not None and not result.empty:
                    print(f"Capital.com fetched {len(result)} rows of {self.timeframe} data")
                    return result
                else:
                    print("Capital.com returned no data")
                    return None
                    
        except Exception as e:
            print(f"Capital.com API error: {e}")
            return None

    def _fetch_alpha_vantage(self, years):
        """Fetch data from Alpha Vantage API"""
        if ForeignExchange is None:
            raise ImportError("alpha_vantage not available")
        
        # Check for API key
        if not self.api_key or self.api_key == 'demo':
            # Try environment variable
            import os
            self.api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
            if not self.api_key:
                print("⚠️  Alpha Vantage requires API key. Get free key at: https://www.alphavantage.co/support/#api-key")
                print("   Set ALPHA_VANTAGE_API_KEY environment variable or pass api_key parameter")
                raise ValueError("Alpha Vantage API key required")
        
        # Alpha Vantage supports up to 5 years of intraday data
        if self.source == 'forex':
            return self._fetch_alpha_vantage_forex(years)
        elif self.source == 'indices':
            return self._fetch_alpha_vantage_stocks(years)
        else:
            raise ValueError(f"Alpha Vantage doesn't support {self.source}")

    def _fetch_alpha_vantage_forex(self, years):
        """Fetch forex data from Alpha Vantage"""
        fe = ForeignExchange(key=self.api_key, output_format='pandas')
        
        # Map timeframes
        interval_map = {
            '15m': '15min',
            '1h': '60min', 
            '4h': '240min',
            '1d': 'daily'
        }
        
        interval = interval_map.get(self.timeframe, '60min')
        
        # Extract currency pair (e.g., EURUSD=X -> EUR, USD)
        if '=' in self.symbol:
            base_symbol = self.symbol.replace('=X', '')
        else:
            base_symbol = self.symbol
            
        if len(base_symbol) == 6:
            from_currency = base_symbol[:3]
            to_currency = base_symbol[3:]
        else:
            # Default to EUR/USD if parsing fails
            from_currency = 'EUR'
            to_currency = 'USD'
            print(f"Warning: Could not parse currency pair from {self.symbol}, using EUR/USD")
        
        try:
            if self.timeframe == '1d':
                data, _ = fe.get_currency_exchange_daily(from_symbol=from_currency, 
                                                       to_symbol=to_currency, 
                                                       outputsize='full')
            else:
                data, _ = fe.get_currency_exchange_intraday(from_symbol=from_currency,
                                                          to_symbol=to_currency,
                                                          interval=interval,
                                                          outputsize='full')
            
            if data.empty:
                return None
                
            # Process Alpha Vantage data format
            data = data.rename(columns={
                '1. open': 'open',
                '2. high': 'high', 
                '3. low': 'low',
                '4. close': 'close',
                '5. volume': 'volume'
            })
            
            # Alpha Vantage returns data in reverse chronological order
            data = data.sort_index()
            
            # Filter to requested time range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=365 * years)
            data = data[data.index >= start_date]
            
            print(f"Alpha Vantage fetched {len(data)} rows of {self.timeframe} data")
            return data[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
        except Exception as e:
            print(f"Alpha Vantage API error: {e}")
            return None

    def _fetch_alpha_vantage_stocks(self, years):
        """Fetch stock/index data from Alpha Vantage"""
        ts = TimeSeries(key=self.api_key, output_format='pandas')
        
        interval_map = {
            '15m': '15min',
            '1h': '60min',
            '4h': '240min', 
            '1d': 'daily'
        }
        
        interval = interval_map.get(self.timeframe, '60min')
        
        try:
            if self.timeframe == '1d':
                data, _ = ts.get_daily_adjusted(symbol=self.symbol, outputsize='full')
            else:
                data, _ = ts.get_intraday(symbol=self.symbol, 
                                        interval=interval,
                                        outputsize='full')
            
            if data.empty:
                return None
                
            # Process Alpha Vantage data format  
            data = data.rename(columns={
                '1. open': 'open',
                '2. high': 'high',
                '3. low': 'low', 
                '4. close': 'close',
                '6. volume': 'volume'
            })
            
            # Alpha Vantage returns data in reverse chronological order
            data = data.sort_index()
            
            # Filter to requested time range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=365 * years)
            data = data[data.index >= start_date]
            
            print(f"Alpha Vantage fetched {len(data)} rows of {self.timeframe} data")
            return data[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
        except Exception as e:
            print(f"Alpha Vantage API error: {e}")
            return None

    def _fetch_fxcm_rest(self, years):
        """Fetch forex data from FXCM REST API (free historical data)"""
        # FXCM provides free historical forex data but requires registration
        # This is a placeholder - in production you'd implement the actual API calls
        
        try:
            # Map symbol format
            if '=' in self.symbol:
                base_symbol = self.symbol.replace('=X', '')
                if len(base_symbol) == 6:
                    fxcm_symbol = f"{base_symbol[:3]}/{base_symbol[3:]}"
                else:
                    fxcm_symbol = 'EUR/USD'
            else:
                fxcm_symbol = self.symbol
                
            print(f"FXCM REST API requires registration and API credentials")
            print("Skipping FXCM for now - would need proper API setup")
            return None
            
        except Exception as e:
            print(f"FXCM REST API error: {e}")
            return None

    def _fetch_yfinance(self, years):
        # Ensure we're working with historical data only
        end = datetime.utcnow()
        start = end - timedelta(days=365 * years)
        interval = self._map_timeframe_yf(self.timeframe)
        
        print(f"Requesting data from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ({interval})")
        
        # For intraday data, check if the requested period exceeds limits
        days_requested = (end - start).days
        max_days_for_interval = self._get_max_safe_days(interval)
        
        if days_requested <= max_days_for_interval:
            # Try to fetch all data at once first
            try:
                result = self._fetch_single_period(start, end, interval)
                if result is not None and not result.empty:
                    print(f"Successfully fetched {len(result)} rows of {interval} data in single request.")
                    return result
            except Exception as e:
                print(f"Single period fetch failed: {e}")
                # Check if it's a time range limitation error
                if "60 days" in str(e) or "requested range" in str(e).lower():
                    print("Detected time range limitation. Switching to iterative fetching...")
                else:
                    print("Error not related to time range. Trying iterative approach anyway...")
        else:
            print(f"Requested period ({days_requested} days) exceeds safe limit for {interval}. Using iterative approach.")
        
        # If single fetch fails or hits time limits, use iterative approach
        print(f"Attempting iterative data fetching for {years} years of {interval} data...")
        result = self._fetch_iterative(start, end, interval)
        
        if result is not None and not result.empty:
            return result
        
        # Final fallback to daily data
        print("Attempting to fetch daily data as final fallback...")
        try:
            result = self._fetch_single_period(start, end, '1d')
            if result is not None and not result.empty:
                print(f"Successfully fetched {len(result)} rows of daily data as fallback.")
                return result
        except Exception as fallback_e:
            print(f"Daily data fallback also failed: {fallback_e}")
        
        raise ValueError(f"Unable to fetch data for {self.symbol} with any method or interval.")

    def _fetch_single_period(self, start, end, interval):
        """Fetch data for a single time period"""
        df = yf.download(self.symbol, start=start, end=end, interval=interval, auto_adjust=True)
        
        if df.empty:
            return None
        
        return self._process_dataframe(df)

    def _fetch_iterative(self, start, end, interval):
        """Fetch data iteratively in chunks to handle time range limitations"""
        # Ensure we don't try to fetch future data
        now = datetime.utcnow()
        if end > now:
            end = now
            print(f"Adjusted end date to current time: {end.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if start >= end:
            print("Invalid date range: start date is after end date")
            return None
        
        # Define chunk sizes based on interval to stay within limits
        chunk_days = self._get_chunk_size(interval)
        
        all_data = []
        current_start = start
        chunk_count = 0
        max_chunks = 200  # Increased safety limit for longer periods
        failed_chunks = 0
        max_failed_chunks = 10  # Allow some failures but not too many
        
        print(f"Starting iterative fetch with {chunk_days}-day chunks from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}...")
        
        while current_start < end and chunk_count < max_chunks and failed_chunks < max_failed_chunks:
            chunk_count += 1
            current_end = min(current_start + timedelta(days=chunk_days), end)
            
            # Skip chunks that are in the future
            if current_start >= now:
                print(f"Skipping future chunk {chunk_count}: {current_start.strftime('%Y-%m-%d')} (beyond current time)")
                break
            
            # Adjust current_end if it's in the future
            if current_end > now:
                current_end = now
                print(f"Adjusted chunk end time to current time: {current_end.strftime('%Y-%m-%d')}")
            
            print(f"Fetching chunk {chunk_count}: {current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')}")
            
            try:
                chunk_data = self._fetch_single_period(current_start, current_end, interval)
                
                if chunk_data is not None and not chunk_data.empty:
                    all_data.append(chunk_data)
                    print(f"  -> Successfully fetched {len(chunk_data)} rows")
                    failed_chunks = 0  # Reset failed counter on success
                else:
                    print(f"  -> No data returned for this chunk")
                    failed_chunks += 1
                
            except Exception as e:
                print(f"  -> Error fetching chunk: {e}")
                failed_chunks += 1
                
                # Try with smaller chunk size if we hit an error
                if "60 days" in str(e) or "requested range" in str(e).lower():
                    if chunk_days > 10:  # Don't go below 10 days
                        chunk_days = max(10, chunk_days // 2)
                        print(f"  -> Reducing chunk size to {chunk_days} days and retrying...")
                        continue
                    else:
                        print(f"  -> Chunk size already at minimum, moving to next period")
                
            # Move to next chunk
            current_start = current_end
            
            # Break if we've reached current time
            if current_end >= now:
                break
            
            # Small delay to be respectful to the API
            time.sleep(0.1)
        
        if failed_chunks >= max_failed_chunks:
            print(f"⚠️  Too many failed chunks ({failed_chunks}), stopping iterative fetch")
        
        if not all_data:
            print("No data collected from any chunks")
            return None
        
        # Combine all chunks
        print(f"Combining {len(all_data)} data chunks...")
        combined_df = pd.concat(all_data, sort=False)
        
        # Remove duplicates that might occur at chunk boundaries
        combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
        combined_df = combined_df.sort_index()
        
        print(f"Final combined dataset: {len(combined_df)} rows from {combined_df.index[0]} to {combined_df.index[-1]}")
        return combined_df

    def _get_chunk_size(self, interval):
        """Determine appropriate chunk size based on interval to stay within API limits"""
        # Conservative chunk sizes to stay well within 60-day limits
        chunk_sizes = {
            '15m': 25,   # 25 days for 15-minute data (very conservative)
            '60m': 40,   # 40 days for hourly data  
            '240m': 50,  # 50 days for 4-hour data
            '1d': 365    # 1 year for daily data (no real limit)
        }
        return chunk_sizes.get(interval, 25)  # Default to 25 days

    def _get_max_safe_days(self, interval):
        """Get the maximum safe number of days for a single request"""
        max_days = {
            '15m': 30,   # 30 days max for 15-minute data
            '60m': 50,   # 50 days max for hourly data
            '240m': 60,  # 60 days max for 4-hour data  
            '1d': 365 * 10  # 10 years for daily data
        }
        return max_days.get(interval, 30)

    def _process_dataframe(self, df):
        """Process and clean the dataframe from Yahoo Finance"""
        # Handle multi-level columns from Yahoo Finance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.rename(columns={
            'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'
        })
        df = df[['open', 'high', 'low', 'close', 'volume']]
        df.index = pd.to_datetime(df.index)
        result = df.dropna()
        
        if result.empty:
            return None
            
        return result

    def _fetch_ccxt(self, years):
        """Fetch crypto data from specified exchange via ccxt"""
        if ccxt is None:
            raise ImportError("ccxt not available")
            
        try:
            ex = getattr(ccxt, self.exchange)()
            return self._fetch_ccxt_data(ex, self.symbol, years)
        except Exception as e:
            print(f"CCXT {self.exchange} error: {e}")
            return None

    def _fetch_ccxt_data(self, exchange, symbol, years):
        """Common method to fetch data via ccxt"""
        since = int((datetime.utcnow() - timedelta(days=365*years)).timestamp() * 1000)
        limit = 1000
        all_ohlcv = []
        
        print(f"Fetching {symbol} data from {exchange.id}...")
        
        while True:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, since=since, limit=limit)
                if not ohlcv:
                    break
                all_ohlcv += ohlcv
                since = ohlcv[-1][0] + 1
                if len(ohlcv) < limit:
                    break
                # Rate limiting
                time.sleep(exchange.rateLimit / 1000)
            except Exception as e:
                print(f"Error fetching batch: {e}")
                break
                
        if not all_ohlcv:
            return None
            
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        
        print(f"CCXT fetched {len(df)} rows of {self.timeframe} data")
        return df[['open', 'high', 'low', 'close', 'volume']].astype(float)

    def _map_timeframe_yf(self, tf):
        mapping = {'15m': '15m', '1h': '60m', '4h': '240m', '1d': '1d'}
        return mapping.get(tf, '1h')
