# Containerization Guide

This document explains how to build and run the mean reversion strategy in a container using Podman.

## Related Documentation

- **[Bot Docker Instructions](BOT_DOCKER_INSTRUCTIONS.md)** - Container deployment for the live trading bot
- **[Telegram Bot Integration](TELEGRAM_BOT_INTEGRATION.md)** - Live trading with Telegram notifications
- **[Transport Layer](TRANSPORT_LAYER.md)** - Storage backend configuration details

## Building the Container

```bash
podman build -t mean-reversion-strategy .
```

## Running the Container

### Simple Run
```bash
podman run mean-reversion-strategy --quick-test
```

### With Volume Mounting
```bash
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test
```

### Transport Configuration

The container supports both local and S3 transport options via CLI arguments:

#### Local Storage (Default)
```bash
# All data stored locally within container/mounted volumes
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test --cache-transport local --log-transport local
```

#### S3 Storage
```bash
# Using S3 for both cache and logs (uses .env file for AWS credentials)
podman run --rm mean-reversion-strategy --quick-test --cache-transport s3 --log-transport s3
```

#### Mixed Storage
```bash
# S3 cache with local logs (uses .env file for AWS credentials)
podman run --rm \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --grid-search balanced --cache-transport s3 --log-transport local
```

### Other Examples
```bash
# Grid search with equity curve plots and local storage
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --grid-search focused --plot-equity-curves --cache-transport local --log-transport local

# Custom symbol and timeframe with S3 cache (uses .env file for AWS credentials)
podman run --rm \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --quick-test --symbol GBPUSD --timeframe 1h --cache-transport s3 --log-transport local

# Random search optimization with S3 storage (uses .env file for AWS credentials)
podman run --rm mean-reversion-strategy --random-search 50 --cache-transport s3 --log-transport s3
```

## Helper Script

A helper script `run_optimization.sh` is provided for convenience:

```bash
# Basic usage (local storage)
./run_optimization.sh --quick-test
./run_optimization.sh --grid-search balanced --plot-equity-curves

# With transport configuration
./run_optimization.sh --quick-test --cache-transport s3 --log-transport local
./run_optimization.sh --grid-search balanced --cache-transport s3 --log-transport s3
```

## Transport Configuration Details

### Cache Transport Options
- `--cache-transport local`: Store data cache in container/mounted volume
- `--cache-transport s3`: Store data cache in AWS S3 bucket

### Log Transport Options  
- `--log-transport local`: Store optimization results in container/mounted volume
- `--log-transport s3`: Store optimization results in AWS S3 bucket

### AWS Configuration
S3 transport options use AWS credentials from the `.env` file that is included during container build. No additional environment variables need to be passed to the container.

### Best Practices
- **Development**: Use `--cache-transport local --log-transport local` with volume mounts
- **CI/CD**: Use `--cache-transport s3 --log-transport s3` for persistent storage
- **Hybrid**: Use `--cache-transport s3 --log-transport local` to share cache but keep results local

## Notes
- Use volume mounting (`-v`) to persist results and logs to your local machine when using local transport
- The container is automatically removed after execution with `--rm`
- AWS credentials for S3 transport are configured via the `.env` file during container build
- Transport configuration via CLI arguments provides more flexibility than environment variables
- For troubleshooting, see the README or [Transport Layer documentation](TRANSPORT_LAYER.md)
- For live trading bot deployment, see [Bot Docker Instructions](BOT_DOCKER_INSTRUCTIONS.md)
