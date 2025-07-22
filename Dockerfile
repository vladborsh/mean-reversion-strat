FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir matplotlib pandas numpy

# Copy the entire project
COPY . .

# Create directories for output data
RUN mkdir -p /app/optimization/cache /app/optimization/results /app/optimization/plots /app/optimization/logs /app/optimization/orders && \
    chmod -R 777 /app/optimization

# Set the entrypoint to run the optimization script
ENTRYPOINT ["python", "optimize_strategy.py"]

# Default command if no arguments provided
CMD ["--help"]
