# Signal Cache Persistence Documentation

## Related Documentation

- **[Telegram Bot Integration](TELEGRAM_BOT_INTEGRATION.md)** - Complete guide to setting up and using the Telegram bot
- **[Telegram DynamoDB Persistence](telegram_dynamodb_persistence.md)** - DynamoDB storage for chat management (shares same base class)
- **[Bot Docker Instructions](BOT_DOCKER_INSTRUCTIONS.md)** - Container deployment with persistence configuration
- **[AWS ECS Deployment](AWS_ECS_DEPLOYMENT.md)** - Cloud deployment with DynamoDB integration
- **[Data Caching](CACHING.md)** - Market data caching system (separate from signal cache)

## Overview

The signal cache now supports persistent storage using AWS DynamoDB, allowing duplicate signal detection to work across application restarts and multiple instances.

## Configuration

### Environment Variables

- `USE_PERSISTENT_CACHE`: Set to `true` to enable DynamoDB persistence (default: `true`)
- `SIGNALS_CACHE_TABLE`: DynamoDB table name (default: `trading-signals-cache`)
- `AWS_REGION`: AWS region for DynamoDB (default: `us-east-1`)

### Disabling Persistence

To use in-memory cache only:
```bash
export USE_PERSISTENT_CACHE=false
```

## Architecture

### Class Hierarchy

```
DynamoDBBase (src/bot/dynamodb_base.py)
    ├── TelegramDynamoDBStorage (telegram_dynamodb_storage.py)
    └── PersistentSignalCache (persistent_signal_cache.py)
```

### Key Components

1. **DynamoDBBase**: Base class with common DynamoDB operations
   - Table creation and management
   - CRUD operations
   - Batch operations
   - TTL (Time To Live) support

2. **PersistentSignalCache**: DynamoDB-backed signal cache
   - Automatic table creation with TTL
   - Local cache for performance
   - Duplicate detection across instances
   - Automatic expiration of old signals

3. **SignalCache**: Original in-memory implementation
   - Lightweight option for single-instance deployments
   - No external dependencies

## DynamoDB Table Structure

### Table: trading-signals-cache

| Attribute | Type | Description |
|-----------|------|-------------|
| signal_hash | String (PK) | Unique hash of signal |
| symbol | String | Trading symbol |
| direction | String | Signal direction (LONG/SHORT) |
| entry_price | Number | Entry price |
| timestamp | String | ISO timestamp when signal was sent |
| expiry_time | Number | Unix timestamp for TTL |
| full_data | Map | Complete signal data |

### TTL Configuration

- Signals automatically expire after `cache_duration_hours` (default: 24 hours)
- DynamoDB handles cleanup automatically
- No manual cleanup required

## Usage

### Default (with persistence)

```python
from src.bot.signal_cache import create_signal_cache

# Creates PersistentSignalCache by default
cache = create_signal_cache(
    use_persistence=True,  # Default
    price_tolerance=0.0005,
    cache_duration_hours=24
)
```

### In-memory only

```python
from src.bot.signal_cache import create_signal_cache

# Creates in-memory SignalCache
cache = create_signal_cache(
    use_persistence=False,
    price_tolerance=0.0005,
    cache_duration_hours=24
)
```

## Features

### Persistent Cache Benefits

1. **Survives Restarts**: Signal history maintained across application restarts
2. **Multi-Instance Support**: Multiple scheduler instances share the same cache
3. **Automatic Cleanup**: DynamoDB TTL removes expired signals
4. **Local Cache**: Fast duplicate checks with local cache, synced with DynamoDB
5. **Fallback Support**: Automatically falls back to in-memory if DynamoDB fails

### Duplicate Detection

The cache detects duplicates based on:
- Symbol match
- Direction match (LONG/SHORT)
- Price within tolerance (default 0.05%)
- Time window (default 24 hours)

## AWS Permissions Required

The IAM role/user needs the following DynamoDB permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DescribeTable",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateTimeToLive",
                "dynamodb:DescribeTimeToLive"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/trading-signals-cache",
                "arn:aws:dynamodb:*:*:table/telegram-chats"
            ]
        }
    ]
}
```

## Monitoring

### Cache Statistics

```python
stats = cache.get_cache_stats()
print(f"Cached signals (local): {stats['cached_signals_local']}")
print(f"Cached signals (DynamoDB): {stats['cached_signals_dynamodb']}")
print(f"Duplicates prevented: {stats['duplicates_prevented']}")
print(f"Duplicate rate: {stats['duplicate_rate']:.2f}%")
```

### View Cached Signals

```python
signals = cache.get_cached_signals()
for signal in signals:
    print(f"{signal['symbol']} {signal['direction']} @ {signal['entry_price']}")
```

## Troubleshooting

### DynamoDB Connection Issues

If DynamoDB connection fails, the system automatically falls back to in-memory cache. Check logs for:
- AWS credentials configuration
- Network connectivity
- IAM permissions

### Manual Cache Sync

To manually sync local cache with DynamoDB:
```python
cache.sync_local_cache()
```

### Clear Cache

To clear all cached signals:
```python
cache.clear_cache()  # Clears both local and DynamoDB
```

## Cost Considerations

- **On-Demand Pricing**: Tables use PAY_PER_REQUEST billing
- **TTL Cleanup**: Free automatic deletion of expired items
- **Typical Usage**: Very low cost for signal caching use case
- **Estimate**: < $1/month for typical trading bot usage

## See Also

- **[Risk Management](RISK_MANAGEMENT.md)** - Position sizing and risk calculations for signals
- **[Strategy Documentation](STRATEGY_DOCUMENTATION.md)** - Core trading strategy that generates signals
- **[Container Documentation](CONTAINER.md)** - General container deployment considerations
- **[Transport Layer](TRANSPORT_LAYER.md)** - Alternative storage backends for other data types