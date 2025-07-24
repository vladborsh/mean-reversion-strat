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

**Symbols covered:** EURUSD=X, GBPUSD=X, USDJPY=X, AUDUSD=X, USDCAD=X, USDCHF=X

---

### Monitoring Scripts

#### `monitor_jobs.sh`
Monitors job status in real-time with automatic completion detection.

**Usage:**
```bash
./scripts/monitor_jobs.sh [job_tracking_file.csv]
```

**Examples:**
```bash
# Monitor specific job batch
./scripts/monitor_jobs.sh forex_jobs_20250724-161151.csv

# List available tracking files if none specified
./scripts/monitor_jobs.sh
```

**Features:**
- Real-time status updates every 30 seconds
- Automatic completion detection
- Clear display of job counts by status
- Shows running and failed jobs
- Auto-stops when all jobs complete

#### `list_jobs.sh`
Lists and finds AWS Batch jobs with filtering options.

**Usage:**
```bash
./scripts/list_jobs.sh [options]
```

**Examples:**
```bash
# List recent running jobs
./scripts/list_jobs.sh --status RUNNING

# Find jobs for specific symbol
./scripts/list_jobs.sh --symbol "EURUSD=X"

# Show only jobs with logs available
./scripts/list_jobs.sh --with-logs

# List failed jobs for debugging
./scripts/list_jobs.sh --status FAILED --recent 5
```

**Features:**
- Filter by job status, symbol, timeframe
- Show logs availability indicator
- Color-coded output by job status
- Integration with log monitoring script

#### `monitor_job_logs.sh`
Monitors job logs in real-time with advanced filtering and following capabilities.

**Usage:**
```bash
./scripts/monitor_job_logs.sh [job_id_or_tracking_file] [options]
```

**Examples:**
```bash
# Monitor single job logs
./scripts/monitor_job_logs.sh abc123-def456-ghi789

# Follow logs in real-time
./scripts/monitor_job_logs.sh abc123-def456-ghi789 --follow

# Show last 100 lines and follow
./scripts/monitor_job_logs.sh abc123-def456-ghi789 --tail 100 --follow

# Monitor all jobs from tracking file
./scripts/monitor_job_logs.sh forex_jobs_20250724-161151.csv --follow

# Filter for errors only
./scripts/monitor_job_logs.sh abc123-def456-ghi789 --filter "ERROR|FAIL|Exception"

# Show logs from last hour
./scripts/monitor_job_logs.sh abc123-def456-ghi789 --since 1h
```

**Features:**
- Real-time log following (like `tail -f`)
- Color-coded log output (errors in red, warnings in yellow, etc.)
- Log filtering with regex patterns
- Time-based log filtering
- Support for single jobs or entire job batches
- Automatic log stream detection
- Graceful handling of jobs without logs

#### `monitor_job_progress.sh`
Monitors optimization job progress by reading status files from S3 instead of CloudWatch logs. Shows detailed progress bars and optimization metrics.

**Usage:**
```bash
./scripts/monitor_job_progress.sh [job_id_or_tracking_file] [options]
```

**Examples:**
```bash
# Monitor single job progress
./scripts/monitor_job_progress.sh abc123-def456-ghi789

# Follow progress in real-time
./scripts/monitor_job_progress.sh abc123-def456-ghi789 --follow

# Monitor all jobs from tracking file with progress bars
./scripts/monitor_job_progress.sh forex_jobs_20250724-161151.csv --follow

# Custom refresh interval (every 10 seconds)
./scripts/monitor_job_progress.sh forex_jobs_20250724-161151.csv --follow --refresh 10

# Show progress once and exit
./scripts/monitor_job_progress.sh forex_jobs_20250724-161151.csv --once
```

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
   
   # Monitor job logs in real-time (for debugging)
   ./scripts/monitor_job_logs.sh <job-id> --follow
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
