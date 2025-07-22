# Containerization Guide

This document explains how to build and run the mean reversion strategy in a container using Podman.

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

### Other Examples
```bash
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --grid-search focused --plot-equity-curves
podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test --symbol GBPUSD=X --timeframe 1h
```

## Helper Script

A helper script `run_optimization.sh` is provided for convenience:

```bash
./run_optimization.sh --quick-test
./run_optimization.sh --grid-search balanced --plot-equity-curves
```

## Notes
- Use volume mounting to persist results and logs to your local machine.
- The container is automatically removed after execution with `--rm`.
- For troubleshooting, see the README or ask for help.
