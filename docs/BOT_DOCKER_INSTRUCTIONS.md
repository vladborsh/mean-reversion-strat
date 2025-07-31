# Strategy Scheduler and Bot Podman Instructions

This document provides instructions for building and running the Podman container for the Mean Reversion Strategy Scheduler with Telegram Bot integration.

## Related Documentation

- **[Telegram Bot Integration](TELEGRAM_BOT_INTEGRATION.md)** - Complete guide to setting up and using the Telegram bot
- **[Container Documentation](CONTAINER.md)** - General container usage and deployment
- **[Strategy Documentation](STRATEGY_DOCUMENTATION.md)** - Core strategy implementation details

## Prerequisites

Before building and running the container, ensure you have:

1. **Podman installed** on your system
2. **Environment variables** configured (see Environment Setup below)
3. **Configuration files** in place:
   - `results/best_configs_balanced.json` (optimized strategy parameters)
   - `.env` file with required API credentials

## Environment Setup

Create a `.env` file in the project root with the following required variables:

```bash
# Capital.com API credentials (required for data fetching)
CAPITAL_COM_API_KEY=your_api_key_here
CAPITAL_COM_PASSWORD=your_password_here
CAPITAL_COM_IDENTIFIER=your_identifier_here

# Telegram Bot Token (optional, for notifications)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

## Build Instructions

### Build the Podman Image

```bash
# Navigate to the project root directory
cd /path/to/mean-reversion-strat

# Build the Podman image for the bot
podman build -f Dockerfile.bot -t mean-reversion-bot:latest .
```

### Verify the Build

```bash
# Check that the image was created successfully
podman images | grep mean-reversion-bot
```

## Run Instructions

### Basic Run (with .env file)

```bash
# Run the container with environment file
podman run --rm \
  --env-file .env \
  -v $(pwd)/live_logs:/app/live_logs \
  -v $(pwd)/results:/app/results \
  mean-reversion-bot:latest
```

### Run with Environment Variables

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

### Run in Background (Detached Mode)

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

### Run without Telegram (Data Analysis Only)

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
- **`results:/app/results`**: Access to optimized strategy configurations

## Container Behavior

### What the Container Does

1. **Initializes** the live strategy scheduler
2. **Loads** optimized configurations from `results/best_configs_balanced.json`
3. **Runs analysis cycles** every 5 minutes (:00, :05, :10, etc.)
4. **Validates trading hours** (6:00-17:00 UTC)
5. **Fetches live data** from Capital.com
6. **Analyzes symbols** for trading signals
7. **Sends notifications** via Telegram (if configured)
8. **Logs results** to `live_logs/` directory

### Schedule

- **Frequency**: Every 5 minutes
- **Trading Hours**: 6:00 AM - 5:00 PM UTC
- **Weekend**: No trading (automatic detection)

## Monitoring and Logs

### View Container Logs

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
# Check if container is running
podman ps | grep mean-reversion-bot

# Check container status
podman inspect mean-reversion-bot
```

## Stopping the Container

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
**Solution**: This has been fixed in the Dockerfile by using a launcher script (`run_bot.py`) that properly sets up the Python path for relative imports. If you encounter this, rebuild the Podman image.

#### 2. "Configuration file not found"
```
ERROR: Configuration file not found: results/best_configs_balanced.json
```
**Solution**: Ensure the `results/` directory with optimized configurations is mounted or present.

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
# Run with debug logging
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
# Run interactive shell
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

1. **Container Orchestration**: Use Podman Compose or Kubernetes
2. **Health Checks**: Implement health check endpoints
3. **Monitoring**: Set up alerting for container failures
4. **Backup**: Regular backup of logs and configurations
5. **Resource Limits**: Set appropriate CPU and memory limits

## Example Podman Compose

For easier management, you can use Podman Compose:

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
