import pandas as pd
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, Union

try:
    import ccxt
except ImportError:
    ccxt = None

try:
    from .capital_com_fetcher import CapitalComDataFetcher, create_capital_com_fetcher
except ImportError:
    CapitalComDataFetcher = None
    create_capital_com_fetcher = None

from .data_cache import get_global_cache

class DataFetcher:
    def __init__(self, source, symbol, timeframe='1h', exchange='binance', api_key=None, use_cache=True, cache_transport_type='local'):
        self.source = source.lower()
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = exchange
        self.api_key = api_key
        self.use_cache = use_cache
        self.cache_transport_type = cache_transport_type
        
        # Initialize cache with transport type if caching is enabled
        if use_cache:
            from .data_cache import DataCache
            from .transport_factory import create_cache_transport
            transport = create_cache_transport(transport_type=cache_transport_type)
            self.cache = DataCache(transport=transport)
        else:
            self.cache = None
        
        # Define provider priorities for different asset types and timeframes
        # Capital.com is now the primary provider for forex and indices
        self.provider_priorities = {
            'forex': {
                '5m': ['capital_com'],
                '15m': ['capital_com'],
                '1h': ['capital_com'],
                '4h': ['capital_com'],  
                '1d': ['capital_com']
            },
            'crypto': {
                '5m': ['ccxt'],
                '15m': ['ccxt'],
                '1h': ['ccxt'],
                '4h': ['ccxt'],
                '1d': ['ccxt']
            },
            'indices': {
                '5m': ['capital_com'],
                '15m': ['capital_com'],
                '1h': ['capital_com'],
                '4h': ['capital_com'],
                '1d': ['capital_com']
            }
        }
        
        if self.source == 'crypto' and ccxt is None:
            print('Warning: ccxt not available for crypto data fetching')
        if (self.source in ['forex', 'indices']) and CapitalComDataFetcher is None:
            print('Warning: Capital.com fetcher not available for forex/indices data fetching')

    def _parse_date(self, date_input: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse date input into datetime object"""
        if date_input is None:
            return None
        
        if isinstance(date_input, datetime):
            return date_input
        
        if isinstance(date_input, str):
            try:
                # Try parsing ISO format dates
                if 'T' in date_input:
                    return datetime.fromisoformat(date_input.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(date_input)
            except ValueError:
                try:
                    # Try parsing common formats
                    return datetime.strptime(date_input, '%Y-%m-%d')
                except ValueError:
                    raise ValueError(f"Unable to parse date: {date_input}. Use ISO format like '2023-01-01' or '2023-01-01T10:00:00'")
        
        raise ValueError(f"Invalid date type: {type(date_input)}. Use string or datetime object.")
    
    def fetch(self, years: Optional[Union[int, float]] = None, 
             start_date: Optional[Union[str, datetime]] = None, 
             end_date: Optional[Union[str, datetime]] = None):
        """Fetch data using multiple providers with fallback strategy and caching
        
        Args:
            years: Number of years of data to fetch (backward compatibility)
            start_date: Start date for data fetching (string or datetime)
            end_date: End date for data fetching (string or datetime)
            
        Note:
            - If years is provided, start_date and end_date are ignored
            - If start_date and end_date are provided, years is ignored
            - If only start_date is provided, end_date defaults to current time
            - If only end_date is provided, raises ValueError
            - If none provided, defaults to years=3
        """
        
        # Parse and validate date parameters
        parsed_start_date = self._parse_date(start_date)
        parsed_end_date = self._parse_date(end_date)
        
        # Parameter validation and resolution
        if years is not None:
            # Use years parameter (backward compatibility)
            if start_date is not None or end_date is not None:
                print("⚠️  Both years and date range specified. Using years parameter for backward compatibility.")
            actual_years = years
            actual_start_date = None
            actual_end_date = None
            date_mode = False
        elif start_date is not None or end_date is not None:
            # Use date range mode
            if start_date is not None and end_date is None:
                # Default end_date to current time
                parsed_end_date = datetime.utcnow()
                print(f"📅 End date not specified, using current time: {parsed_end_date.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            elif start_date is None and end_date is not None:
                raise ValueError("If end_date is specified, start_date must also be provided")
            
            # Validate date range
            if parsed_start_date >= parsed_end_date:
                raise ValueError(f"Start date ({parsed_start_date}) must be before end date ({parsed_end_date})")
            
            actual_years = None
            actual_start_date = parsed_start_date
            actual_end_date = parsed_end_date
            date_mode = True
        else:
            # Default to 3 years
            actual_years = 3
            actual_start_date = None
            actual_end_date = None
            date_mode = False
            print("📅 No date parameters specified, defaulting to 3 years of data")
        
        # Try to get data from cache first
        if self.use_cache and self.cache:
            if date_mode:
                print(f"🔍 Checking cache for {self.timeframe} {self.source} data for {self.symbol} from {actual_start_date.strftime('%Y-%m-%d')} to {actual_end_date.strftime('%Y-%m-%d')}")
            else:
                print(f"🔍 Checking cache for {actual_years} years of {self.timeframe} {self.source} data for {self.symbol}")
            
            cached_data = self.cache.get(
                source=self.source,
                symbol=self.symbol, 
                timeframe=self.timeframe,
                years=actual_years,
                start_date=actual_start_date,
                end_date=actual_end_date,
                additional_params={'exchange': self.exchange} if self.source == 'crypto' else None
            )
            
            if cached_data is not None:
                print(f"📦 Cache hit! Using cached data ({len(cached_data)} rows)")
                return cached_data
            else:
                print("📦 Cache miss - fetching fresh data")
        
        providers = self.provider_priorities.get(self.source, {}).get(self.timeframe, ['ccxt'])
        
        if date_mode:
            print(f"Attempting to fetch {self.timeframe} {self.source} data for {self.symbol} from {actual_start_date.strftime('%Y-%m-%d')} to {actual_end_date.strftime('%Y-%m-%d')}")
        else:
            print(f"Attempting to fetch {actual_years} years of {self.timeframe} {self.source} data for {self.symbol}")
        print(f"Provider priority order: {providers}")
        
        last_error = None
        for provider in providers:
            try:
                print(f"\n🔄 Trying provider: {provider}")
                
                if provider == 'ccxt':
                    result = self._fetch_ccxt(actual_years, actual_start_date, actual_end_date)
                elif provider == 'capital_com':
                    result = self._fetch_capital_com(actual_years, actual_start_date, actual_end_date)
                elif provider == 'fxcm_rest':
                    result = self._fetch_fxcm_rest(actual_years, actual_start_date, actual_end_date)
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
                            years=actual_years,
                            start_date=actual_start_date,
                            end_date=actual_end_date,
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

    def _fetch_capital_com(self, years=None, start_date=None, end_date=None):
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
                    years=years,
                    start_date=start_date,
                    end_date=end_date
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

    def _fetch_fxcm_rest(self, years=None, start_date=None, end_date=None):
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

    def _fetch_ccxt(self, years=None, start_date=None, end_date=None):
        """Fetch crypto data from specified exchange via ccxt"""
        if ccxt is None:
            raise ImportError("ccxt not available")
            
        try:
            ex = getattr(ccxt, self.exchange)()
            return self._fetch_ccxt_data(ex, self.symbol, years, start_date, end_date)
        except Exception as e:
            print(f"CCXT {self.exchange} error: {e}")
            return None

    def _fetch_ccxt_data(self, exchange, symbol, years=None, start_date=None, end_date=None):
        """Common method to fetch data via ccxt"""
        # Calculate date range
        if start_date is not None:
            since = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000) if end_date else None
        else:
            # Fallback to years-based calculation
            since = int((datetime.utcnow() - timedelta(days=365*years)).timestamp() * 1000)
            end_timestamp = None
        limit = 1000
        all_ohlcv = []
        
        if start_date:
            date_info = f"from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d') if end_date else 'now'}"
        else:
            date_info = f"for {years} years"
        print(f"Fetching {symbol} data {date_info} from {exchange.id}...")
        
        while True:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=self.timeframe, since=since, limit=limit)
                if not ohlcv:
                    break
                
                # Check if we've reached the end date
                if end_timestamp and ohlcv[-1][0] >= end_timestamp:
                    # Filter out data beyond end_date
                    ohlcv = [candle for candle in ohlcv if candle[0] < end_timestamp]
                    all_ohlcv += ohlcv
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
