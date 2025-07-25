#!/bin/bash
# Submit AWS Batch jobs for forex major pairs
# Usage: ./submit_forex_jobs.sh [timeframe] [optimization_type]
# Example: ./submit_forex_jobs.sh 5m balanced

set -e

# Configuration
JOB_QUEUE="${BATCH_JOB_QUEUE:-mean-reversion-job-queue}"
JOB_DEFINITION="${BATCH_JOB_DEFINITION:-mean-reversion-optimization-fixed}"
TIMEFRAME="${1:-5m}"
OPTIMIZATION_TYPE="${2:-focused}"

# Array of forex symbols
SYMBOLS=("EURUSD=X" "GBPUSD=X" "USDJPY=X" "AUDUSD=X" "USDCAD=X" "USDCHF=X" "NZDUSD=X" "EURGBP=X" "EURJPY=X" "EURCHF=X" "GBPJPY=X" "BTCUSD=X" "ETHUSD=X" "GOLD=X" "SILVER=X")

echo "Submitting forex jobs with configuration:"
echo "  Job Queue: $JOB_QUEUE"
echo "  Job Definition: $JOB_DEFINITION"
echo "  Timeframe: $TIMEFRAME"
echo "  Optimization Type: $OPTIMIZATION_TYPE"
echo "  Symbols: ${SYMBOLS[*]}"
echo ""

# Track submitted jobs
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
JOB_LOG="forex_jobs_${TIMESTAMP}.csv"
echo "job_id,job_name,symbol,timeframe,optimization_type,submitted_at" > "$JOB_LOG"

# Submit jobs for each symbol
for SYMBOL in "${SYMBOLS[@]}"; do
  CLEAN_SYMBOL=$(echo "$SYMBOL" | sed 's/[^a-zA-Z0-9]/-/g')
  # Shorten job names to avoid AWS limits (128 char max)
  TIMESTAMP_SHORT=$(date +%m%d-%H%M)
  JOB_NAME="opt-${CLEAN_SYMBOL}-${OPTIMIZATION_TYPE}-${TIMESTAMP_SHORT}"
  
  echo "Submitting job for $SYMBOL..."
  
  RESULT=$(aws batch submit-job \
    --job-name "$JOB_NAME" \
    --job-queue "$JOB_QUEUE" \
    --job-definition "$JOB_DEFINITION" \
    --container-overrides '{
      "command": ["--grid-search", "'$OPTIMIZATION_TYPE'", "--symbol", "'$SYMBOL'", "--timeframe", "'$TIMEFRAME'", "--cache-transport", "s3", "--log-transport", "s3", "--quiet"]
    }' \
    --tags '{
      "Project": "MeanReversionStrategy",
      "Symbol": "'$SYMBOL'",
      "Timeframe": "'$TIMEFRAME'",
      "OptimizationType": "'$OPTIMIZATION_TYPE'"
    }')
  
  # Extract job ID
  JOB_ID=$(echo "$RESULT" | grep -o '"jobId": "[^"]*"' | sed 's/"jobId": "\([^"]*\)"/\1/')
  
  # Log job submission
  echo "$JOB_ID,$JOB_NAME,$SYMBOL,$TIMEFRAME,$OPTIMIZATION_TYPE,$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$JOB_LOG"
  
  echo "  ✓ Submitted: $JOB_NAME (ID: $JOB_ID)"
  sleep 1  # Small delay between submissions
done

echo ""
echo "✅ All forex jobs submitted successfully!"
echo "📊 Job tracking saved to: $JOB_LOG"
echo ""
echo "To monitor jobs, run:"
echo "  aws batch list-jobs --job-queue $JOB_QUEUE"