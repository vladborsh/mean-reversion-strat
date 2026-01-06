# Strategy Scheduler and Bot Podman Instructions

This document provides instructions for building and running the Podman container for the Mean Reversion Strategy Scheduler with Telegram Bot integration.

> **Note**: This project uses Podman and podman-compose. All commands use `podman` and `podman-compose`.

## Related Documentation

- **[Telegram Bot Integration](TELEGRAM_BOT_INTEGRATION.md)** - Complete guide to setting up and using the Telegram bot
- **[Signal Cache Persistence](signal_cache_persistence.md)** - DynamoDB configuration for signal duplicate prevention
- **[Telegram DynamoDB Persistence](telegram_dynamodb_persistence.md)** - DynamoDB storage for chat management
- **[Container Documentation](CONTAINER.md)** - General container usage and deployment
- **[Strategy Documentation](STRATEGY_DOCUMENTATION.md)** - Core strategy implementation details

## Prerequisites

Before building and running the container, ensure you have:

1. **Podman and Podman Compose installed** on your system
   - macOS/Windows: [Podman Desktop](https://podman.io/getting-started/installation)
   - Linux: `sudo apt-get install podman podman-compose`
2. **Environment variables** configured (see Environment Setup below)
3. **Configuration files** in place (for legacy bots - unified bot uses bot_config.json)
   - `.env` file with required API credentials
   - See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for unified bot setup

## Environment Setup

Create a `.env` file in the project root with the following required variables:

```bash
# Capital.com API credentials (required for data fetching)
CAPITAL_COM_API_KEY=your_api_key_here
CAPITAL_COM_PASSWORD=your_password_here
CAPITAL_COM_IDENTIFIER=your_identifier_here

# Telegram Bot Token (optional, for notifications)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# DynamoDB Configuration (optional, for persistence)
# Signal Cache Persistence
USE_PERSISTENT_CACHE=true
SIGNALS_CACHE_TABLE=trading-signals-cache

# Telegram Chat Persistence  
TELEGRAM_CHATS_TABLE=telegram-chats
AWS_REGION=us-east-1

# AWS Credentials (if using DynamoDB)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Build Instructions

> **Recommended**: Use the unified bot via podman-compose. See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for complete setup.

### Build the Podman Image

```bash
# Navigate to the project root directory
cd /path/to/mean-reversion-strat

# Build using podman-compose (recommended)
podman-compose build unified-bot

# Or build directly with Podman
podman build -f Dockerfile.bot -t mean-reversion-bot:latest .
```

### Verify the Build

```bash
# Check that the image was created successfully
podman images | grep mean-reversion-bot
```

## Run Instructions

> **Important**: The unified bot (unified_bot.py) is now the recommended way to run trading strategies. 
> This section documents legacy individual scheduler usage. See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for unified bot setup.

### Using Podman Compose (Recommended)

```bash
# Run the unified bot (recommended)
podman-compose up -d unified-bot

# View logs
podman-compose logs -f unified-bot

# Stop the bot
podman-compose stop unified-bot
```

### Legacy: Basic Run (with .env file)

```bash
# Run the legacy scheduler container with environment file
podman run --rm \
  --env-file .env \
  -v $(pwd)/live_logs:/app/live_logs \
  -v $(pwd)/results:/app/results \
  mean-reversion-bot:latest
```

### Legacy: Run with Environment Variables

```bash
# Run with explicit environment variables
podman run --rm \
  -e CAPITAL_COM_API_KEY=your_api_key \
  -e CAPITAL_COM_PASSWORD=your_password \
  -e CAPITAL_COM_IDENTIFIER=your_identifier \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -v $(pwd)/live_logs:/app/live_logs \
  -v $(pwd)/results:/app/results \
  mean-reversion-bot:latest
```

### Legacy: Run in Background (Detached Mode)

```bash
# Run the container in the background
podman run -d \
  --name mean-reversion-bot \
  --env-file .env \
  -v $(pwd)/live_logs:/app/live_logs \
  -v $(pwd)/results:/app/results \
  --restart unless-stopped \
  mean-reversion-bot:latest
```

### Legacy: Run without Telegram (Data Analysis Only)

If you want to run the strategy without Telegram notifications:

```bash
podman run --rm \
  -e CAPITAL_COM_API_KEY=your_api_key \
  -e CAPITAL_COM_PASSWORD=your_password \
  -e CAPITAL_COM_IDENTIFIER=your_identifier \
  -v $(pwd)/live_logs:/app/live_logs \
  -v $(pwd)/results:/app/results \
  mean-reversion-bot:latest
```

## Volume Mounts Explained

- **`live_logs:/app/live_logs`**: Persistent storage for trading logs and analysis results
- **`results:/app/results`**: Access to optimized strategy configurations (legacy bots only)

> **Note**: The unified bot uses bot_config.json for configuration instead of results directory. See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md#configuration).

## Container Behavior

### What the Container Does

> **Note**: This describes legacy scheduler behavior. The unified bot has enhanced features including parallel execution and better error handling.

1. **Initializes** the live strategy scheduler
2. **Loads** configuration (unified bot: bot_config.json, legacy: results/best_configs_balanced.json)
3. **Runs analysis cycles** every 5 minutes (:00, :05, :10, etc.)
4. **Validates trading hours** (configured per strategy)
5. **Fetches live data** from Capital.com
6. **Analyzes symbols** for trading signals
7. **Sends notifications** via Telegram (if configured)
8. **Logs results** to `live_logs/` directory

### Schedule

- **Frequency**: Every 5 minutes (configurable in bot_config.json for unified bot)
- **Trading Hours**: Configured per symbol/strategy
- **Weekend**: Automatic detection and skip

## Monitoring and Logs

### View Container Logs (Podman Compose)

```bash
# View logs from running unified bot
podman-compose logs unified-bot

# Follow logs in real-time
podman-compose logs -f unified-bot

# View last 100 lines
podman-compose logs --tail=100 unified-bot
```

### View Container Logs (Direct Podman)

```bash
# View logs from running container
podman logs mean-reversion-bot

# Follow logs in real-time
podman logs -f mean-reversion-bot
```

### Access Log Files

Log files are automatically created in the `live_logs/` directory:

- `scheduler.log` - Main application logs
- `strategy_log_YYYYMMDD.json` - Daily trading analysis results

### Container Health Check

```bash
# Using podman-compose
podman-compose ps

# Check if container is running (direct Docker)
podman ps | grep mean-reversion-bot

# Check container status
podman inspect mean-reversion-bot
```

## Stopping the Container

### Using Podman Compose (Recommended)

```bash
# Stop the unified bot
podman-compose stop unified-bot

# Remove the container (keeps image)
podman-compose down
```

### Direct Podman Commands

### Graceful Shutdown

```bash
# Stop the container gracefully (allows cleanup)
podman stop mean-reversion-bot
```

### Force Stop

```bash
# Force stop if needed
podman kill mean-reversion-bot
```

### Remove Container

```bash
# Remove stopped container
podman rm mean-reversion-bot
```

## Troubleshooting

### Common Issues

#### 1. "ImportError: attempted relative import with no known parent package"
```
ImportError: attempted relative import with no known parent package
```
**Solution**: This has been fixed in Dockerfile.bot. If you encounter this, rebuild the Podman image with `podman-compose build unified-bot`.

#### 2. "Configuration file not found"
```
ERROR: Configuration file not found: bot_config.json or results/best_configs_balanced.json
```
**Solution**: 
- **Unified bot**: Ensure `bot_config.json` exists in project root and is properly configured
- **Legacy bots**: Ensure the `results/` directory with optimized configurations is mounted or present
- See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md#configuration) for configuration details

#### 3. "Missing required environment variables"
```
ERROR: Missing required environment variables: CAPITAL_COM_API_KEY
```
**Solution**: Check your `.env` file or environment variable setup.

#### 4. "Capital.com connection failed"
```
ERROR: Capital.com connection failed: Authentication failed
```
**Solution**: Verify your Capital.com API credentials are correct and active.

#### 5. "Telegram bot initialization failed"
```
ERROR: Failed to initialize Telegram bot
```
**Solution**: Check your `TELEGRAM_BOT_TOKEN` or run without Telegram notifications.

### Debug Mode

To run with more verbose logging:

```bash
# Run with debug logging using podman-compose
podman-compose up unified-bot  # Remove -d flag to see logs

# Or run directly with Docker
podman run --rm \
  --env-file .env \
  -e PYTHONPATH=/app/src:/app \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/live_logs:/app/live_logs \
  -v $(pwd)/results:/app/results \
  mean-reversion-bot:latest
```

### Interactive Shell

To access the container for debugging:

```bash
# Using podman-compose
podman-compose exec unified-bot /bin/bash

# Or run interactive shell directly
podman run -it --rm \
  --env-file .env \
  -v $(pwd):/app \
  mean-reversion-bot:latest \
  /bin/bash
```

## Resource Requirements

### Minimum Requirements

- **CPU**: 1 core
- **Memory**: 512MB RAM
- **Storage**: 1GB for logs and cache
- **Network**: Internet access for API calls

### Recommended Requirements

- **CPU**: 2 cores
- **Memory**: 1GB RAM
- **Storage**: 5GB for extended logging
- **Network**: Stable internet connection

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Environment Files**: Keep `.env` files secure and local
3. **Network**: Consider running on private networks in production
4. **Updates**: Regularly update base images for security patches

## Production Deployment

For production deployment, consider:

1. **Use Unified Bot**: Use podman-compose with unified-bot service (see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md))
2. **Container Orchestration**: Use Podman Compose or Kubernetes
3. **Cloud Deployment**: See [AWS_ECS_DEPLOYMENT.md](AWS_ECS_DEPLOYMENT.md) for AWS setup
4. **Health Checks**: Implement health check endpoints (already configured in podman-compose.yml)
5. **Monitoring**: Set up alerting for container failures
6. **Backup**: Regular backup of logs and configurations
7. **Resource Limits**: Set appropriate CPU and memory limits

## Migration to Unified Bot

The unified bot (unified_bot.py) is the recommended approach for running trading strategies. It provides:

- **Parallel execution**: Run multiple strategies simultaneously
- **Shared infrastructure**: Single Telegram bot and signal cache
- **Better error handling**: One strategy failure doesn't stop others
- **Centralized configuration**: Single bot_config.json file
- **Improved monitoring**: Better logging and health checks

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for complete setup instructions and the migration guide section.

## Example Podman Compose (Legacy Reference)

> **Note**: Use the project's main podman-compose.yml file. This is for reference only.

For easier management, the project includes a podman-compose.yml file:

```yaml
version: '3.8'
services:
  mean-reversion-bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    container_name: mean-reversion-bot
    env_file: .env
    volumes:
      - ./live_logs:/app/live_logs
      - ./results:/app/results
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Then run with:

```bash
podman-compose up -d
podman-compose logs -f
```
