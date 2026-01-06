# AWS Batch Setup Guide Using AWS Console

This guide provides step-by-step instructions for setting up AWS Batch using the AWS Console UI to run mean reversion optimization jobs across multiple symbols.

> **Related Documentation:**
> - [Hyperparameter Optimization](HYPERPARAMETER_OPTIMIZATION.md) - Optimization methods and configurations
> - [AWS Batch Scripts](AWS_BATCH_SCRIPTS.md) - Job submission and monitoring scripts
> - [Post-Processing & Results Analysis](POST_PROCESSING.md) - Analyzing batch optimization results

## Prerequisites

1. AWS account with appropriate permissions
2. Podman installed for container building
3. Basic understanding of AWS services

## Required AWS Permissions

Your AWS user/role needs the following managed policies:
- `AWSBatchFullAccess` - Full access to AWS Batch
- `AmazonECS_FullAccess` - ECS for container management
- `EC2FullAccess` - For compute environments
- `IAMFullAccess` - To create and manage roles
- `AmazonEC2ContainerRegistryFullAccess` - For ECR
- `AmazonS3FullAccess` - For results storage
- `CloudWatchFullAccess` - For logging

## Step 1: Create IAM Roles Using AWS Console

### 1.1 Create Batch Service Role

1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **Batch** → **Next**
3. The policy `AWSBatchServiceRole` should be automatically selected → **Next**
4. **Role name**: `AWSBatchServiceRole`
5. **Description**: `Service role for AWS Batch`
6. Click **Create role**

### 1.2 Create EC2 Instance Role

1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **EC2** → **Next**
3. Search and select `AmazonEC2ContainerServiceforEC2Role` → **Next**
4. **Role name**: `ecsInstanceRole`
5. **Description**: `Instance role for ECS instances in Batch`
6. Click **Create role**

### 1.3 Create Job Execution Role

1. Go to **IAM Console** → **Roles** → **Create role**
2. Select **AWS service** → **Elastic Container Service** → **Elastic Container Service Task** → **Next**
3. Click **Create policy** (opens in new tab):
   - **Service**: S3
   - **Actions**: `GetObject`, `PutObject`, `DeleteObject`, `ListBucket`
   - **Resources**: 
     - **bucket**: `arn:aws:s3:::your-optimization-bucket-name`
     - **object**: `arn:aws:s3:::your-optimization-bucket-name/*`
   - Add another statement:
     - **Service**: CloudWatch Logs
     - **Actions**: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`
     - **Resources**: `*`
   - **Name**: `MeanReversionJobExecutionPolicy`
   - Click **Create policy**
4. Back to role creation, refresh and select `MeanReversionJobExecutionPolicy` → **Next**
5. **Role name**: `MeanReversionJobExecutionRole`
6. **Description**: `Execution role for mean reversion batch jobs`
7. Click **Create role**

## Step 2: Create S3 Bucket Using AWS Console

1. Go to **S3 Console** → **Create bucket**
2. **Bucket name**: `your-optimization-bucket-name` (must be globally unique)
3. **Region**: Choose your preferred region (e.g., us-east-1)
4. Leave other settings as default → **Create bucket**
5. After creation, go to the bucket → **Management** tab → **Lifecycle rules**
6. **Create lifecycle rule**:
   - **Rule name**: `DeleteOldOptimizationResults`
   - **Rule scope**: Apply to all objects
   - **Lifecycle rule actions**: ✅ Expire current versions of objects
   - **Days after object creation**: `30`
   - **Create rule**

## Step 3: Create ECR Repository Using AWS Console

1. Go to **ECR Console** → **Repositories** → **Create repository**
2. **Repository name**: `mean-reversion-strategy`
3. **Tag immutability**: Disabled
4. **Scan on push**: Enabled (optional)
5. **Encryption**: AES-256
6. **Create repository**
7. **Copy the Repository URI** (you'll need this later)

## Step 4: Create Security Group Using AWS Console

1. Go to **EC2 Console** → **Security Groups** → **Create security group**
2. **Security group name**: `mean-reversion-batch-sg`
3. **Description**: `Security group for mean reversion batch jobs`
4. **VPC**: Select your default VPC
5. **Outbound rules**: 
   - **Type**: All traffic
   - **Protocol**: All
   - **Port range**: All
   - **Destination**: 0.0.0.0/0
6. **Create security group**

## Step 5: Create Compute Environment Using AWS Console

1. Go to **Batch Console** → **Compute environments** → **Create**
2. **Select orchestration type**: Amazon Elastic Compute Cloud (EC2)
3. **Compute environment configuration**:
   - **Name**: `mean-reversion-compute-env`
   - **Service role**: Select `AWSBatchServiceRole`
4. **Instance configuration**:
   - **Provisioning model**: On-Demand
   - **Allowed instance types**: `c5.large`, `c5.xlarge`, `c5.2xlarge`
   - **Minimum vCPUs**: `0`
   - **Maximum vCPUs**: `100`
   - **Desired vCPUs**: `0`
5. **Networking**:
   - **VPC**: Select your default VPC
   - **Subnets**: Select all available subnets
   - **Security groups**: Select `mean-reversion-batch-sg`
6. **Instance role**: `ecsInstanceRole`
7. **Tags**: 
   - **Key**: `Project`, **Value**: `MeanReversionStrategy`
8. **Create compute environment**

## Step 6: Create Job Queue Using AWS Console

1. Go to **Batch Console** → **Job queues** → **Create**
2. **General configuration**:
   - **Name**: `mean-reversion-job-queue`
   - **Priority**: `1`
   - **State**: Enabled
3. **Connected compute environments**:
   - **Select compute environments**: `mean-reversion-compute-env`
   - **Order**: `1`
4. **Create job queue**

## Step 7: Create Job Definition Using AWS Console

1. Go to **Batch Console** → **Job definitions** → **Create**
2. **General configuration**:
   - **Name**: `mean-reversion-optimization-fixed`
   - **Platform type**: EC2
3. **Container configuration**:
   - **Image**: `[YOUR-ACCOUNT-ID].dkr.ecr.[REGION].amazonaws.com/mean-reversion-strategy:latest`
     - Replace `[YOUR-ACCOUNT-ID]` with your AWS account ID
     - Replace `[REGION]` with your region (e.g., us-east-1)
   - **vCPUs**: `2`
   - **Memory**: `4096` MiB
   - **Job role**: Select `MeanReversionJobExecutionRole`
4. **Environment variables**:
   - **Name**: `AWS_DEFAULT_REGION`, **Value**: `us-east-1` (or your region)
5. **Job timeout**:
   - **Timeout**: `14400` seconds (4 hours)
6. **Retry strategy**:
   - **Job attempts**: `2`
7. **Create job definition**

## Step 8: Verify Setup Using AWS Console

### 8.1 Check Compute Environment Status
1. Go to **Batch Console** → **Compute environments**
2. Find `mean-reversion-compute-env`
3. **Status** should show `VALID` and **State** should show `ENABLED`

### 8.2 Check Job Queue Status
1. Go to **Batch Console** → **Job queues**
2. Find `mean-reversion-job-queue`
3. **State** should show `ENABLED`
4. **Connected compute environments** should show `mean-reversion-compute-env`

### 8.3 Check Job Definition
1. Go to **Batch Console** → **Job definitions**
2. Find `mean-reversion-optimization-fixed`
3. Click on it to see the configuration details
4. Verify the container image URI is correct

### 8.4 Check ECR Repository
1. Go to **ECR Console** → **Repositories**
2. Find `mean-reversion-strategy`
3. Note the **Repository URI** for container builds

## Building and Pushing Container to ECR

Before you can run jobs, you need to build and push your container image to ECR:

### Step 1: Get AWS Account Information
```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Set your preferred region
AWS_REGION="us-east-1"
```

### Step 2: Login to ECR
```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | podman login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

### Step 3: Build and Push Container
```bash
# Navigate to your project directory
cd /path/to/mean-reversion-strat

# Build the container
podman build -t mean-reversion-strategy:latest .

# Tag for ECR
podman tag mean-reversion-strategy:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mean-reversion-strategy:latest

# Push to ECR
podman push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mean-reversion-strategy:latest

echo "Container image: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mean-reversion-strategy:latest"
```

## Submitting Jobs Using AWS CLI

### 🚀 Quick Start with Scripts

For ease of use, we provide ready-to-use bash scripts in the `scripts/` directory.

**📖 For detailed script documentation, see [AWS_BATCH_SCRIPTS.md](AWS_BATCH_SCRIPTS.md)**

```bash
# View all available scripts and their usage
./scripts/aws_batch_help.sh

# Submit forex jobs with default settings
./scripts/submit_forex_jobs.sh

# Submit jobs for all major forex pairs with default settings
./scripts/submit_forex_jobs.sh

# Monitor job progress
./scripts/monitor_jobs.sh forex_jobs_*.csv
```

### Single Job Submission
```bash
# Submit a test job
# Note: Since Dockerfile has ENTRYPOINT ["python", "optimize_strategy.py"], 
# only specify the arguments in the command array
aws batch submit-job \
  --job-name "test-optimization-EURUSD-$(date +%Y%m%d-%H%M%S)" \
  --job-queue "mean-reversion-job-queue" \
  --job-definition "mean-reversion-optimization-fixed" \
  --container-overrides '{
    "command": ["--grid-search", "focused", "--symbol", "EURUSD", "--timeframe", "5m", "--cache-transport", "s3", "--log-transport", "s3", "--quiet"]
  }' \
  --tags '{
    "Project": "MeanReversionStrategy",
    "Symbol": "EURUSD"
  }'
```

### Submit Multiple Jobs for Different Symbols

#### Forex Major Pairs

Use the provided script to submit jobs for all major forex pairs:

```bash
# Submit jobs for all forex major pairs with default settings (5m timeframe, balanced optimization)
./scripts/submit_forex_jobs.sh

# Submit with custom timeframe and optimization type
./scripts/submit_forex_jobs.sh 15m focused

# Submit with 1-hour timeframe and risk optimization
./scripts/submit_forex_jobs.sh 1h risk
```

**Script location**: `scripts/submit_forex_jobs.sh`

**Usage**: `./scripts/submit_forex_jobs.sh [timeframe] [optimization_type]`

**Environment variables**:
- `BATCH_JOB_QUEUE`: Override default job queue (default: mean-reversion-job-queue)
- `BATCH_JOB_DEFINITION`: Override default job definition (default: mean-reversion-optimization-fixed)

#### Comprehensive Multi-Symbol Batch
```bash
#!/bin/bash
# Comprehensive batch job submission script

# Configuration
SYMBOLS=("EURUSD" "GBPUSD" "USDJPY" "AUDUSD" "BTC/USDT" "ETH/USDT")
TIMEFRAMES=("15m" "1h")
OPTIMIZATION_TYPES=("balanced" "focused")
JOB_QUEUE="mean-reversion-job-queue"
JOB_DEFINITION="mean-reversion-optimization-fixed"

# Track submitted jobs
echo "job_id,job_name,symbol,timeframe,optimization_type,submitted_at" > batch_jobs.csv

# Submit jobs
for SYMBOL in "${SYMBOLS[@]}"; do
  for TIMEFRAME in "${TIMEFRAMES[@]}"; do
    for OPT_TYPE in "${OPTIMIZATION_TYPES[@]}"; do
      # Clean symbol for job name
      CLEAN_SYMBOL=$(echo "$SYMBOL" | sed 's/[^a-zA-Z0-9]/-/g')
      JOB_NAME="opt-${CLEAN_SYMBOL}-${TIMEFRAME}-${OPT_TYPE}-$(date +%Y%m%d-%H%M%S)"
      
      # Submit job
      RESULT=$(aws batch submit-job \
        --job-name "$JOB_NAME" \
        --job-queue "$JOB_QUEUE" \
        --job-definition "$JOB_DEFINITION" \
        --container-overrides '{
          "command": ["--grid-search", "'$OPT_TYPE'", "--symbol", "'$SYMBOL'", "--timeframe", "'$TIMEFRAME'", "--years", "2", "--cache-transport", "s3", "--log-transport", "s3", "--quiet"]
        }' \
        --tags '{
          "Project": "MeanReversionStrategy",
          "Symbol": "'$SYMBOL'",
          "Timeframe": "'$TIMEFRAME'",
          "OptimizationType": "'$OPT_TYPE'"
        }')
      
      # Extract job ID
      JOB_ID=$(echo "$RESULT" | grep -o '"jobId": "[^"]*"' | sed 's/"jobId": "\([^"]*\)"/\1/')
      
      # Log job submission
      echo "$JOB_ID,$JOB_NAME,$SYMBOL,$TIMEFRAME,$OPT_TYPE,$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> batch_jobs.csv
      
      echo "Submitted: $JOB_NAME (ID: $JOB_ID)"
      sleep 1  # Small delay between submissions
    done
  done
done

echo "All jobs submitted. Tracking saved to batch_jobs.csv"
```

## Monitoring Jobs Using AWS CLI

### Quick Monitoring with Script

The easiest way to monitor your submitted jobs is using the provided monitoring script:

```bash
# Monitor jobs using the tracking file generated by the submission scripts
./scripts/monitor_jobs.sh forex_jobs_20250724-161151.csv

# The script will show real-time status updates and automatically detect completion
```

**Script location**: `scripts/monitor_jobs.sh`

**Usage**: `./scripts/monitor_jobs.sh [job_tracking_file.csv]`

**Features**:
- Real-time status updates every 30 seconds
- Automatic completion detection
- Clear display of job counts by status
- Shows running and failed jobs
- Auto-stops when all jobs complete

### Manual Job Status Checks
```bash
# List all jobs in the queue
aws batch list-jobs --job-queue mean-reversion-job-queue

# Get detailed status of specific jobs (using job IDs from batch_jobs.csv)
JOB_IDS=$(cut -d, -f1 batch_jobs.csv | tail -n +2 | tr '\n' ' ')
aws batch describe-jobs --jobs $JOB_IDS

# Check jobs by status
aws batch list-jobs --job-queue mean-reversion-job-queue --job-status RUNNING
aws batch list-jobs --job-queue mean-reversion-job-queue --job-status SUCCEEDED
aws batch list-jobs --job-queue mean-reversion-job-queue --job-status FAILED
```

### Monitor Jobs with a Simple Script
```bash
#!/bin/bash
# Simple job monitoring script

if [ ! -f "batch_jobs.csv" ]; then
  echo "batch_jobs.csv not found. Submit jobs first."
  exit 1
fi

# Get job IDs from tracking file
JOB_IDS=$(cut -d, -f1 batch_jobs.csv | tail -n +2 | paste -sd ' ')

echo "Monitoring $(wc -l < batch_jobs.csv | tr -d ' ') jobs..."
echo "=================================="

while true; do
  # Get job statuses
  JOBS_DATA=$(aws batch describe-jobs --jobs $JOB_IDS --query 'jobs[*].[jobId,jobName,status]' --output text)
  
  # Count by status
  SUBMITTED=$(echo "$JOBS_DATA" | grep -c "SUBMITTED" || echo 0)
  PENDING=$(echo "$JOBS_DATA" | grep -c "PENDING" || echo 0)
  RUNNABLE=$(echo "$JOBS_DATA" | grep -c "RUNNABLE" || echo 0)
  STARTING=$(echo "$JOBS_DATA" | grep -c "STARTING" || echo 0)
  RUNNING=$(echo "$JOBS_DATA" | grep -c "RUNNING" || echo 0)
  SUCCEEDED=$(echo "$JOBS_DATA" | grep -c "SUCCEEDED" || echo 0)
  FAILED=$(echo "$JOBS_DATA" | grep -c "FAILED" || echo 0)
  
  # Clear screen and show status
  clear
  echo "Job Status Monitor - $(date)"
  echo "=================================="
  echo "SUBMITTED  : $SUBMITTED"
  echo "PENDING    : $PENDING"
  echo "RUNNABLE   : $RUNNABLE"
  echo "STARTING   : $STARTING"
  echo "RUNNING    : $RUNNING"
  echo "SUCCEEDED  : $SUCCEEDED"
  echo "FAILED     : $FAILED"
  echo "=================================="
  
  # Show failed jobs
  if [ $FAILED -gt 0 ]; then
    echo "FAILED JOBS:"
    echo "$JOBS_DATA" | grep "FAILED" | cut -f2
    echo "=================================="
  fi
  
  # Check if all jobs are complete
  ACTIVE=$((SUBMITTED + PENDING + RUNNABLE + STARTING + RUNNING))
  if [ $ACTIVE -eq 0 ]; then
    echo "🎉 All jobs completed!"
    break
  fi
  
  echo "Press Ctrl+C to stop monitoring..."
  sleep 30
done
```

### View Job Logs
```bash
# Get logs for a specific job (replace JOB_ID with actual job ID)
JOB_ID="your-job-id-here"

# Get job details including log stream
aws batch describe-jobs \
  --jobs $JOB_ID \
  --region your-region

# Get the log stream name from job details
LOG_STREAM_NAME=$(aws batch describe-jobs \
  --jobs $JOB_ID \
  --region your-region \
  --query "jobs[0].attempts[0].taskProperties.logStreamName" \
  --output text)

# View logs in CloudWatch
if [ "$LOG_STREAM_NAME" != "null" ]; then
  aws logs get-log-events \
    --log-group-name /aws/batch/job \
    --log-stream-name $LOG_STREAM_NAME \
    --region your-region \
    --output text
else
  echo "Job not started yet or logs not available"
fi

# Follow logs in real-time (if job is still running)
aws logs tail /aws/batch/job \
  --log-stream-names $LOG_STREAM_NAME \
  --region your-region \
  --follow
```

### Complete Log Monitoring Script
```bash
#!/bin/bash
# Complete job log monitoring script

JOB_ID="your-job-id-here"
REGION="your-region"

echo "Monitoring job: $JOB_ID"

while true; do
  # Get job status
  STATUS=$(aws batch describe-jobs --jobs $JOB_ID --region $REGION --query "jobs[0].status" --output text)
  echo "Job Status: $STATUS"
  
  # Try to get logs if available
  LOG_STREAM=$(aws batch describe-jobs --jobs $JOB_ID --region $REGION --query "jobs[0].attempts[0].taskProperties.logStreamName" --output text 2>/dev/null)
  
  if [ "$LOG_STREAM" != "None" ] && [ "$LOG_STREAM" != "" ] && [ "$LOG_STREAM" != "null" ]; then
    echo "=== LATEST LOGS ==="
    aws logs get-log-events \
      --log-group-name /aws/batch/job \
      --log-stream-name $LOG_STREAM \
      --region $REGION \
      --start-from-head \
      --output text \
      --query "events[*].[timestamp,message]" | tail -20
    echo "==================="
  fi
  
  # Exit if job is complete
  if [ "$STATUS" = "SUCCEEDED" ] || [ "$STATUS" = "FAILED" ]; then
    echo "Job completed with status: $STATUS"
    break
  fi
  
  sleep 10
done
```

### Get Failed Job Details
```bash
# Get details of failed jobs
aws batch list-jobs \
  --job-queue mean-reversion-job-queue \
  --job-status FAILED \
  --query 'jobList[*].[jobName,statusReason]' \
  --output table

# Get detailed failure information
FAILED_JOB_IDS=$(aws batch list-jobs --job-queue mean-reversion-job-queue --job-status FAILED --query 'jobList[*].jobId' --output text)

if [ ! -z "$FAILED_JOB_IDS" ]; then
  aws batch describe-jobs --jobs $FAILED_JOB_IDS \
    --query 'jobs[*].[jobName,statusReason,attempts[-1].exitCode]' \
    --output table
fi
```

## Results Collection and Aggregation

Since you're using S3 transport, your results will be automatically stored in your S3 bucket under:
- **Cache**: `s3://your-bucket/mean-reversion-strat/cache/`
- **Results**: `s3://your-bucket/mean-reversion-strat/optimization/results/`
- **Logs**: `s3://your-bucket/mean-reversion-strat/optimization/logs/`

### Quick Download

```bash
# Create local results directory
mkdir -p batch-results

# Download all optimization results
aws s3 sync s3://your-optimization-bucket/mean-reversion-strat/optimization/results/ ./batch-results/

# List downloaded files
ls -la batch-results/
```

### Comprehensive Analysis

For complete instructions on analyzing batch results, generating PNL charts, and comparing optimization objectives, see:

**📖 [Post-Processing and Results Analysis](POST_PROCESSING.md)**

The post-processing guide includes:
- Downloading and aggregating AWS Batch results
- Analyzing optimization results by symbol and objective
- Generating equity curve visualizations
- Comparing different optimization strategies
- Python scripts for automated analysis
- Troubleshooting common issues

**Quick Start:**
```bash
# 1. Download results from S3
aws s3 sync s3://your-bucket/mean-reversion-strat/optimization/results/ ./batch-results/

# 2. Analyze and generate best configs
python3 post-processing/analyze_batch_results.py \
    --results-dir batch-results \
    --output-dir results

# 3. Generate PNL charts
python3 post-processing/generate_config_pnl.py \
    --config-file results/best_configs_balanced.json

# See POST_PROCESSING.md for complete workflow
```

## Notes and Best Practices

- **Container Updates**: After updating your code, rebuild and push the container with a new tag, then update the job definition
- **Cost Optimization**: The compute environment automatically scales from 0 to 100 vCPUs, so you only pay for what you use
- **Job Parallelization**: You can run multiple symbols simultaneously - AWS Batch will distribute them across available compute resources
- **Monitoring**: Use CloudWatch logs and the Batch console to monitor job progress and debug issues
- **Resource Limits**: Each job uses 2 vCPUs and 4GB memory - adjust in the job definition if needed
- **Timeout**: Jobs will timeout after 4 hours - increase if your optimizations take longer
- **Storage**: Results are stored in S3 with a 30-day lifecycle policy to control costs

## Troubleshooting

### Common Issues
1. **Job stays in RUNNABLE state**: Check compute environment has available capacity and proper networking
2. **Job fails immediately**: Check container image exists in ECR and job definition is correct
3. **Permission errors**: Verify job execution role has proper S3 and CloudWatch permissions
4. **Container not found**: Ensure container image URI in job definition matches your ECR repository

### Getting Help
- Check CloudWatch logs for detailed error messages
- Use AWS Batch console to view job details and status reasons
- Verify all IAM roles and policies are correctly configured
