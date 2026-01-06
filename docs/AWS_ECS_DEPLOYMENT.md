# AWS ECS Deployment Guide for Mean Reversion Strategy Bot

This document provides step-by-step instructions for deploying the Mean Reversion Strategy Bot container on AWS Elastic Container Service (ECS) using the AWS Console and CLI.

## Related Documentation

- **[Bot Podman Instructions](BOT_DOCKER_INSTRUCTIONS.md)** - Local container setup and testing
- **[Telegram Bot Integration](TELEGRAM_BOT_INTEGRATION.md)** - Bot configuration and features
- **[Signal Cache Persistence](signal_cache_persistence.md)** - DynamoDB configuration for signal caching
- **[Telegram DynamoDB Persistence](telegram_dynamodb_persistence.md)** - DynamoDB storage for chat management
- **[Container Documentation](CONTAINER.md)** - General container usage

## Prerequisites

Before deploying to ECS, ensure you have:

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Docker** installed locally for building images
4. **Strategy optimized** with `results/best_configs_balanced.json`
5. **API credentials** for Capital.com and Telegram

## Step 1: Prepare Container Image

### 1.1 Build and Test Locally

```bash
# Navigate to project directory
cd /path/to/mean-reversion-strat

# Build the container
podman build -f Dockerfile.bot -t mean-reversion-bot:latest .

# Test locally first
podman run --rm --env-file .env mean-reversion-bot:latest
```

### 1.2 Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository \
    --repository-name mean-reversion-bot \
    --region eu-central-1 \
    --image-scanning-configuration scanOnPush=true

# Get login token
aws ecr get-login-password --region eu-central-1 | podman login --username AWS --password-stdin <aws-account-id>.dkr.ecr.eu-central-1.amazonaws.com
```

### 1.3 Push Image to ECR

```bash
# Tag the image
podman tag mean-reversion-bot:latest <aws-account-id>.dkr.ecr.eu-central-1.amazonaws.com/mean-reversion-bot:latest

# Push to ECR
podman push <aws-account-id>.dkr.ecr.eu-central-1.amazonaws.com/mean-reversion-bot:latest
```

## Step 2: Create ECS Infrastructure

### Choosing Your Launch Type: Fargate vs EC2

> **2026 Update**: AWS Fargate pricing has become more competitive for small workloads. Consider your options:

#### Fargate (Recommended for Small-Medium Workloads)

**Pros:**
- No server management required
- Pay only for running tasks (per-second billing)
- Automatic scaling and patching
- Better for intermittent workloads
- Easier setup and maintenance

**Cons:**
- Slightly higher cost for 24/7 workloads
- Less control over underlying infrastructure

**Best for:**
- Getting started quickly
- Intermittent or scheduled workloads
- Teams without DevOps expertise
- Development and testing environments

**Pricing (2026 approximate):**
- 0.25 vCPU, 0.5 GB RAM = ~$10-12/month (24/7)
- With scheduled scaling: ~$5-8/month

#### EC2 (Recommended for High-Volume or Cost-Sensitive 24/7 Workloads)

**Pros:**
- Lower cost for always-running tasks
- More control over instance types
- Can use Reserved Instances for savings
- Better for predictable 24/7 workloads

**Cons:**
- Requires more management
- Manual patching and updates
- More complex setup

**Best for:**
- Cost-sensitive 24/7 operations
- High-volume trading (100+ requests/minute)
- Teams with DevOps experience
- Production at scale

**Pricing (2026 approximate):**
- t3.micro: ~$7.50/month (24/7)
- t4g.micro (ARM): ~$6/month (24/7)

### Decision Matrix

| Your Situation | Recommended |
|----------------|-------------|
| Just starting out | **Fargate** |
| Development/Testing | **Fargate** |
| Running 6-8 hours/day only | **Fargate** |
| 24/7 operation, budget-conscious | **EC2** |
| High-frequency trading (>100 req/min) | **EC2** |
| No DevOps team | **Fargate** |
| Want automatic scaling | **Fargate** |

For this guide, we'll show **both options**. Choose the one that fits your needs.

## Step 3: Create ECS Cluster

### Option A: Fargate Cluster (Recommended for Most Users)

#### Using AWS Console

1. Navigate to **ECS Console** → **Clusters**
2. Click **Create Cluster**
3. **Cluster configuration**:
   - **Cluster name**: `mean-reversion-cluster`
   - **Infrastructure**: AWS Fargate (serverless)
4. **Monitoring** (optional):
   - Enable **Container Insights** for detailed metrics
5. Click **Create**

The cluster will be created in seconds. No EC2 instances to manage!

### Option B: EC2 Cluster (For Cost-Sensitive 24/7 Operations)

#### Using AWS Console

1. Navigate to **ECS Console** → **Clusters**
2. Click **Create Cluster**
3. Choose **EC2 Linux + Networking**
4. Configure cluster:
   - **Cluster name**: `mean-reversion-cluster`
   - **EC2 instance type**: `t3.micro` or `t4g.micro` (ARM, cheaper)
   - **Number of instances**: `1`
   - **VPC**: Use default or select existing
   - **Subnets**: Select at least 2 availability zones
   - **Auto assign public IP**: Enable
   - **Security group**: Use default (allows all outbound traffic)
5. Click **Create**

The cluster will automatically:
- Create EC2 instances with ECS-optimized AMI
- Set up Auto Scaling Group
- Create security groups with proper outbound rules

## Step 2.1: Create Security Group (If Not Using Default)

## Step 4: Create Task Definition

### 4.1 Create Task Definition using AWS Console

1. Navigate to **ECS Console** → **Task Definitions**
2. Click **Create new Task Definition**
3. **Choose launch type compatibility**:
   - For **Fargate**: Select **Fargate**
   - For **EC2**: Select **EC2**

#### For Fargate Launch Type

4. Configure task definition:
   - **Task Definition Name**: `mean-reversion-bot`
   - **Task Role**: Select `MeanReversionJobExecutionRole`
   - **Network Mode**: `awsvpc` (default for Fargate)
   - **Task execution role**: Select `ecsTaskExecutionRole`
   - **Task memory (GB)**: `0.5` (512 MB)
   - **Task CPU (vCPU)**: `0.25` (256 CPU units)

5. Add Container:
   - **Container name**: `mean-reversion-bot`
   - **Image**: `<aws-account-id>.dkr.ecr.eu-central-1.amazonaws.com/mean-reversion-bot:latest`
   - **Memory Limits**: Soft limit `512` MiB
   - **Port mappings**: Leave empty (no ports needed)

#### For EC2 Launch Type

4. Configure task definition:
   - **Task Definition Name**: `mean-reversion-bot`
   - **Network Mode**: `bridge`
   - **Task memory (MiB)**: `512`
   - **Task CPU (unit)**: `256`

5. Add Container:
   - **Container name**: `mean-reversion-bot`
   - **Image**: `<aws-account-id>.dkr.ecr.eu-central-1.amazonaws.com/mean-reversion-bot:latest`
   - **Memory Limits (MiB)**: Soft limit `512`
   - **Port mappings**: Leave empty (no ports needed)

#### Common Configuration (Both Launch Types)

6. Add Environment Variables:
   - `PYTHONUNBUFFERED` = `1`
   - `LOG_LEVEL` = `INFO`

7. Add Secrets (from Parameter Store):
   - `CAPITAL_COM_API_KEY` → `/mean-reversion-bot/capital-com-api-key`
   - `CAPITAL_COM_PASSWORD` → `/mean-reversion-bot/capital-com-password`
   - `CAPITAL_COM_IDENTIFIER` → `/mean-reversion-bot/capital-com-identifier`
   - `TELEGRAM_BOT_TOKEN` → `/mean-reversion-bot/telegram-bot-token`

8. Configure Logging:
   - **Log driver**: `awslogs`
   - **awslogs-group**: `/ecs/mean-reversion-bot`
   - **awslogs-region**: `eu-central-1`
   - **awslogs-stream-prefix**: `ecs`

9. Click **Create**

### 4.2 Create CloudWatch Log Group

```bash
# Create log group
aws logs create-log-group \
    --log-group-name /ecs/mean-reversion-bot \
    --region eu-central-1

# Set retention policy (optional)
aws logs put-retention-policy \
    --log-group-name /ecs/mean-reversion-bot \
    --retention-in-days 30 \
    --region eu-central-1
```

## Step 5: Create ECS Service using AWS Console

### 5.1 Create Service

1. Navigate to your **ECS Cluster** → `mean-reversion-cluster`
2. Go to **Services** tab → Click **Create**
3. Configure service:
   - **Launch type**: Select **Fargate** or **EC2** (match your task definition)
   - **Task Definition**: Select `mean-reversion-bot:1`
   - **Cluster**: `mean-reversion-cluster`
   - **Service name**: `mean-reversion-bot-service`
   - **Service type**: `REPLICA`
   - **Number of tasks**: `1`

4. **Network Configuration** (Fargate only):
   - **VPC**: Select your VPC
   - **Subnets**: Select at least 2 subnets
   - **Security groups**: Select security group with outbound access
   - **Auto-assign public IP**: ENABLED

5. **Deployments**:
   - **Minimum healthy percent**: `0`
   - **Maximum percent**: `100`

6. **Task Placement** (EC2 only):
   - **Placement Templates**: `AZ Balanced Spread`

7. **Load balancing**: Skip (not needed)

8. **Service discovery**: Skip (not needed)

9. **Auto Scaling**: We'll configure this separately

10. Click **Create Service**

## Step 6: Configure Auto Scaling using AWS Console

### 6.1 Service Auto Scaling

1. Navigate to your **ECS Service** → `mean-reversion-bot-service`
2. Go to **Auto Scaling** tab → Click **Create**
3. Configure auto scaling:
   - **Service**: `mean-reversion-bot-service`
   - **Minimum capacity**: `1`
   - **Desired capacity**: `1`
   - **Maximum capacity**: `2`

4. **Scaling policies**:
   - **Policy name**: `cpu-scaling-policy`
   - **ECS service metric**: `Average CPU utilization`
   - **Target value**: `70`
   - **Scale-out cooldown**: `300 seconds`
   - **Scale-in cooldown**: `300 seconds`

5. Click **Save**

### 6.2 Cluster Auto Scaling

The cluster auto scaling is automatically managed by the capacity provider configured during cluster creation. EC2 instances will be added/removed based on task placement requirements.

## Step 7: Configure CloudWatch Alarms using AWS Console

### 7.1 High CPU Utilization Alarm

1. Navigate to **CloudWatch Console** → **Alarms**
2. Click **Create alarm**
3. **Select metric**:
   - **Service**: `ECS`
   - **Metric**: `CPUUtilization`
   - **Dimensions**: 
     - `ServiceName` = `mean-reversion-bot-service`
     - `ClusterName` = `mean-reversion-cluster`
4. **Conditions**:
   - **Threshold type**: `Static`
   - **Whenever CPUUtilization is**: `Greater than 80`
   - **Datapoints to alarm**: `2 of 2`
   - **Period**: `5 minutes`
5. **Actions**: Configure SNS topic for notifications (optional)
6. **Name**: `mean-reversion-bot-high-cpu`
7. Click **Create alarm**

### 7.2 Task Failure Alarm

1. **Select metric**:
   - **Service**: `ECS`
   - **Metric**: `RunningCount`
   - **Dimensions**: Same as above
2. **Conditions**:
   - **Whenever RunningCount is**: `Lower than 1`
   - **Datapoints to alarm**: `2 of 2`
   - **Period**: `5 minutes`
3. **Name**: `mean-reversion-bot-task-failures`
4. Click **Create alarm**

### 7.3 View Logs

```bash
# View recent logs
aws logs describe-log-streams \
    --log-group-name /ecs/mean-reversion-bot \
    --region eu-central-1

# Get specific log events
aws logs get-log-events \
    --log-group-name /ecs/mean-reversion-bot \
    --log-stream-name ecs/mean-reversion-bot/<task-id> \
    --region eu-central-1
```

## Step 8: Deployment Scripts

### 8.1 Create Deployment Script

Create `deploy-to-ecs.sh`:

```bash
#!/bin/bash

set -e

# Configuration
AWS_REGION="eu-central-1"
AWS_ACCOUNT_ID="your-account-id"
CLUSTER_NAME="mean-reversion-cluster"
SERVICE_NAME="mean-reversion-bot-service"
REPOSITORY_NAME="mean-reversion-bot"

echo "Starting ECS deployment..."

# Build and push image
echo "Building Podman image..."
podman build -f Dockerfile.bot -t $REPOSITORY_NAME:latest .

echo "Tagging and pushing to ECR..."
podman tag $REPOSITORY_NAME:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME:latest

aws ecr get-login-password --region $AWS_REGION | podman login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

podman push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPOSITORY_NAME:latest

# Update service
echo "Updating ECS service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment \
    --region $AWS_REGION

### 8.2 Create Update Script

Create `update-config.sh`:

```bash
#!/bin/bash

# Force service update to pull latest image
aws ecs update-service \
    --cluster mean-reversion-cluster \
    --service mean-reversion-bot-service \
    --force-new-deployment \
    --region eu-central-1
```

## Step 9: Testing and Validation

### 9.1 Service Health Check

```bash
# Check service status
aws ecs describe-services \
    --cluster mean-reversion-cluster \
    --services mean-reversion-bot-service \
    --region eu-central-1

# Check task status
aws ecs list-tasks \
    --cluster mean-reversion-cluster \
    --service-name mean-reversion-bot-service \
    --region eu-central-1
```

### 9.2 Execute Commands in Running Container

```bash
# Enable execute command capability (already done in service definition)
# Run commands inside the container
aws ecs execute-command \
    --cluster mean-reversion-cluster \
    --task <task-arn> \
    --container mean-reversion-bot \
    --interactive \
    --command "/bin/bash" \
    --region eu-central-1
```

## Cost Optimization

### 10.1 2026 Cost Comparison

For your low-traffic workload (15 requests per 5 minutes):

#### Fargate Pricing (0.25 vCPU, 0.5 GB RAM)
```bash
# 24/7 operation
# - Compute: $0.04048/hour = $29.15/month
# - With 50% utilization (scheduled): ~$14.50/month
# - With 33% utilization (8hrs/day): ~$9.70/month
```

#### EC2 t3.micro Pricing
```bash
# 24/7 operation
# - Instance: $0.0104/hour = $7.50/month
# - EBS storage: $0.10/GB/month (8GB = $0.80/month)
# - Total: ~$8.30/month
```

#### EC2 t4g.micro (ARM) Pricing
```bash
# 24/7 operation (20% cheaper than t3)
# - Instance: $0.0084/hour = $6.05/month
# - EBS storage: $0.10/GB/month (8GB = $0.80/month)
# - Total: ~$6.85/month
```

#### Recommendation by Use Case

| Use Case | Best Option | Estimated Cost |
|----------|-------------|----------------|
| Getting Started / Testing | Fargate (scheduled) | $5-10/month |
| Part-time Trading (8hrs/day) | Fargate | $9-12/month |
| 24/7 Trading, Budget-focused | EC2 t4g.micro | $7/month |
| 24/7 Trading, Ease-of-use | Fargate | $29/month |
| High-frequency (>100 req/min) | EC2 t3.small | $15/month |

### 10.2 Scheduled Scaling (Fargate or EC2)

Scale down during non-trading hours to save costs:

```bash
# Create scheduled scaling for night hours (scale to 0)
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/mean-reversion-cluster/mean-reversion-bot-service \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name scale-down-night \
  --schedule "cron(0 18 * * ? *)" \
  --scalable-target-action MinCapacity=0,MaxCapacity=0 \
  --region eu-central-1

# Scale up for trading hours (scale to 1)
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/mean-reversion-cluster/mean-reversion-bot-service \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name scale-up-morning \
  --schedule "cron(0 6 * * ? *)" \
  --scalable-target-action MinCapacity=1,MaxCapacity=1 \
  --region eu-central-1
```

**Potential Savings**: 50-66% reduction in costs with scheduled scaling

### 10.3 Additional Cost Optimization Tips

1. **Use ARM (Graviton) instances**: 20% cheaper than x86 (EC2 only)
2. **Enable Container Insights selectively**: Only when debugging
3. **Use log retention**: Set CloudWatch log retention to 7-30 days
4. **Rightsizing**: Start small (0.25 vCPU), scale up only if needed
5. **Reserved Instances**: For long-term EC2 usage (save up to 40%)
6. **Spot Instances**: For non-critical dev/test (save up to 70%)

## Troubleshooting

### Common Issues

#### 1. Task Fails to Start
```bash
# Check task definition
aws ecs describe-task-definition --task-definition mean-reversion-bot:1

# Check task failures
aws ecs describe-tasks --cluster mean-reversion-cluster --tasks <task-arn>
```

#### 2. Container Can't Pull Image
- Verify ECR repository exists
- Check image URI in task definition
- Ensure image was pushed successfully

#### 3. Environment Variables Not Working
- Confirm parameter names match exactly

- Confirm parameter names match exactly

#### 4. Network Connectivity Issues
- Check security group outbound rules
- Verify subnet routing
- Ensure internet gateway for public subnets

### Debug Commands

```bash
# View service events
aws ecs describe-services \
    --cluster mean-reversion-cluster \
    --services mean-reversion-bot-service \
    --region eu-central-1 \
    --query 'services[0].events'

# Check CloudWatch logs
aws logs filter-log-events \
    --log-group-name /ecs/mean-reversion-bot \
    --start-time $(date -d '1 hour ago' +%s)000 \
    --region eu-central-1
```

## Security Best Practices

1. **Store secrets** in Parameter Store or Secrets Manager
2. **Enable container insights** for monitoring
3. **Use private subnets** with NAT Gateway for production
4. **Enable VPC Flow Logs** for network monitoring
5. **Use AWS Config** for compliance monitoring

## Maintenance

### Regular Tasks

1. **Update base images** regularly for security patches
2. **Monitor costs** and optimize resource usage
3. **Review CloudWatch alarms** and adjust thresholds
4. **Backup strategy configurations** to S3
5. **Test disaster recovery** procedures
6. **Review and rotate** API credentials

### Updates

To update the bot:

1. Build new image with updated code
2. Push to ECR with new tag
3. Update task definition with new image
4. Deploy using `update-service` command

This completes the AWS ECS deployment guide for your Mean Reversion Strategy Bot. The setup provides a scalable, monitored, and secure environment for running your trading bot in the cloud.
