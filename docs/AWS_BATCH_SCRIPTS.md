# AWS Batch Job Management Scripts

This directory contains bash scripts for managing AWS Batch jobs for the mean reversion strategy optimization.

**Note**: Run all commands from the project root directory (`mean-reversion-strat/`).

## Scripts Overview

### Job Submission Scripts

#### `submit_forex_jobs.sh`
Submits optimization jobs for all major forex pairs.

**Usage:**
```bash
./scripts/submit_forex_jobs.sh [timeframe] [optimization_type]
```

**Examples:**
```bash
# Default: 5m timeframe, balanced optimization
./scripts/submit_forex_jobs.sh

# Custom timeframe and optimization
./scripts/submit_forex_jobs.sh 15m focused
./scripts/submit_forex_jobs.sh 1h risk
```

**Symbols covered:** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, EURGBP, EURJPY, EURCHF, GBPJPY, BTCUSD, ETHUSD, GOLD=X, SILVER=X

---

### Monitoring Scripts

#### `monitor_job_progress.py`
Monitors optimization job progress by reading status files from S3. Shows detailed progress bars and optimization metrics.

**Usage:**
```bash
./scripts/monitor_job_progress.py [job_id_or_tracking_file] [options]
```

**Examples:**
```bash
# Monitor single job progress
./scripts/monitor_job_progress.py abc123-def456-ghi789

# Follow progress in real-time
./scripts/monitor_job_progress.py abc123-def456-ghi789 --follow

# Monitor all jobs from tracking file with progress bars
./scripts/monitor_job_progress.py forex_jobs_20250724-161151.csv --follow

# Custom refresh interval (every 10 seconds)
./scripts/monitor_job_progress.py forex_jobs_20250724-161151.csv --follow --refresh 10

# Show progress once and exit
./scripts/monitor_job_progress.py forex_jobs_20250724-161151.csv --once
```

**Features:**
- Real-time status updates via S3 monitoring
- Progress bars for optimization jobs
- Color-coded output by job status
- Detailed metrics display
- Support for single jobs or entire job batches
- Automatic refresh capabilities

#### Using AWS CLI for Basic Monitoring
For basic monitoring, you can use AWS CLI commands directly:

**List jobs by status:**
```bash
# List running jobs
aws batch list-jobs --job-queue mean-reversion-job-queue --job-status RUNNING

# List failed jobs
aws batch list-jobs --job-queue mean-reversion-job-queue --job-status FAILED

# List completed jobs
aws batch list-jobs --job-queue mean-reversion-job-queue --job-status SUCCEEDED
```

**Monitor CloudWatch logs:**
```bash
# Tail logs for specific job
aws logs tail /aws/batch/job --follow

# View logs with time filters
aws logs tail /aws/batch/job --since 1h
```

---

## Configuration

### Environment Variables
Set these environment variables to customize job submission:

```bash
# Required (if different from defaults)
export BATCH_JOB_QUEUE="your-queue-name"           # Default: mean-reversion-job-queue
export BATCH_JOB_DEFINITION="your-job-definition"  # Default: mean-reversion-optimization-fixed

# AWS Configuration (if not using default AWS profile)
export AWS_PROFILE="your-profile"
export AWS_REGION="your-region"
```

### Job Tracking Files
Job submission scripts create CSV tracking files with format:
```
job_id,job_name,symbol,timeframe,optimization_type,submitted_at
abc123-def456,opt-EURUSD-X-balanced-20250724-161151,EURUSD,5m,balanced,2025-07-24T16:11:51Z
```

These files can be used with monitoring scripts to track job batches.

---

## Quick Start Guide

### 1. Prerequisites
- AWS CLI configured with appropriate permissions
- AWS Batch setup completed (see [AWS_BATCH_SETUP.md](AWS_BATCH_SETUP.md))
- Docker image built and pushed to ECR

### 2. Submit Jobs
```bash
# Default submission (5m timeframe, balanced optimization)
./scripts/submit_forex_jobs.sh

# Custom configuration
./scripts/submit_forex_jobs.sh 15m focused
```

### 3. Monitor Progress
```bash
# Monitor using the generated tracking file
./scripts/monitor_job_progress.py forex_jobs_20250724-161151.csv --follow

# Monitor specific job
./scripts/monitor_job_progress.py abc123-def456-ghi789
```

### 4. Check Results
Results are stored in:
- **S3**: `s3://your-bucket/mean-reversion-strat/optimization/results/`
- **Local**: `./optimization/results/` (if using local transport)

---

## Troubleshooting

### Common Issues

#### Jobs Stay in PENDING Status
- Check if compute environment is available
- Verify job queue is active
- Check AWS service limits

#### Jobs Fail Immediately
- Verify container image exists in ECR
- Check IAM permissions for job execution role
- Review CloudWatch logs for container startup errors

#### No Progress Updates
- Verify S3 bucket permissions for writing status files
- Check if transport layer is configured correctly
- Ensure job container has AWS credentials

### Debugging Commands
```bash
# Check job queue status
aws batch describe-job-queues --job-queues mean-reversion-job-queue

# Check compute environment
aws batch describe-compute-environments

# View recent job details
aws batch describe-jobs --jobs <job-id>

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/batch/job
```

### Getting Help
- Use `./scripts/aws_batch_help.sh` for quick command reference
- See [AWS_BATCH_SETUP.md](AWS_BATCH_SETUP.md) for detailed setup instructions
- Check [CONTAINER.md](../CONTAINER.md) for container-related issues

**Features:**
- Visual progress bars for each optimization job
- Real-time progress tracking from S3 status files
- Detailed optimization metrics (PnL, ratios, elapsed time)
- Overall progress summary for multiple jobs
- Automatic completion detection
- Color-coded status indicators
- Support for single jobs or job batches
- Estimated completion times

---

### Utility Scripts

#### `aws_batch_help.sh`
Shows overview of all available scripts and performs dependency checks.

**Usage:**
```bash
./scripts/aws_batch_help.sh
```

**Features:**
- Lists all available scripts with examples
- Checks AWS CLI installation and configuration
- Provides quick start instructions

---

## Environment Variables

All scripts support these optional environment variables:

- `BATCH_JOB_QUEUE`: Override default job queue (default: `mean-reversion-job-queue`)
- `BATCH_JOB_DEFINITION`: Override default job definition (default: `mean-reversion-optimization-fixed`)

**Example:**
```bash
export BATCH_JOB_QUEUE="my-custom-queue"
export BATCH_JOB_DEFINITION="my-custom-job-definition"
./scripts/submit_forex_jobs.sh
```

## Job Tracking

All submission scripts generate CSV tracking files with the format:
```
job_id,job_name,symbol,timeframe,optimization_type,submitted_at
```

These files are used by the monitoring script and can be analyzed later for job management.

## Prerequisites

1. **AWS CLI** installed and configured
2. **AWS Batch** infrastructure set up (see `AWS_BATCH_SETUP.md`)
3. **Container image** built and pushed to ECR
4. **Proper permissions** for AWS Batch, ECR, S3, and CloudWatch

## Quick Start

1. Set up AWS Batch infrastructure:
   ```bash
   # Follow the guide in AWS_BATCH_SETUP.md
   ```

2. Build and push container:
   ```bash
   # See container build instructions in AWS_BATCH_SETUP.md
   ```

3. Submit and monitor jobs:
   ```bash
   # Get help and overview
   ./scripts/aws_batch_help.sh
   
   # Submit forex optimization jobs
   ./scripts/submit_forex_jobs.sh
   
   # Monitor job status
   ./scripts/monitor_jobs.sh forex_jobs_*.csv
   
   # Monitor job progress with progress bars (recommended for optimization jobs)
   ./scripts/monitor_job_progress.sh forex_jobs_*.csv --follow
   
   # List running jobs
   ./scripts/list_jobs.sh --status RUNNING
   
   # Monitor job progress with detailed tracking
   ./scripts/monitor_job_progress.py forex_jobs_*.csv --follow
   ```

## Troubleshooting

### Common Issues

1. **Scripts not executable:**
   ```bash
   chmod +x scripts/*.sh
   ```

2. **AWS credentials not configured:**
   ```bash
   aws configure
   # or
   export AWS_PROFILE=your-profile
   ```

3. **Job queue or definition not found:**
   - Check AWS Batch console for correct names
   - Verify setup completed successfully
   - Use environment variables to override defaults

4. **Monitoring script can't find tracking file:**
   - Run monitoring script from same directory where you submitted jobs
   - Check file exists: `ls -la *.csv`

### Getting Help

- Run `./scripts/aws_batch_help.sh` for dependency checks
- Check AWS Batch console for job details
- Review CloudWatch logs for job execution details
- See main documentation: `AWS_BATCH_SETUP.md`
