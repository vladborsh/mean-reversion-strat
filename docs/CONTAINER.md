# Containerization Guide - Optimizer

> **Quick Links:**
> - **Live Trading Bot**: See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) (recommended for most users)
> - **AWS Cloud Deployment**: See [AWS_ECS_DEPLOYMENT.md](AWS_ECS_DEPLOYMENT.md) or [AWS_BATCH_SETUP.md](AWS_BATCH_SETUP.md)
> - **Legacy Bot Setup**: See [BOT_DOCKER_INSTRUCTIONS.md](BOT_DOCKER_INSTRUCTIONS.md)

This document explains how to build and run the **strategy optimizer** container for backtesting and hyperparameter optimization.

**Important Distinction:**
- `Dockerfile` → This file → Strategy optimizer (backtesting)
- `Dockerfile.bot` → See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) → Live trading bot

## Related Documentation

- **[Podman Deployment](DOCKER_DEPLOYMENT.md)** - Complete guide for live trading bot with podman-compose
- **[Transport Layer](TRANSPORT_LAYER.md)** - Storage backend configuration details
- **[Hyperparameter Optimization](HYPERPARAMETER_OPTIMIZATION.md)** - Optimization methods and parameters

## Building the Container

```bash
# Using podman-compose (recommended)
podman-compose --profile optimizer build optimizer

# Or build directly with Podman
podman build -t mean-reversion-strategy .
```

## Running the Container

### Using Podman Compose (Recommended)

```bash
# Run quick test
podman-compose --profile optimizer run --rm optimizer --quick-test

# Run with custom parameters
podman-compose --profile optimizer run --rm optimizer \
  --grid-search balanced --plot-equity-curves
```

### Direct Podman Commands

### Simple Run
```bash
podman run --rm mean-reversion-strategy --quick-test
```

### With Volume Mounting
```bash
podman run --rm \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --quick-test
```

### Transport Configuration

The container supports both local and S3 transport options via CLI arguments:

#### Local Storage (Default)
```bash
# All data stored locally within container/mounted volumes
podman run --rm \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --quick-test \
  --cache-transport local --log-transport local
```

#### S3 Storage
```bash
# Using S3 for both cache and logs (requires .env file with AWS credentials)
podman run --rm \
  --env-file .env \
  mean-reversion-strategy --quick-test \
  --cache-transport s3 --log-transport s3
```

#### Mixed Storage
```bash
# S3 cache with local logs (requires .env file with AWS credentials)
podman run --rm \
  --env-file .env \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --grid-search balanced \
  --cache-transport s3 --log-transport local
```

### Other Examples
```bash
# Grid search with equity curve plots and local storage
podman run --rm \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --grid-search focused \
  --plot-equity-curves --cache-transport local --log-transport local

# Custom symbol and timeframe with S3 cache
podman run --rm \
  --env-file .env \
  -v $(pwd)/optimization:/app/optimization \
  mean-reversion-strategy --quick-test \
  --symbol GBPUSD --timeframe 1h \
  --cache-transport s3 --log-transport local

# Random search optimization with S3 storage
podman run --rm \
  --env-file .env \
  mean-reversion-strategy --random-search 50 \
  --cache-transport s3 --log-transport s3
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
S3 transport options use AWS credentials from the `.env` file. Create a `.env` file with:

```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
```

Then mount it with `--env-file .env` when running the container.

### Best Practices
- **Development**: Use `--cache-transport local --log-transport local` with volume mounts
- **CI/CD**: Use `--cache-transport s3 --log-transport s3` for persistent storage
- **Hybrid**: Use `--cache-transport s3 --log-transport local` to share cache but keep results local

## Notes
- Use volume mounting (`-v`) to persist results and logs to your local machine when using local transport
- The container is automatically removed after execution with `--rm`
- AWS credentials for S3 transport are configured via the `.env` file mounted at runtime
- Transport configuration via CLI arguments provides more flexibility than environment variables
- For troubleshooting, see the README or [Transport Layer documentation](TRANSPORT_LAYER.md)
- For live trading bot deployment, see [Podman Deployment](DOCKER_DEPLOYMENT.md)
- This optimizer uses `Dockerfile`, while the live bot uses `Dockerfile.bot`
