# Podman Deployment Guide

## Overview

This project supports Podman deployment for both the unified trading bot and the strategy optimizer. 

### Podman Images

The project provides **two separate Dockerfiles**:

| Dockerfile | Purpose | Entry Point | Service Name |
|------------|---------|-------------|--------------|
| **Dockerfile.bot** | Live trading bot | `trading_bot.py` | `trading-bot` (recommended) |
| **Dockerfile** | Strategy optimizer | `optimize_strategy.py` | `optimizer` |

> **Important**: Make sure you're using the correct Dockerfile for your use case:
> - **Live trading**: Use `Dockerfile.bot` → Run `trading_bot.py`
> - **Backtesting/Optimization**: Use `Dockerfile` → Run `optimize_strategy.py`

### Deployment Options

The Podman setup provides:

- **Trading Bot**: Runs all strategies in parallel with shared infrastructure (recommended)
- **Legacy Bots**: Separate schedulers (deprecated, for backward compatibility)
- **Optimizer**: For backtesting and hyperparameter optimization

## Quick Start

### 1. Prerequisites

```bash
# Install Podman and Podman Compose
# macOS: Install Podman Desktop
# Linux: sudo apt-get install podman podman-compose
# Windows: Install Podman Desktop

# Verify installation
podman --version
podman-compose --version
```

### 2. Setup Environment Variables

Create a `.env` file in the project root:

```bash
# Capital.com API credentials (required)
CAPITAL_COM_API_KEY=your_api_key_here
CAPITAL_COM_PASSWORD=your_password_here
CAPITAL_COM_IDENTIFIER=your_identifier_here

# Telegram bot (optional but recommended)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# DynamoDB for persistence (optional)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1

# Signal cache settings
USE_PERSISTENT_CACHE=true
```

### 3. Run the Trading Bot

```bash
# Build and start the trading bot
podman-compose up -d trading-bot

# View logs
podman-compose logs -f trading-bot

# Stop the bot
podman-compose stop trading-bot

# Remove the bot
podman-compose down
```

## Podman Services

This project provides two main Podman images:

1. **`Dockerfile.bot`** → Live trading bot (trading-bot, mean-reversion-bot, custom-strategy-bot)
2. **`Dockerfile`** → Strategy optimizer for backtesting and hyperparameter optimization

### Trading Bot (Recommended)

**Service**: `trading-bot`  
**File**: `Dockerfile.bot`  
**Command**: `python trading_bot.py`

The trading bot runs all strategies in parallel with shared infrastructure.

```bash
# Start trading bot
podman-compose up -d trading-bot

# View real-time logs
podman-compose logs -f trading-bot

# Check status
podman-compose ps trading-bot

# Restart bot
podman-compose restart trading-bot

# Stop bot
podman-compose stop trading-bot
```

**Features**:
- Runs mean reversion and custom strategies in parallel
- Shared Telegram bot and signal cache
- Error isolation (one strategy failure doesn't stop others)
- Automatic restart on failure
- Log rotation (10MB max, 3 files)
- Health checks every 60 seconds

### Legacy Bots (Deprecated - Migration Recommended)

> **⚠️ Deprecation Notice**: 
> Legacy individual schedulers (`mean-reversion-bot`, `custom-strategy-bot`) are deprecated and will be removed in a future version.
> 
> **Please migrate to `trading-bot`** for:
> - Better performance with parallel execution
> - Shared infrastructure (single Telegram bot, signal cache)
> - Improved error handling and monitoring
> - Centralized configuration via `bot_config.json`
>
> See [Migration Guide](#migration-from-legacy-to-trading-bot) below.

**Services**: `mean-reversion-bot`, `custom-strategy-bot`  
**Profile**: `legacy`  
**File**: `Dockerfile.bot` (same as trading bot, different command)

These are the old separate schedulers, kept for backward compatibility only.

```bash
# Run legacy bots (requires --profile flag)
podman-compose --profile legacy up -d mean-reversion-bot custom-strategy-bot

# View logs
podman-compose logs -f mean-reversion-bot
podman-compose logs -f custom-strategy-bot

# Stop legacy bots
podman-compose --profile legacy down
```

**⚠️ Not recommended for new deployments**. Use trading-bot instead.

### Strategy Optimizer

**Service**: `optimizer`  
**File**: `Dockerfile`  
**Profile**: `optimizer`

For backtesting and hyperparameter optimization.

#### Basic Usage

```bash
# Run optimizer with default help
podman-compose --profile optimizer run --rm optimizer

# Run optimization for a specific symbol
podman-compose --profile optimizer run --rm optimizer \
  --symbol EURUSD \
  --timeframe 5m \
  --optimization-type grid \
  --years 1

# Run optimization with custom parameters
podman-compose --profile optimizer run --rm optimizer \
  --symbol GBPUSD \
  --timeframe 15m \
  --optimization-type search \
  --years 2 \
  --bb-window-range 10,30 \
  --vwap-window-range 10,30

# View optimization results
ls -la ./optimization/results/
```

#### Transport Configuration

The optimizer supports both local and S3 storage for cache and results:

**Local Storage (Default)**
```bash
# All data stored in mounted volumes
podman-compose --profile optimizer run --rm optimizer \
  --quick-test \
  --cache-transport local \
  --log-transport local
```

**S3 Storage**
```bash
# Store data in S3 (requires AWS credentials in .env)
podman-compose --profile optimizer run --rm optimizer \
  --quick-test \
  --cache-transport s3 \
  --log-transport s3
```

**Mixed Storage**
```bash
# S3 cache with local results
podman-compose --profile optimizer run --rm optimizer \
  --grid-search balanced \
  --cache-transport s3 \
  --log-transport local
```

#### Advanced Examples

```bash
# Grid search with equity curve plots
podman-compose --profile optimizer run --rm optimizer \
  --grid-search focused \
  --plot-equity-curves \
  --cache-transport local \
  --log-transport local

# Custom symbol and timeframe with S3 cache
podman-compose --profile optimizer run --rm optimizer \
  --quick-test \
  --symbol GBPUSD \
  --timeframe 1h \
  --cache-transport s3 \
  --log-transport local

# Random search optimization with S3 storage
podman-compose --profile optimizer run --rm optimizer \
  --random-search 50 \
  --cache-transport s3 \
  --log-transport s3
```

**Transport Options:**
- `--cache-transport local`: Store data cache in mounted volume
- `--cache-transport s3`: Store data cache in AWS S3 bucket
- `--log-transport local`: Store optimization results in mounted volume
- `--log-transport s3`: Store optimization results in AWS S3 bucket

**AWS Configuration for S3:**
Add to your `.env` file:
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

**Best Practices:**
- **Development**: Use `--cache-transport local --log-transport local` with volume mounts
- **CI/CD**: Use `--cache-transport s3 --log-transport s3` for persistent storage
- **Hybrid**: Use `--cache-transport s3 --log-transport local` to share cache but keep results local

## Configuration

### bot_config.json

The master configuration file controls which strategies run:

```json
{
  "strategies": {
    "mean_reversion": {
      "enabled": true,
      "config_file": "assets_config_wr45.json",
      ...
    },
    "custom_strategies": {
      "enabled": true,
      "config_file": "assets_config_custom_strategies.json",
      ...
    }
  }
}
```

> **Note**: The `bot_config.json` file should exist in your project root. If it doesn't exist, create it or see the trading bot documentation for the default configuration structure.

**To enable/disable strategies**:
1. Edit `bot_config.json`
2. Set `enabled: false` for strategies you don't want
3. Restart the container: `podman-compose restart trading-bot`

### Volume Mounts

The podman-compose.yml mounts the following directories:

```yaml
volumes:
  # Logs (read-write)
  - ./live_logs:/app/live_logs
  
  # Configuration files (read-only)
  - ./bot_config.json:/app/bot_config.json:ro
  - ./assets_config_wr45.json:/app/assets_config_wr45.json:ro
  - ./assets_config_custom_strategies.json:/app/assets_config_custom_strategies.json:ro
  
  # Environment variables (read-only)
  - ./.env:/app/.env:ro
```

**Benefits**:
- Logs persist on host machine
- Configuration changes don't require rebuild
- Easy to backup and monitor

## Podman Commands

### Build Images

```bash
# Build trading bot image
podman-compose build trading-bot

# Build optimizer image
podman-compose build optimizer

# Build all images
podman-compose build
```

### View Logs

```bash
# View all logs
podman-compose logs

# Follow logs (real-time)
podman-compose logs -f trading-bot

# View last 100 lines
podman-compose logs --tail=100 trading-bot

# View logs with timestamps
podman-compose logs -t trading-bot
```

### Container Management

```bash
# List running containers
podman-compose ps

# Stop all services
podman-compose stop

# Start all services
podman-compose start

# Restart a service
podman-compose restart trading-bot

# Remove containers (keeps images)
podman-compose down

# Remove containers and images
podman-compose down --rmi all

# Remove containers, images, and volumes
podman-compose down --rmi all -v
```

### Execute Commands in Container

```bash
# Open shell in container
podman-compose exec trading-bot /bin/bash

# Run Python command
podman-compose exec trading-bot python -c "print('Hello from container')"

# Check Python version
podman-compose exec trading-bot python --version

# List files
podman-compose exec trading-bot ls -la /app

# View configuration
podman-compose exec trading-bot cat /app/bot_config.json
```

### Debugging

```bash
# Check container health
podman-compose ps trading-bot

# Inspect container
podman inspect mean-reversion-trading-bot

# View resource usage
podman stats mean-reversion-trading-bot

# Check environment variables
podman-compose exec trading-bot env | grep CAPITAL_COM

# Test bot initialization
podman-compose exec trading-bot python -c "from unified_bot import main; print('OK')"
```

## Production Deployment

### Recommended Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd mean-reversion-strat

# 2. Configure environment
cp .env.example .env
nano .env  # Add your credentials

# 3. Configure strategies
nano bot_config.json  # Enable/disable strategies

# 4. Build and start
podman-compose build trading-bot
podman-compose up -d trading-bot

# 5. Verify logs
podman-compose logs -f trading-bot

# 6. Monitor
podman-compose ps
podman stats mean-reversion-trading-bot
```

### Monitoring

```bash
# Check logs regularly
podman-compose logs --tail=50 trading-bot

# Monitor resource usage
podman stats mean-reversion-trading-bot

# Check health status
podman-compose ps trading-bot

# Set up log rotation (already configured in podman-compose.yml)
# - Max size: 10MB per file
# - Max files: 3 files
# - Automatic rotation
```

### Automatic Restart

The trading-bot is configured with `restart: unless-stopped`, which means:
- Container restarts automatically if it crashes
- Container starts automatically on system boot
- Container stays stopped if manually stopped

To change restart policy:
```yaml
# podman-compose.yml
services:
  trading-bot:
    restart: no          # Never restart
    restart: always      # Always restart
    restart: on-failure  # Restart only on error
    restart: unless-stopped  # Current (recommended)
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
podman-compose logs trading-bot

# Check configuration
podman-compose config

# Verify environment variables
podman-compose exec trading-bot env
```

### Bot Not Connecting to Capital.com

```bash
# Verify credentials in container
podman-compose exec trading-bot python << 'EOF'
import os
print(f"API Key: {os.getenv('CAPITAL_COM_API_KEY')[:10]}...")
print(f"Password: {'***' if os.getenv('CAPITAL_COM_PASSWORD') else 'NOT SET'}")
print(f"Identifier: {os.getenv('CAPITAL_COM_IDENTIFIER')}")
EOF

# Test Capital.com connection
podman-compose exec trading-bot python << 'EOF'
from src.capital_com_fetcher import create_capital_com_fetcher
fetcher = create_capital_com_fetcher()
print("Connection OK" if fetcher else "Connection FAILED")
EOF
```

### Telegram Not Working

```bash
# Check token
podman-compose exec trading-bot python << 'EOF'
import os
token = os.getenv('TELEGRAM_BOT_TOKEN')
print(f"Token: {token[:10] if token else 'NOT SET'}...")
EOF

# Test Telegram bot
podman-compose exec trading-bot python << 'EOF'
from src.bot.telegram_bot import create_telegram_bot_from_env
bot = create_telegram_bot_from_env()
print("Telegram OK" if bot else "Telegram FAILED")
EOF
```

### Container Using Too Much Memory

```bash
# Check resource usage
podman stats mean-reversion-trading-bot

# Add memory limits to podman-compose.yml
services:
  trading-bot:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### Logs Taking Up Too Much Space

Logs are already configured with rotation:
- Max size: 10MB per file
- Max files: 3 files
- Total max: 30MB

To adjust:
```yaml
# podman-compose.yml
services:
  trading-bot:
    logging:
      driver: "json-file"
      options:
        max-size: "5m"    # Reduce max size
        max-file: "2"     # Reduce file count
```

## Updating the Bot

```bash
# 1. Stop the bot
podman-compose stop trading-bot

# 2. Pull latest changes
git pull origin main

# 3. Rebuild image
podman-compose build trading-bot

# 4. Start the bot
podman-compose up -d trading-bot

# 5. Verify logs
podman-compose logs -f trading-bot
```

## Migration from Legacy to Trading Bot

If you're currently using the legacy individual schedulers (`mean-reversion-bot` or `custom-strategy-bot`), follow these steps to migrate to the trading bot:

### Step 1: Understand the Differences

| Feature | Legacy Bots | Trading Bot |
|---------|------------|-------------|
| **Execution** | Sequential (one at a time) | Parallel (all strategies run simultaneously) |
| **Configuration** | Separate per-strategy config files | Single `bot_config.json` file |
| **Infrastructure** | Separate Telegram bots and caches | Shared Telegram bot and signal cache |
| **Error Handling** | One failure stops everything | Isolated failures per strategy |
| **Monitoring** | Separate logs per scheduler | Unified logging with strategy tags |
| **Maintenance** | Multiple containers to manage | Single container |

### Step 2: Create bot_config.json

Create a `bot_config.json` file in your project root:

```json
{
  "strategies": {
    "mean_reversion": {
      "enabled": true,
      "config_file": "assets_config_wr45.json",
      "check_interval_minutes": 5,
      "trading_hours": {
        "enabled": true,
        "start_hour": 6,
        "end_hour": 17,
        "timezone": "UTC"
      }
    },
    "custom_strategies": {
      "enabled": true,
      "config_file": "assets_config_custom_strategies.json",
      "check_interval_minutes": 5,
      "trading_hours": {
        "enabled": true,
        "start_hour": 0,
        "end_hour": 23,
        "timezone": "UTC"
      }
    }
  },
  "telegram": {
    "enabled": true,
    "notifications": {
      "signals": true,
      "errors": true,
      "startup": true
    }
  },
  "signal_cache": {
    "use_persistent": true,
    "cooldown_minutes": 60
  }
}
```

### Step 3: Stop Legacy Bots

```bash
# Stop the legacy containers
podman-compose --profile legacy stop mean-reversion-bot custom-strategy-bot

# Or remove them completely
podman-compose --profile legacy down
```

### Step 4: Start Trading Bot

```bash
# Build and start the trading bot
podman-compose build trading-bot
podman-compose up -d trading-bot

# Verify it's running
podman-compose ps trading-bot

# Check the logs
podman-compose logs -f trading-bot
```

### Step 5: Verify Migration

Monitor the logs to ensure:
1. Both strategies are initializing correctly
2. Trading signals are being detected
3. Telegram notifications are working
4. No error messages appear

```bash
# Check for successful initialization
podman-compose logs trading-bot | grep -i "initialized"

# Monitor for errors
podman-compose logs trading-bot | grep -i "error"

# Watch real-time activity
podman-compose logs -f trading-bot
```

### Step 6: Update Your Deployment Scripts

If you have scripts or automation, update them:

**Old:**
```bash
podman-compose --profile legacy up -d mean-reversion-bot custom-strategy-bot
```

**New:**
```bash
podman-compose up -d trading-bot
```

### Rollback (If Needed)

If you encounter issues and need to rollback:

```bash
# Stop trading bot
podman-compose stop trading-bot

# Restart legacy bots
podman-compose --profile legacy up -d mean-reversion-bot custom-strategy-bot
```

### Benefits After Migration

After migration, you'll benefit from:
- **30-50% faster execution** through parallel processing
- **Better reliability** with isolated error handling
- **Easier management** with single container
- **Improved monitoring** with unified logs
- **Lower resource usage** with shared infrastructure

### Troubleshooting Migration

**Issue: "bot_config.json not found"**
- Ensure the file exists in project root
- Check podman-compose.yml mounts it correctly
- Verify file permissions (should be readable)

**Issue: "Strategies not running"**
- Check `enabled: true` in bot_config.json
- Verify config files exist (assets_config_wr45.json, etc.)
- Check logs for specific error messages

**Issue: "Telegram not working"**
- Verify TELEGRAM_BOT_TOKEN in .env file
- Check bot was created properly with BotFather
- Test token with: `podman-compose exec trading-bot python -c "import os; print(os.getenv('TELEGRAM_BOT_TOKEN')[:10])"`

For more help, check the logs: `podman-compose logs -f trading-bot`

## Security Best Practices

1. **Never commit .env file**: Already in .gitignore
2. **Use read-only mounts**: Configuration files are mounted as `:ro`
3. **Limit container resources**: Add memory/CPU limits if needed
4. **Regular updates**: Keep Podman images updated
5. **Monitor logs**: Check for suspicious activity
6. **Secure credentials**: Use Podman secrets for production

Example with Podman secrets:
```yaml
services:
  trading-bot:
    secrets:
      - capital_com_api_key
      - capital_com_password
      - telegram_bot_token

secrets:
  capital_com_api_key:
    file: ./secrets/api_key.txt
  capital_com_password:
    file: ./secrets/password.txt
  telegram_bot_token:
    file: ./secrets/telegram_token.txt
```

## Summary

**For Production**: Use `trading-bot` service (recommended)  
**For Development**: Run locally with `python trading_bot.py`  
**For Backtesting**: Use `optimizer` service with --profile flag  
**For Legacy**: Use `mean-reversion-bot` or `custom-strategy-bot` with --profile legacy (deprecated)

### Quick Reference

| Use Case | Command | Dockerfile |
|----------|---------|------------|
| Live Trading (Recommended) | `podman-compose up -d trading-bot` | Dockerfile.bot |
| Backtesting/Optimization | `podman-compose --profile optimizer run --rm optimizer --quick-test` | Dockerfile |
| Legacy Individual Schedulers | `podman-compose --profile legacy up -d mean-reversion-bot` | Dockerfile.bot |

The trading bot provides the best performance and features with parallel execution, error isolation, and shared infrastructure.

For optimizer details including transport configuration (S3 vs local storage), see the [Strategy Optimizer](#strategy-optimizer) section above.
