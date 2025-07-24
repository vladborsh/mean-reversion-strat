#!/bin/bash
# AWS Batch Management Scripts for Mean Reversion Strategy
# This script shows all available AWS Batch job management scripts

echo "🚀 AWS Batch Job Management Scripts"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -d "scripts" ]; then
  echo "❌ Error: Please run this from the project root directory"
  echo "   Current directory: $(pwd)"
  echo "   Expected: /path/to/mean-reversion-strat"
  exit 1
fi

echo "📁 Available Scripts in ./scripts/:"
echo ""

# Job Submission Scripts
echo "🔧 JOB SUBMISSION SCRIPTS:"
echo "  ./scripts/submit_forex_jobs.sh [timeframe] [optimization_type]"
echo "    Submit optimization jobs for all major forex pairs"
echo "    Example: ./scripts/submit_forex_jobs.sh 15m balanced"
echo "    Default: ./scripts/submit_forex_jobs.sh (uses 5m timeframe, balanced optimization)"
echo ""

# Monitoring Scripts
echo "📊 MONITORING SCRIPTS:"
echo "  ./scripts/monitor_job_progress.py [job_id_or_tracking_file] [options]"
echo "    Monitor job progress by reading S3 status files"
echo "    Example: ./scripts/monitor_job_progress.py forex_jobs_20250724-161151.csv --follow"
echo "    Example: ./scripts/monitor_job_progress.py abc123-def456-ghi789 --refresh 10"
echo ""
echo "  aws batch list-jobs --job-queue <queue-name>"
echo "    List AWS Batch jobs using AWS CLI"
echo "    Example: aws batch list-jobs --job-queue mean-reversion-job-queue"
echo ""
echo "  aws logs describe-log-streams --log-group-name /aws/batch/job"
echo "    Check CloudWatch logs for job output"
echo "    Example: aws logs tail /aws/batch/job --follow"
echo ""

# Configuration
echo "⚙️  CONFIGURATION:"
echo "  Environment Variables (optional):"
echo "    BATCH_JOB_QUEUE=your-queue-name"
echo "    BATCH_JOB_DEFINITION=your-job-definition"
echo ""

# Quick Start
echo "🚦 QUICK START:"
echo "  1. Set up AWS Batch (see docs/AWS_BATCH_SETUP.md)"
echo "  2. Build and push container to ECR"
echo "  3. Submit jobs:"
echo "     ./scripts/submit_forex_jobs.sh"
echo "  4. Monitor progress:"
echo "     ./scripts/monitor_job_progress.py forex_jobs_*.csv --follow"
echo "  5. View job status:"
echo "     aws batch list-jobs --job-queue mean-reversion-job-queue"
echo "  6. Check logs via CloudWatch or S3:"
echo "     aws logs tail /aws/batch/job --follow"
echo ""

# Dependencies Check
echo "🔍 DEPENDENCY CHECK:"
echo -n "  AWS CLI: "
if command -v aws &> /dev/null; then
  echo "✅ Found ($(aws --version 2>&1 | cut -d' ' -f1))"
else
  echo "❌ Not found - Please install AWS CLI"
fi

echo -n "  AWS Credentials: "
if aws sts get-caller-identity &> /dev/null; then
  echo "✅ Configured"
else
  echo "❌ Not configured - Run 'aws configure'"
fi

echo ""
echo "📖 For detailed setup instructions, see: docs/AWS_BATCH_SETUP.md"
