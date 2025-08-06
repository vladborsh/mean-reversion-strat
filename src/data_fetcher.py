import pandas as pd
import time
import requests
from datetime import datetime, timedelta

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
        
        providers = self.provider_priorities.get(self.source, {}).get(self.timeframe, ['ccxt'])
        
        print(f"Attempting to fetch {years} years of {self.timeframe} {self.source} data for {self.symbol}")
        print(f"Provider priority order: {providers}")
        
        last_error = None
        for provider in providers:
            try:
                print(f"\n🔄 Trying provider: {provider}")
                
                if provider == 'ccxt':
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
