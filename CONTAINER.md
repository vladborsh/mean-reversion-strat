# Containerized Mean Reversion Strategy

This document provides instructions for running the mean reversion strategy optimization in a container using Podman.

## Prerequisites

- Podman installed on your system
- Basic knowledge of container operations

## Building the Container

You can build the container manually using:

```bash
podman build -t mean-reversion-strategy .
```

## Running Optimization

The container is set up to run the `optimize_strategy.py` script with any CLI arguments you provide.

### Basic Usage

```bash
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test
```

### Using the Helper Script

For convenience, a helper script is provided:

```bash
./run_optimization.sh --quick-test
```

### Examples

Run a quick test:
```bash
./run_optimization.sh --quick-test
```

Run a grid search with focused parameters:
```bash
./run_optimization.sh --grid-search focused --plot-equity-curves
```

Run random search with 50 iterations:
```bash
./run_optimization.sh --random-search 50 --sort-objective balanced
```

Custom symbol and timeframe:
```bash
./run_optimization.sh --quick-test --symbol GBPUSD=X --timeframe 1h
```

Or run directly with podman:
```bash
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --grid-search focused

# Run focused grid search with S3 transport (no volume mount needed)
podman run --rm mean-reversion-strategy --grid-search focused --symbol GBPUSD=X --timeframe 5m --cache-transport s3 --log-transport s3
```

## Output Files

All optimization results are saved to the `optimization` directory, which is mounted as a volume:

- `optimization/cache`: Cached data
- `optimization/results`: Optimization results
- `optimization/plots`: Generated plots
- `optimization/logs`: Log files
- `optimization/orders`: Order information

## Transport Layer Support

The container supports both local and S3 storage backends:

### Local Storage (Default)
When using local storage, mount the optimization directory as a volume:
```bash
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test
```

### S3 Storage
When using S3 transport, no volume mount is needed as all data is stored in the cloud:
```bash
# All data stored in S3 - no volume mount required
podman run --rm mean-reversion-strategy --grid-search focused --symbol GBPUSD=X --timeframe 5m --cache-transport s3 --log-transport s3
```

**S3 Benefits:**
- No local storage requirements
- Shared access across multiple environments
- Automatic backup and durability
- Ideal for CI/CD and cloud deployment

Make sure to configure AWS credentials through environment variables or AWS configuration files when using S3 transport.

## Note on Volumes

The Podman command mounts the local `optimization` directory to `/app/optimization` in the container. This ensures that:

1. All output files are saved to your local filesystem
2. Cached data can be reused between runs
3. Results can be easily accessed after the container exits

## Troubleshooting

If you encounter permission issues with output files, you may need to adjust the permissions in the container or on your local system.
