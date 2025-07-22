#!/bin/bash
# run_optimization.sh
# Example script to run optimization in Podman container

# Set container engine to podman
CONTAINER_ENGINE="podman"

# Build the container
echo "Building simplified container using podman..."
if ! podman build -t mean-reversion-strategy .; then
    echo "Error building container. Please check your Dockerfile and try again."
    exit 1
fi
echo "Container built successfully!"

# Example commands
echo "
Example commands:

# Run quick test
podman run --rm -v \$(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test

# Run grid search with focused parameters
podman run --rm -v \$(pwd)/optimization:/app/optimization mean-reversion-strategy --grid-search focused --plot-equity-curves

# Run random search with 50 iterations
podman run --rm -v \$(pwd)/optimization:/app/optimization mean-reversion-strategy --random-search 50 --sort-objective balanced

# Custom symbol and timeframe
podman run --rm -v \$(pwd)/optimization:/app/optimization mean-reversion-strategy --quick-test --symbol GBPUSD=X --timeframe 1h
"

# Execute the command if provided
if [ $# -gt 0 ]; then
    echo "Running optimization with arguments: $@"
    
    # Make sure the optimization directory exists
    mkdir -p $(pwd)/optimization/{cache,results,plots,logs,orders}
    
    # Run the container with volume mounting
    if ! podman run --rm -v $(pwd)/optimization:/app/optimization mean-reversion-strategy "$@"; then
        echo "Error running container. Please check your arguments and try again."
        exit 1
    fi
fi
