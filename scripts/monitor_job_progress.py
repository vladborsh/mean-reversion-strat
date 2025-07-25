#!/usr/bin/env python3
"""
Monitor AWS Batch job progress by reading status files from S3.

This Python rewrite replaces the complex Bash script with a cleaner,
more maintainable implementation while preserving all functionality.

Usage: ./monitor_job_progress.py [job_id_or_tracking_file] [options]
Example: ./monitor_job_progress.py abc123-def456-ghi789
Example: ./monitor_job_progress.py forex_jobs_20250724-161151.csv --follow
Example: ./monitor_job_progress.py forex_jobs_20250724-161151.csv --refresh 10
"""

import argparse
import csv
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import tempfile

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# Configuration
DEFAULT_REFRESH_INTERVAL = 30
S3_BUCKET = "strategy-backtest-bucket"
S3_LOGS_PREFIX = "mean-reversion-strat/optimization/logs"
AWS_JOB_QUEUE = "mean-reversion-job-queue"

# ANSI Color codes
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GRAY = '\033[0;37m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

    @classmethod
    def disable(cls):
        """Disable all colors for non-color output."""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = ''
        cls.PURPLE = cls.CYAN = cls.GRAY = cls.BOLD = cls.NC = ''


# Progress bar characters
FULL_BLOCK = "█"
PARTIAL_BLOCKS = ["▏", "▎", "▍", "▌", "▋", "▊", "▉"]


@dataclass
class JobInfo:
    """Job information extracted from tracking file or job name."""
    symbol: str = "unknown"
    timeframe: str = "unknown"
    optimization_type: str = "unknown"
    timestamp: str = ""


@dataclass
class JobStatus:
    """Complete job status information."""
    job_id: str
    status: str
    job_name: str
    info: JobInfo
    completed: int = 0
    total: int = 0
    percentage: float = 0.0
    elapsed_time: str = "N/A"
    estimated_completion: str = "N/A"
    current_best_pnl: str = "N/A"
    current_best_ratio: str = "N/A"
    last_result: str = "N/A"
    failure_reason: str = ""
    created_at: int = 0  # Unix timestamp


class ProgressBar:
    """Enhanced progress bar with unicode blocks and color coding."""
    
    @staticmethod
    def draw(current: int, total: int, width: int = 50, show_percentage: bool = True) -> str:
        """Draw a progress bar with the given parameters."""
        if total == 0:
            bar = '[' + '-' * width + ']'
            if show_percentage:
                bar += " N/A"
            return bar

        # Calculate percentage with decimal precision
        percentage = (current * 100.0) / total
        
        # Calculate filled width for progress bar
        filled_width = int((current * width) / total)
        empty_width = width - filled_width
        
        # Create progress bar
        bar_content = FULL_BLOCK * filled_width
        
        # Add partial block if needed
        if empty_width > 0 and filled_width < width:
            remainder = (current * width) % total
            if remainder > 0:
                partial_index = min(6, int((remainder * 7) / total))
                if partial_index >= 0:
                    bar_content += PARTIAL_BLOCKS[partial_index]
                    empty_width -= 1
        
        # Add empty blocks
        bar_content += ' ' * empty_width
        
        # Color the bar based on progress
        if percentage >= 100:
            colored_bar = f"{Colors.GREEN}[{bar_content}]{Colors.NC}"
        elif percentage >= 75:
            colored_bar = f"{Colors.CYAN}[{bar_content}]{Colors.NC}"
        elif percentage >= 50:
            colored_bar = f"{Colors.YELLOW}[{bar_content}]{Colors.NC}"
        elif percentage >= 25:
            colored_bar = f"{Colors.BLUE}[{bar_content}]{Colors.NC}"
        else:
            colored_bar = f"{Colors.GRAY}[{bar_content}]{Colors.NC}"
        
        # Add percentage if requested
        if show_percentage:
            if percentage < 10 and percentage % 1 != 0:
                colored_bar += f" {percentage:.1f}% ({current}/{total})"
            else:
                colored_bar += f" {percentage:3.0f}% ({current}/{total})"
        
        return colored_bar


class AWSBatchMonitor:
    """Main class for monitoring AWS Batch jobs."""
    
    def __init__(self, use_color: bool = True):
        self.use_color = use_color
        if not use_color:
            Colors.disable()
        
        # Initialize AWS clients
        try:
            self.batch_client = boto3.client('batch')
            self.s3_client = boto3.client('s3')
            # Test credentials
            self._test_aws_credentials()
        except NoCredentialsError:
            print(f"{Colors.RED}Error: AWS credentials not configured.{Colors.NC}")
            print("Run 'aws configure' or set AWS_PROFILE environment variable.")
            sys.exit(1)
    
    def _test_aws_credentials(self):
        """Test AWS credentials by making a simple call."""
        try:
            sts_client = boto3.client('sts')
            sts_client.get_caller_identity()
        except Exception as e:
            print(f"{Colors.RED}Error: AWS credentials invalid or insufficient permissions.{Colors.NC}")
            print(f"Details: {e}")
            sys.exit(1)
    
    def format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def get_job_status(self, job_id: str) -> str:
        """Get job status from AWS Batch."""
        try:
            response = self.batch_client.describe_jobs(jobs=[job_id])
            if response['jobs']:
                return response['jobs'][0]['status']
            return "UNKNOWN"
        except ClientError as e:
            print(f"{Colors.YELLOW}Warning: Could not get status for job {job_id}: {e}{Colors.NC}")
            return "UNKNOWN"
    
    def get_job_name(self, job_id: str) -> str:
        """Get job name from AWS Batch."""
        try:
            response = self.batch_client.describe_jobs(jobs=[job_id])
            if response['jobs']:
                return response['jobs'][0]['jobName']
            return "unknown"
        except ClientError:
            return "unknown"
    
    def get_job_failure_reason(self, job_id: str) -> str:
        """Get job failure reason from AWS Batch."""
        try:
            response = self.batch_client.describe_jobs(jobs=[job_id])
            if response['jobs']:
                return response['jobs'][0].get('statusReason', '')
            return ""
        except ClientError:
            return ""
    
    def get_jobs_from_queue(self, job_statuses: List[str] = None) -> List[Dict]:
        """Get jobs from the AWS Batch queue with specified statuses."""
        if job_statuses is None:
            job_statuses = ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING', 'SUCCEEDED', 'FAILED']
        
        # First, let's verify the queue exists
        try:
            queues_response = self.batch_client.describe_job_queues(jobQueues=[AWS_JOB_QUEUE])
            queues = queues_response.get('jobQueues', [])
            if not queues:
                print(f"{Colors.RED}Error: Job queue '{AWS_JOB_QUEUE}' not found!{Colors.NC}")
                # List available queues
                all_queues = self.batch_client.describe_job_queues()
                queue_names = [q['jobQueueName'] for q in all_queues.get('jobQueues', [])]
                print(f"{Colors.YELLOW}Available queues: {queue_names}{Colors.NC}")
                return []
        except Exception as e:
            print(f"{Colors.RED}Error checking queue: {e}{Colors.NC}")
            return []
        
        all_jobs = []
        
        for status in job_statuses:
            try:
                # Try direct API call first (without paginator)
                direct_response = self.batch_client.list_jobs(
                    jobQueue=AWS_JOB_QUEUE,
                    jobStatus=status,
                    maxResults=100
                )
                direct_jobs = direct_response.get('jobSummaryList', [])
                
                if direct_jobs:
                    for job in direct_jobs:
                        job_detail = {
                            'jobId': job['jobId'],
                            'jobName': job['jobName'],
                            'status': job['status'],
                            'createdAt': job.get('createdAt', 0),
                            'startedAt': job.get('startedAt', 0),
                            'stoppedAt': job.get('stoppedAt', 0)
                        }
                        all_jobs.append(job_detail)
                    continue
                
                # If direct call found nothing, try paginator
                paginator = self.batch_client.get_paginator('list_jobs')
                
                for page in paginator.paginate(
                    jobQueue=AWS_JOB_QUEUE,
                    jobStatus=status
                ):
                    jobs = page.get('jobSummaryList', [])
                    
                    for job in jobs:
                        # Get detailed job information
                        job_detail = {
                            'jobId': job['jobId'],
                            'jobName': job['jobName'],
                            'status': job['status'],
                            'createdAt': job.get('createdAt', 0),
                            'startedAt': job.get('startedAt', 0),
                            'stoppedAt': job.get('stoppedAt', 0)
                        }
                        all_jobs.append(job_detail)
            
            except ClientError as e:
                print(f"{Colors.YELLOW}Warning: Could not list jobs with status {status}: {e}{Colors.NC}")
            except Exception as e:
                print(f"{Colors.RED}Unexpected error for status {status}: {e}{Colors.NC}")
        
        # Sort by creation time (newest first)
        all_jobs.sort(key=lambda x: x['createdAt'], reverse=True)
        return all_jobs
    
    def get_recent_jobs(self) -> List[Dict]:
        """Get recent jobs from the queue (all statuses)."""
        jobs = self.get_jobs_from_queue()
        return jobs[:50]  # Default limit of 50
    
    def get_active_jobs(self) -> List[Dict]:
        """Get only active (non-terminal) jobs from the queue."""
        active_statuses = ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING']
        return self.get_jobs_from_queue(active_statuses)
    
    def get_job_info_from_csv(self, job_id: str, tracking_file: str) -> Optional[JobInfo]:
        """Extract job info from CSV tracking file."""
        try:
            with open(tracking_file, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if row and row[0] == job_id:
                        symbol = row[2] if len(row) > 2 else "unknown"
                        timeframe = row[3] if len(row) > 3 else "unknown"
                        optimization_type = row[4] if len(row) > 4 else "unknown"
                        submitted_at = row[5] if len(row) > 5 else ""
                        
                        # Extract timestamp (2025-07-24T11:27:51Z -> 20250724_112751)
                        timestamp = ""
                        if submitted_at:
                            timestamp = re.sub(r'[-:TZ]', '', submitted_at)[:15]
                            timestamp = timestamp[:8] + '_' + timestamp[8:]
                        
                        return JobInfo(symbol, timeframe, optimization_type, timestamp)
        except (FileNotFoundError, OSError, IndexError):
            pass
        return None
    
    def extract_job_info_from_name(self, job_name: str) -> JobInfo:
        """Extract job info from job name as fallback."""
        # Extract symbol (pattern: opt-SYMBOL-...)
        symbol_match = re.search(r'opt-([^-]*-[^-]*)-', job_name)
        symbol = "unknown"
        if symbol_match:
            symbol = symbol_match.group(1).replace('-X', '=X')
        
        # Extract timeframe (pattern: opt-SYMBOL-TIMEFRAME-...)
        timeframe = "unknown"
        timeframe_match = re.search(r'opt-[^-]+-[^-]+-([^-]+)-', job_name)
        if timeframe_match:
            timeframe = timeframe_match.group(1)
        
        # Extract optimization type
        optimization_type = "unknown"
        type_match = re.search(r'opt-[^-]+-[^-]+-[^-]+-([^-]+)-[0-9]+', job_name)
        if type_match:
            optimization_type = type_match.group(1)
        
        # Extract timestamp from job name if present
        timestamp = ""
        timestamp_match = re.search(r'-(\d{8}_\d{6})$', job_name)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
        
        return JobInfo(symbol, timeframe, optimization_type, timestamp)
    
    def read_status_from_s3(self, job_id: str, job_info: JobInfo) -> Optional[str]:
        """Read status file from S3."""
        # Convert symbol format (EURUSD=X -> EURUSDX)
        s3_symbol = job_info.symbol.replace('=X', 'X')
        
        # Try different prefix patterns - including the actual S3 naming convention
        # The S3 files use patterns like: EURUSDX_5m_progress_grid_search_focused_timestamp.txt
        prefixes = [
            # Try with common timeframes and 'balanced' optimization type
            f"{s3_symbol}_5m_progress_grid_search_focused_",
            f"{s3_symbol}_1h_progress_grid_search_focused_",
            f"{s3_symbol}_4h_progress_grid_search_focused_",
            f"{s3_symbol}_1d_progress_grid_search_focused_",
            # Try with other common optimization types
            f"{s3_symbol}_5m_progress_grid_search_{job_info.optimization_type}_",
            f"{s3_symbol}_1h_progress_grid_search_{job_info.optimization_type}_",
            f"{s3_symbol}_4h_progress_grid_search_{job_info.optimization_type}_",
            f"{s3_symbol}_1d_progress_grid_search_{job_info.optimization_type}_",
            # Original patterns (in case timeframe extraction works correctly)
            f"{s3_symbol}_{job_info.timeframe}_progress_grid_search_focused_",
            f"{s3_symbol}_{job_info.timeframe}_progress_grid_search_{job_info.optimization_type}_",
            f"{s3_symbol}_{job_info.timeframe}_progress_",
            # Broader patterns
            f"{s3_symbol}_progress_grid_search_focused_",
            f"{s3_symbol}_progress_grid_search_{job_info.optimization_type}_",
            f"{s3_symbol}_progress_",
            # Job ID based patterns
            f"{job_id}_status",
            f"{job_id}_",
        ]
        
        for prefix in prefixes:
            try:
                # List files with this prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=S3_BUCKET,
                    Prefix=f"{S3_LOGS_PREFIX}/{prefix}"
                )
                
                if 'Contents' in response:
                    # Find .txt files
                    txt_files = [obj['Key'] for obj in response['Contents'] 
                                if obj['Key'].endswith('.txt')]
                    
                    if txt_files:
                        # Take the most recent matching file (sort by timestamp in filename)
                        txt_files.sort(reverse=True)  # Most recent first
                        status_file = txt_files[0]
                        
                        # Download and read the file
                        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
                            try:
                                self.s3_client.download_file(S3_BUCKET, status_file, temp_file.name)
                                with open(temp_file.name, 'r') as f:
                                    content = f.read()
                                os.unlink(temp_file.name)
                                return content
                            except ClientError:
                                os.unlink(temp_file.name)
                                continue
            except ClientError:
                continue
        
        return None
    
    def parse_status_file(self, content: str) -> Dict[str, str]:
        """Parse status file content and extract metrics."""
        data = {
            'completed': '0',
            'total': '0',
            'percentage': '0',
            'elapsed_time': 'N/A',
            'estimated_completion': 'N/A',
            'current_best_pnl': 'N/A',
            'current_best_ratio': 'N/A',
            'last_result': 'N/A'
        }
        
        for line in content.split('\n'):
            line = line.strip()
            if 'Completed:' in line:
                # Extract "Completed: 99/31104 (0.3%)"
                match = re.search(r'Completed: (\d+)/(\d+) \(([0-9.]+)%\)', line)
                if match:
                    data['completed'] = match.group(1)
                    data['total'] = match.group(2)
                    data['percentage'] = match.group(3)
            elif line.startswith('Elapsed Time:'):
                data['elapsed_time'] = line.replace('Elapsed Time:', '').strip()
            elif line.startswith('Estimated Completion:'):
                data['estimated_completion'] = line.replace('Estimated Completion:', '').strip()
            elif line.startswith('Current Best PnL:'):
                data['current_best_pnl'] = line.replace('Current Best PnL:', '').strip()
            elif line.startswith('Current Best PnL/Drawdown Ratio:'):
                data['current_best_ratio'] = line.replace('Current Best PnL/Drawdown Ratio:', '').strip()
            elif line.startswith('Last Result:'):
                data['last_result'] = line.replace('Last Result:', '').strip()
        
        return data
    
    def get_complete_job_status(self, job_id: str, job_data: Optional[Dict] = None) -> JobStatus:
        """Get complete status information for a job."""
        # Get basic info from AWS (use provided data if available)
        if job_data:
            status = job_data['status']
            job_name = job_data['jobName']
            created_at = job_data.get('createdAt', 0)
        else:
            status = self.get_job_status(job_id)
            job_name = self.get_job_name(job_id)
            created_at = 0
        
        # Extract job info from job name
        job_info = self.extract_job_info_from_name(job_name)
        
        # Create basic job status
        job_status = JobStatus(
            job_id=job_id,
            status=status,
            job_name=job_name,
            info=job_info,
            created_at=created_at
        )
        
        # Get failure reason if failed
        if status == "FAILED":
            job_status.failure_reason = self.get_job_failure_reason(job_id)
        
        # Try to get progress data for running/completed jobs
        if status in ["RUNNING", "SUCCEEDED"]:
            status_content = self.read_status_from_s3(job_id, job_info)
            if status_content:
                parsed_data = self.parse_status_file(status_content)
                job_status.completed = int(parsed_data['completed'])
                job_status.total = int(parsed_data['total'])
                job_status.percentage = float(parsed_data['percentage'])
                job_status.elapsed_time = parsed_data['elapsed_time']
                job_status.estimated_completion = parsed_data['estimated_completion']
                job_status.current_best_pnl = parsed_data['current_best_pnl']
                job_status.current_best_ratio = parsed_data['current_best_ratio']
                job_status.last_result = parsed_data['last_result']
        
        return job_status
    
    def monitor_single_job(self, job_id: str):
        """Monitor progress of a single job."""
        print(f"{Colors.BLUE}Monitoring progress for job: {Colors.CYAN}{job_id}{Colors.NC}")
        print("=" * 50)
        
        job_status = self.get_complete_job_status(job_id)
        
        print(f"{Colors.BLUE}Job Name: {Colors.CYAN}{job_status.job_name}{Colors.NC}")
        print(f"{Colors.BLUE}Symbol: {Colors.CYAN}{job_status.info.symbol}{Colors.NC}")
        print(f"{Colors.BLUE}Timeframe: {Colors.CYAN}{job_status.info.timeframe}{Colors.NC}")
        print(f"{Colors.BLUE}Optimization Type: {Colors.CYAN}{job_status.info.optimization_type}{Colors.NC}")
        print(f"{Colors.BLUE}Status: {Colors.CYAN}{job_status.status}{Colors.NC}")
        print()
        
        # Handle different job states
        if job_status.status in ["SUBMITTED", "PENDING", "RUNNABLE", "STARTING"]:
            print(f"{Colors.YELLOW}Job is in '{job_status.status}' state. "
                  f"Progress data will be available when job starts running.{Colors.NC}")
            return
        
        if job_status.status == "RUNNING":
            if job_status.total > 0:
                # Show progress bar
                print(f"{Colors.BOLD}Progress:{Colors.NC}")
                progress_bar = ProgressBar.draw(job_status.completed, job_status.total, 60, True)
                print(f"  {progress_bar}")
                print()
                
                # Show detailed information
                print(f"{Colors.BOLD}Details:{Colors.NC}")
                print(f"  {Colors.BLUE}Elapsed Time:{Colors.NC} {job_status.elapsed_time}")
                print(f"  {Colors.BLUE}Estimated Completion:{Colors.NC} {job_status.estimated_completion}")
                print(f"  {Colors.BLUE}Current Best PnL:{Colors.NC} {Colors.GREEN}{job_status.current_best_pnl}{Colors.NC}")
                print(f"  {Colors.BLUE}Current Best Ratio:{Colors.NC} {Colors.GREEN}{job_status.current_best_ratio}{Colors.NC}")
                print(f"  {Colors.BLUE}Last Result:{Colors.NC} {job_status.last_result}")
            else:
                print(f"{Colors.YELLOW}Job is running but no progress data available yet.{Colors.NC}")
                self._show_search_patterns(job_status.info, job_id)
        
        elif job_status.status == "SUCCEEDED":
            print(f"{Colors.GREEN}✅ Job completed successfully!{Colors.NC}")
            if job_status.current_best_pnl != "N/A":
                print(f"  {Colors.BLUE}Final Best PnL:{Colors.NC} {Colors.GREEN}{job_status.current_best_pnl}{Colors.NC}")
                print(f"  {Colors.BLUE}Final Best Ratio:{Colors.NC} {Colors.GREEN}{job_status.current_best_ratio}{Colors.NC}")
        
        elif job_status.status == "FAILED":
            print(f"{Colors.RED}❌ Job failed!{Colors.NC}")
            if job_status.failure_reason:
                print(f"{Colors.RED}Failure reason: {job_status.failure_reason}{Colors.NC}")
        
        else:
            print(f"{Colors.GRAY}Job status: {job_status.status}{Colors.NC}")
            print(f"{Colors.YELLOW}No progress data available.{Colors.NC}")
    
    def _show_search_patterns(self, job_info: JobInfo, job_id: str):
        """Show the patterns being searched for progress files."""
        print(f"{Colors.GRAY}Searching for progress files with patterns:{Colors.NC}")
        s3_symbol = job_info.symbol.replace('=X', 'X')
        patterns = [
            f"{s3_symbol}_{job_info.timeframe}_progress_grid_search_{job_info.optimization_type}_*.txt",
            f"{s3_symbol}_{job_info.timeframe}_progress_*.txt",
            f"{s3_symbol}_progress_*.txt",
            f"{job_id}_status*.txt"
        ]
        for pattern in patterns:
            print(f"{Colors.GRAY}  {pattern}{Colors.NC}")
    
    def _display_jobs_table(self, job_statuses: List[JobStatus], status_counts: Dict[str, int], 
                           total_with_progress: int, total_progress_sum: float):
        """Display jobs in a formatted table."""
        if not job_statuses:
            return
        
        # Table headers
        print(f"{Colors.BOLD}┌────┬────────────┬─────────┬─────────────────────────────────────────────┬────────────────┬─────────────┐{Colors.NC}")
        print(f"{Colors.BOLD}│ #  │ Symbol     │ Status  │ Progress                                    │ Best PnL       │ Started     │{Colors.NC}")
        print(f"{Colors.BOLD}├────┼────────────┼─────────┼─────────────────────────────────────────────┼────────────────┼─────────────┤{Colors.NC}")
        
        # Table rows
        for i, job_status in enumerate(job_statuses, 1):
            # Format symbol (truncate if too long)
            symbol = job_status.info.symbol.replace('=X', '')[:10]
            
            # Format status with color
            if job_status.status == "RUNNING":
                status_colored = f"{Colors.YELLOW}RUNNING{Colors.NC}"
            elif job_status.status == "SUCCEEDED":
                status_colored = f"{Colors.GREEN}DONE   {Colors.NC}"
            elif job_status.status == "FAILED":
                status_colored = f"{Colors.RED}FAILED {Colors.NC}"
            elif job_status.status in ["SUBMITTED", "PENDING", "RUNNABLE", "STARTING"]:
                status_colored = f"{Colors.GRAY}PENDING{Colors.NC}"
            else:
                status_colored = f"{Colors.PURPLE}{job_status.status[:7]:<7}{Colors.NC}"
            
            # Format progress
            if job_status.status in ["RUNNING", "SUCCEEDED"] and job_status.total > 0:
                # Create compact progress bar (40 chars)
                progress_bar = ProgressBar.draw(job_status.completed, job_status.total, 33, False)
                progress_text = f"{progress_bar} {job_status.percentage:5.1f}%"
            elif job_status.status == "RUNNING":
                progress_text = f"{Colors.GRAY}{'Starting/No data yet':<43}{Colors.NC}"
            else:
                progress_text = f"{Colors.GRAY}{'N/A':<43}{Colors.NC}"
            
            # Format best PnL
            if job_status.current_best_pnl != "N/A" and job_status.current_best_pnl.strip():
                pnl_text = f"{Colors.GREEN}{job_status.current_best_pnl[:14]:<14}{Colors.NC}"
            else:
                pnl_text = f"{Colors.GRAY}{'N/A':<14}{Colors.NC}"
            
            # Format start time from creation timestamp
            if job_status.created_at > 0:
                start_time_dt = datetime.fromtimestamp(job_status.created_at / 1000)
                start_time = f"{Colors.GRAY}{start_time_dt.strftime('%m-%d %H:%M'):<11}{Colors.NC}"
            else:
                start_time = f"{Colors.GRAY}{'Unknown':<11}{Colors.NC}"
            
            # Print table row
            print(f"│{i:3d} │ {Colors.BOLD}{symbol:<10}{Colors.NC} │ {status_colored} │ {progress_text} │ {pnl_text} │ {start_time} │")
        
        # Table footer
        print(f"{Colors.BOLD}└────┴────────────┴─────────┴─────────────────────────────────────────────┴────────────────┴─────────────┘{Colors.NC}")
        print()
        
        # Show summary
        print(f"{Colors.BOLD}Summary:{Colors.NC}")
        print(f"  {Colors.GREEN}✅ Completed: {status_counts['SUCCEEDED']}{Colors.NC}")
        print(f"  {Colors.YELLOW}🔄 Running: {status_counts['RUNNING']}{Colors.NC}")
        print(f"  {Colors.GRAY}⏳ Pending: {status_counts['PENDING']}{Colors.NC}")
        print(f"  {Colors.RED}❌ Failed: {status_counts['FAILED']}{Colors.NC}")
        if status_counts['OTHER'] > 0:
            print(f"  {Colors.PURPLE}⚠️  Other: {status_counts['OTHER']}{Colors.NC}")
        
        # Show overall progress
        if total_with_progress > 0:
            avg_progress = total_progress_sum / total_with_progress
            print()
            print(f"{Colors.BOLD}Overall Progress:{Colors.NC}")
            # Create overall progress bar
            overall_bar = ProgressBar.draw(int(avg_progress), 100, 50, True)
            print(f"  {overall_bar}")
    
    def monitor_queue_jobs(self, follow: bool = False, refresh_interval: int = 30, active_only: bool = False):
        """Monitor progress of jobs from the AWS Batch queue."""
        try:
            while True:
                # Clear screen for follow mode
                if follow:
                    os.system('clear' if os.name == 'posix' else 'cls')
                
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"{Colors.BOLD}{Colors.BLUE}AWS Batch Job Progress Monitor{Colors.NC}")
                print(f"{Colors.BLUE}Job Queue: {Colors.CYAN}{AWS_JOB_QUEUE}{Colors.NC}")
                
                # Get jobs from queue
                if active_only:
                    print(f"{Colors.BLUE}Showing: {Colors.CYAN}Active jobs only{Colors.NC}")
                    jobs_data = self.get_active_jobs()
                else:
                    print(f"{Colors.BLUE}Showing: {Colors.CYAN}Recent jobs{Colors.NC}")
                    jobs_data = self.get_recent_jobs()
                
                print(f"{Colors.BLUE}Total Jobs: {Colors.CYAN}{len(jobs_data)}{Colors.NC}")
                print(f"{Colors.BLUE}Last Updated: {Colors.CYAN}{current_time}{Colors.NC}")
                print("=" * 60)
                print()
                
                if not jobs_data:
                    print(f"{Colors.YELLOW}No jobs found in queue {AWS_JOB_QUEUE}{Colors.NC}")
                    if not follow:
                        break
                    print(f"{Colors.GRAY}Refreshing in {refresh_interval}s... (Press Ctrl+C to stop){Colors.NC}")
                    time.sleep(refresh_interval)
                    continue
                
                # Get status for all jobs and count statuses
                job_statuses = []
                status_counts = {
                    'RUNNING': 0, 'SUCCEEDED': 0, 'FAILED': 0, 
                    'PENDING': 0, 'OTHER': 0
                }
                total_with_progress = 0
                total_progress_sum = 0.0
                
                for job_data in jobs_data:
                    job_status = self.get_complete_job_status(job_data['jobId'], job_data)
                    job_statuses.append(job_status)
                    
                    # Count status
                    if job_status.status == 'RUNNING':
                        status_counts['RUNNING'] += 1
                    elif job_status.status == 'SUCCEEDED':
                        status_counts['SUCCEEDED'] += 1
                    elif job_status.status == 'FAILED':
                        status_counts['FAILED'] += 1
                    elif job_status.status in ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING']:
                        status_counts['PENDING'] += 1
                    else:
                        status_counts['OTHER'] += 1
                    
                    # Track overall progress
                    if job_status.status in ["RUNNING", "SUCCEEDED"] and job_status.total > 0:
                        total_with_progress += 1
                        total_progress_sum += job_status.percentage
                
                # Display jobs in table format
                self._display_jobs_table(job_statuses, status_counts, total_with_progress, total_progress_sum)
                
                # Exit conditions for follow mode
                if follow:
                    if active_only:
                        # For active only mode, check if no active jobs remain
                        active_count = status_counts['RUNNING'] + status_counts['PENDING']
                        if active_count == 0:
                            print()
                            print(f"{Colors.GREEN}🎉 No active jobs remaining!{Colors.NC}")
                            break
                    
                    print()
                    print(f"{Colors.GRAY}Refreshing in {refresh_interval}s... (Press Ctrl+C to stop){Colors.NC}")
                    time.sleep(refresh_interval)
                else:
                    break
        
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.NC}")
            return True
        
        return True
    
    def list_recent_jobs(self, active_only: bool = True):
        """List recent jobs from the AWS Batch queue."""
        queue_desc = f"active jobs from queue" if active_only else f"recent jobs from queue"
        print(f"{Colors.BLUE}Recent {queue_desc}: {Colors.CYAN}{AWS_JOB_QUEUE}{Colors.NC}")
        print("=" * 60)
        
        try:
            if active_only:
                jobs_data = self.get_active_jobs()
            else:
                jobs_data = self.get_recent_jobs()
            
            if not jobs_data:
                job_type = "active" if active_only else "recent"
                print(f"{Colors.YELLOW}No {job_type} jobs found in queue{Colors.NC}")
                return
            
            # Filter to only running jobs if active_only is True
            if active_only:
                jobs_data = [job for job in jobs_data if job['status'] == 'RUNNING']
                if not jobs_data:
                    print(f"{Colors.YELLOW}No running jobs found in queue{Colors.NC}")
                    return
            
            print(f"Showing {len(jobs_data)} jobs:")
            print()
            
            # Get complete job status for all jobs
            job_statuses = []
            status_counts = {
                'RUNNING': 0, 'SUCCEEDED': 0, 'FAILED': 0, 
                'PENDING': 0, 'OTHER': 0
            }
            total_with_progress = 0
            total_progress_sum = 0.0
            
            for job_data in jobs_data:
                job_status = self.get_complete_job_status(job_data['jobId'], job_data)
                job_statuses.append(job_status)
                
                # Count status
                if job_status.status == 'RUNNING':
                    status_counts['RUNNING'] += 1
                elif job_status.status == 'SUCCEEDED':
                    status_counts['SUCCEEDED'] += 1
                elif job_status.status == 'FAILED':
                    status_counts['FAILED'] += 1
                elif job_status.status in ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING']:
                    status_counts['PENDING'] += 1
                else:
                    status_counts['OTHER'] += 1
                
                # Track overall progress
                if job_status.status in ["RUNNING", "SUCCEEDED"] and job_status.total > 0:
                    total_with_progress += 1
                    total_progress_sum += job_status.percentage
            
            # Display jobs in table format
            self._display_jobs_table(job_statuses, status_counts, total_with_progress, total_progress_sum)
            
        except Exception as e:
            print(f"{Colors.RED}Error listing jobs: {e}{Colors.NC}")
            print()
            print(f"{Colors.BLUE}Alternative: Use AWS CLI directly:{Colors.NC}")
            print(f"  aws batch list-jobs --job-queue {AWS_JOB_QUEUE} --job-status RUNNING")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Monitor AWS Batch job progress by reading status files from S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List running jobs from queue (default)
  %(prog)s

  # List all recent jobs (including completed/failed)
  %(prog)s --show-all

  # Monitor single job progress
  %(prog)s abc123-def456-ghi789

  # Follow running jobs in real-time
  %(prog)s --follow

  # Follow all jobs (including completed) in real-time
  %(prog)s --follow --show-all

  # Custom refresh interval (every 10 seconds)
  %(prog)s --follow --refresh 10
        """
    )
    
    parser.add_argument(
        'input',
        nargs='?',
        help='Single job ID to monitor. '
             'If not provided, will monitor all jobs from mean-reversion-job-queue'
    )
    parser.add_argument(
        '--follow', '-f',
        action='store_true',
        help='Follow progress in real-time (refreshes every 30s)'
    )
    parser.add_argument(
        '--refresh',
        type=int,
        default=DEFAULT_REFRESH_INTERVAL,
        help=f'Refresh interval in seconds (default: {DEFAULT_REFRESH_INTERVAL})'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Show progress once and exit (default if no --follow)'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )

    parser.add_argument(
        '--active-only',
        action='store_true',
        help='Show only active (non-terminal) jobs'
    )
    parser.add_argument(
        '--show-all',
        action='store_true',
        help='Show all recent jobs (not just running ones)'
    )
    
    args = parser.parse_args()
    
    # Handle follow logic
    if args.refresh != DEFAULT_REFRESH_INTERVAL:
        args.follow = True  # Implied when refresh is specified
    
    if args.once:
        args.follow = False
    
    # Initialize monitor
    monitor = AWSBatchMonitor(use_color=not args.no_color)
    
    if not args.input:
        # No job ID provided - either list recent jobs or monitor queue
        if args.follow:
            # Follow mode - monitor jobs from queue
            # Default to active_only unless --show-all is specified
            active_only = args.active_only or not args.show_all
            monitor.monitor_queue_jobs(
                follow=True, 
                refresh_interval=args.refresh, 
                active_only=active_only
            )
        else:
            # Just list jobs - default to showing only running jobs unless --show-all
            show_active_only = not args.show_all
            monitor.list_recent_jobs(active_only=show_active_only)
        return
    
    # Single job ID provided
    if args.follow:
        # For single job follow, we need to implement a loop
        try:
            while True:
                if args.follow:
                    os.system('clear' if os.name == 'posix' else 'cls')
                
                monitor.monitor_single_job(args.input)
                
                if not args.follow:
                    break
                
                job_status = monitor.get_complete_job_status(args.input)
                if job_status.status in ["SUCCEEDED", "FAILED"]:
                    print()
                    print(f"{Colors.GREEN}Job monitoring complete.{Colors.NC}")
                    break
                
                print()
                print(f"{Colors.GRAY}Refreshing in {args.refresh}s... (Press Ctrl+C to stop){Colors.NC}")
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Monitoring stopped by user{Colors.NC}")
    else:
        monitor.monitor_single_job(args.input)


if __name__ == '__main__':
    main()
