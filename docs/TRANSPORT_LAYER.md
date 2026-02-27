# Transport Layer Documentation

## Overview

The Mean Reversion Strategy project includes a flexible transport layer that supports both local filesystem and AWS S3 storage for caching and logging. This allows you to seamlessly switch between local development and cloud-based storage without changing your code.

## Features

### Supported Transports
- **Local Filesystem**: Default option, stores files locally
- **AWS S3**: Cloud storage option for scalability and team collaboration

### Supported Data Types
- **Data Cache**: Market data caching (OHLCV data)
- **Optimization Results**: Backtest results, CSV logs, progress tracking
- **Best Parameters**: JSON files with optimal strategy parameters
- **Performance Logs**: Optimization progress and status files

### Key Benefits
- **Automatic Fallback**: Falls back to local storage if S3 configuration fails
- **Unified Interface**: Same API regardless of storage backend
- **Transport-specific Optimizations**: Each transport is optimized for its storage type

## Configuration

### Environment Variables (for AWS S3 access only)

Add these variables to your `.env` file for S3 support:

```bash
# AWS S3 Configuration (required for S3 transport)
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
AWS_S3_PREFIX=mean-reversion-strat/  # Optional prefix

# Note: CACHE_TRANSPORT and LOG_TRANSPORT are now configured via CLI arguments
# Use --cache-transport and --log-transport options when running scripts
```

### Transport Configuration via CLI

**⚠️ Breaking Change**: Transport configuration has moved from environment variables to command-line arguments for better control and flexibility.

All CLI tools now accept these parameters:
- `--cache-transport {local,s3}`: Configure cache storage backend (default: local)
- `--log-transport {local,s3}`: Configure log/optimization storage backend (default: local)

**Examples:**
```bash
# Strategy backtesting
python scripts/run_backtest.py --cache-transport local --log-transport local    # All local (default)
python scripts/run_backtest.py --cache-transport s3 --log-transport s3          # All S3
python scripts/run_backtest.py --cache-transport local --log-transport s3       # Mixed

# Optimization
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
python optimize_strategy.py --random-search 100 --cache-transport local --log-transport s3

# Cache management  
python cache_manager.py info --cache-transport s3
python cache_manager.py clear --cache-transport local --log-transport s3
```

### Transport Types

#### Local Transport
- **Use case**: Development, small-scale testing, no cloud dependency
- **Storage**: Local filesystem
- **Benefits**: Fast access, no external dependencies, no costs
- **Limitations**: No sharing across machines, manual backup required

#### S3 Transport
- **Use case**: Production, team collaboration, automatic backup
- **Storage**: AWS S3 bucket
- **Benefits**: Scalable, shared access, automatic backup, durability
- **Limitations**: Requires AWS credentials, potential network latency, AWS costs

## Usage Examples

### CLI-Based Configuration (Recommended)

The transport layer is now configured via command-line arguments for better control:

```bash
# Strategy backtesting with different transport configurations
python scripts/run_backtest.py --cache-transport local --log-transport local    # Default
python scripts/run_backtest.py --cache-transport s3 --log-transport s3          # Full S3
python scripts/run_backtest.py --cache-transport local --log-transport s3       # Mixed mode

# Optimization with transport selection
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
```

### Programmatic Usage

```python
from src.data_cache import DataCache
from src.hyperparameter_optimizer import HyperparameterOptimizer
from src.transport_factory import create_cache_transport, create_optimization_transport

# Data cache with explicit transport type
cache_transport = create_cache_transport(transport_type='s3')
cache = DataCache(transport=cache_transport)

# Hyperparameter optimizer with transport types
optimizer = HyperparameterOptimizer(
    data_source='forex',
    symbol='EURUSD',
    timeframe='15m',
    years=2,
    cache_transport_type='s3',
    log_transport_type='s3'
)
```

### Manual Transport Creation

```python
from src.transport import LocalTransport
from src.s3_transport import S3Transport
from src.data_cache import DataCache

# Local transport
local_transport = LocalTransport('/path/to/cache')
cache = DataCache(transport=local_transport)

# S3 transport
s3_transport = S3Transport(
    bucket_name='my-trading-bucket',
    prefix='mean-reversion/',
    aws_access_key_id='...',
    aws_secret_access_key='...'
)
cache = DataCache(transport=s3_transport)
```

## Cache Management Commands

### View Cache Information
```bash
# View data cache information
python cache_manager.py info --cache-transport local
python cache_manager.py info --cache-transport s3

# View optimization storage information
python cache_manager.py optimization-info --log-transport local
python cache_manager.py optimization-info --log-transport s3
```

### Clear Cache
```bash
# Clear old cache files (older than specified days)
python cache_manager.py clear --max-age-days 7 --cache-transport local
python cache_manager.py clear --max-age-days 7 --cache-transport s3

# Clear all cache files
python cache_manager.py clear --cache-transport local
python cache_manager.py clear --cache-transport s3
```

### Invalidate Specific Cache
```bash
# Invalidate cache for specific symbol
python cache_manager.py invalidate --symbol EURUSD --cache-transport local
python cache_manager.py invalidate --symbol EURUSD --cache-transport s3
```

## S3 Storage Structure

When using S3 transport, files are organized with the following structure:

```
s3://your-bucket/mean-reversion-strat/
├── cache/                          # Market data cache
│   ├── data_hash1.pkl
│   └── data_hash2.pkl
├── logs/                          # Optimization logs
│   ├── results/
│   │   ├── grid_search_20250722_143052.csv
│   │   └── best_params_20250722_143052.json
│   └── logs/
│       └── progress_20250722_143052.txt
└── optimization/                  # Full optimization results
    ├── cache/
    │   ├── result_hash1_param1.pkl
    │   └── result_hash2_param2.pkl
    ├── results/
    └── logs/
```

## Performance Considerations

### Local Transport
- **Read/Write**: Very fast (limited by disk I/O)
- **List operations**: Fast (filesystem operations)
- **Cleanup**: Fast (direct file deletion)

### S3 Transport  
- **Read/Write**: Moderate speed (network dependent)
- **List operations**: Moderate (S3 API calls)
- **Cleanup**: Efficient (batch operations)
- **Costs**: Pay per request and storage

## Error Handling and Fallback

The system includes robust error handling:

1. **Configuration Errors**: Falls back to local transport
2. **Network Issues**: Logs errors, continues operation where possible
3. **Permission Issues**: Clear error messages with fallback suggestions
4. **Corrupted Files**: Automatic cleanup and retry

## Migration Between Transports

### Local to S3 Migration

```bash
# Export existing local cache info
python cache_manager.py info --cache-transport local > local_cache_info.txt

# Start using S3 for new operations (existing local data remains)
python scripts/run_backtest.py --cache-transport s3 --log-transport s3
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3

# Optional: Manually upload existing local data to S3 if needed
# aws s3 sync ./cache/ s3://your-bucket/mean-reversion-strat/cache/
# aws s3 sync ./optimization/ s3://your-bucket/mean-reversion-strat/optimization/
```

### S3 to Local Migration  

```bash
# Download S3 data if you want to preserve it locally
aws s3 sync s3://your-bucket/mean-reversion-strat/cache/ ./cache/
aws s3 sync s3://your-bucket/mean-reversion-strat/optimization/ ./optimization/

# Start using local transport
python scripts/run_backtest.py --cache-transport local --log-transport local
python optimize_strategy.py --grid-search balanced --cache-transport local --log-transport local
```

### Environment Variable Migration (Breaking Change)

**⚠️ If you were using `CACHE_TRANSPORT` and `LOG_TRANSPORT` environment variables:**

**Old approach (.env file):**
```bash
CACHE_TRANSPORT=s3
LOG_TRANSPORT=s3
```

**New approach (CLI arguments):**
```bash
# Remove from .env file and use CLI arguments instead
python scripts/run_backtest.py --cache-transport s3 --log-transport s3
python optimize_strategy.py --grid-search balanced --cache-transport s3 --log-transport s3
python cache_manager.py info --cache-transport s3
```

**Benefits of CLI approach:**
- Per-run configuration without changing environment
- Better control and visibility of transport settings
- Easier to mix transport types for different operations
- No need to restart shells after .env changes

## Best Practices

### Development
- Use local transport for fast iteration
- Enable S3 for long-term experiments
- Regular cleanup of old files

### Production
- Use S3 transport for durability  
- Set up proper AWS IAM permissions
- Monitor AWS costs
- Implement lifecycle policies on S3 bucket

### Team Collaboration
- Shared S3 bucket for team access
- Clear naming conventions for optimization runs
- Regular cleanup policies

## AWS S3 Setup

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://your-bucket-name
   ```

2. **Configure AWS Credentials**:
   - Option 1: Environment variables (recommended for containers)
   - Option 2: AWS credentials file (`~/.aws/credentials`)
   - Option 3: IAM roles (for EC2 instances)

3. **Set up IAM User** with these permissions:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "s3:GetObject",
                   "s3:PutObject",
                   "s3:DeleteObject",
                   "s3:ListBucket"
               ],
               "Resource": [
                   "arn:aws:s3:::your-bucket-name",
                   "arn:aws:s3:::your-bucket-name/*"
               ]
           }
       ]
   }
   ```

## Security Considerations

- Use IAM roles or environment variables for AWS credentials
- Restrict S3 bucket access to necessary operations only
- Enable S3 encryption at rest for sensitive data

## Troubleshooting

### Common Issues

1. **S3 Connection Failed**
   ```
   Error: Failed to create S3 transport: No credentials found
   Solution: Configure AWS credentials in .env file
   ```

2. **Permission Denied**
   ```
   Error: Access denied to S3 bucket
   Solution: Check AWS IAM permissions for S3 operations
   ```

3. **Bucket Not Found**
   ```
   Error: S3 bucket 'bucket-name' not found
   Solution: Create bucket or check bucket name in .env
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Monitoring and Maintenance

### Regular Tasks
- Monitor S3 costs and usage
- Clean up old optimization files
- Review and rotate AWS credentials
- Check for failed uploads/downloads

### Monitoring Commands
```bash
# Check cache status
python cache_manager.py info

# Check optimization storage
python cache_manager.py optimization-info

# Performance test
python cache_manager.py test
```
