"""
AWS S3 transport implementation for storing and retrieving files.
"""

import os
import pickle
import json
import io
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import logging

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .transport import TransportInterface

logger = logging.getLogger(__name__)


class S3Transport(TransportInterface):
    """AWS S3 transport implementation."""
    
    def __init__(self, bucket_name: str, prefix: str = "", 
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 region_name: str = 'us-east-1'):
        """
        Initialize S3 transport.
        
        Args:
            bucket_name: S3 bucket name
            prefix: Optional prefix for all keys (e.g., 'mean-reversion-strat/')
            aws_access_key_id: AWS access key (uses env vars if None)
            aws_secret_access_key: AWS secret key (uses env vars if None)
            region_name: AWS region
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3Transport. Install with: pip install boto3")
        
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip('/') + '/' if prefix else ''
        
        # Initialize S3 client
        session_kwargs = {'region_name': region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key_id,
                'aws_secret_access_key': aws_secret_access_key
            })
        
        try:
            session = boto3.Session(**session_kwargs)
            self.s3_client = session.client('s3')
            
            # Test connection
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"S3Transport initialized: s3://{bucket_name}/{self.prefix}")
            
        except NoCredentialsError:
            raise ValueError("AWS credentials not found. Please configure AWS credentials.")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise ValueError(f"S3 bucket '{bucket_name}' not found")
            else:
                raise ValueError(f"Error connecting to S3: {e}")
    
    def _get_s3_key(self, key: str) -> str:
        """Convert key to S3 object key with prefix."""
        clean_key = key.strip('/')
        return f"{self.prefix}{clean_key}"
    
    def exists(self, key: str) -> bool:
        """Check if a file exists at the given key."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=self._get_s3_key(key))
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking if {key} exists: {e}")
                return False
    
    def save_pickle(self, key: str, data: Any) -> bool:
        """Save data as pickle file."""
        try:
            # Serialize to bytes
            buffer = io.BytesIO()
            pickle.dump(data, buffer, protocol=pickle.HIGHEST_PROTOCOL)
            buffer.seek(0)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                buffer, 
                self.bucket_name, 
                self._get_s3_key(key),
                ExtraArgs={'ContentType': 'application/octet-stream'}
            )
            
            logger.debug(f"Saved pickle to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving pickle to S3 {key}: {e}")
            return False
    
    def load_pickle(self, key: str) -> Optional[Any]:
        """Load pickle data from key."""
        try:
            buffer = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, self._get_s3_key(key), buffer)
            buffer.seek(0)
            
            data = pickle.load(buffer)
            logger.debug(f"Loaded pickle from S3: {key}")
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            else:
                logger.error(f"Error loading pickle from S3 {key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error loading pickle from S3 {key}: {e}")
            return None
    
    def save_text(self, key: str, content: str) -> bool:
        """Save text content to key."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self._get_s3_key(key),
                Body=content.encode('utf-8'),
                ContentType='text/plain'
            )
            
            logger.debug(f"Saved text to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving text to S3 {key}: {e}")
            return False
    
    def load_text(self, key: str) -> Optional[str]:
        """Load text content from key."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self._get_s3_key(key))
            content = response['Body'].read().decode('utf-8')
            
            logger.debug(f"Loaded text from S3: {key}")
            return content
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            else:
                logger.error(f"Error loading text from S3 {key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error loading text from S3 {key}: {e}")
            return None
    
    def save_json(self, key: str, data: Dict[str, Any]) -> bool:
        """Save JSON data to key."""
        try:
            json_content = json.dumps(data, indent=2, default=str)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self._get_s3_key(key),
                Body=json_content.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.debug(f"Saved JSON to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving JSON to S3 {key}: {e}")
            return False
    
    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Load JSON data from key."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self._get_s3_key(key))
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            logger.debug(f"Loaded JSON from S3: {key}")
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            else:
                logger.error(f"Error loading JSON from S3 {key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error loading JSON from S3 {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete file at key."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=self._get_s3_key(key))
            logger.debug(f"Deleted from S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting from S3 {key}: {e}")
            return False
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with given prefix."""
        try:
            keys = []
            s3_prefix = self._get_s3_key(prefix)
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Remove our internal prefix to get the user key
                        key = obj['Key']
                        if key.startswith(self.prefix):
                            user_key = key[len(self.prefix):]
                            keys.append(user_key)
            
            return sorted(keys)
        except Exception as e:
            logger.error(f"Error listing S3 keys with prefix '{prefix}': {e}")
            return []
    
    def get_info(self) -> Dict[str, Any]:
        """Get transport information (size, file count, etc.)."""
        try:
            total_size = 0
            total_files = 0
            files_info = []
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_files += 1
                        size = obj['Size']
                        total_size += size
                        
                        # Calculate age
                        modified_time = obj['LastModified']
                        if modified_time.tzinfo is None:
                            modified_time = modified_time.replace(tzinfo=timezone.utc)
                        
                        age_hours = (datetime.now(timezone.utc) - modified_time).total_seconds() / 3600
                        
                        # Remove our internal prefix to get the user key
                        key = obj['Key']
                        if key.startswith(self.prefix):
                            user_key = key[len(self.prefix):]
                        else:
                            user_key = key
                        
                        files_info.append({
                            'key': user_key,
                            'size_bytes': size,
                            'age_hours': age_hours,
                            'modified_time': modified_time.isoformat()
                        })
            
            return {
                'transport_type': 's3',
                'bucket': self.bucket_name,
                'prefix': self.prefix,
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'files': files_info
            }
        except Exception as e:
            logger.error(f"Error getting S3 transport info: {e}")
            return {'transport_type': 's3', 'error': str(e)}
    
    def cleanup(self, max_age_days: int = 30) -> int:
        """Clean up old files, return number of files deleted."""
        try:
            deleted_count = 0
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            # List objects to delete
            objects_to_delete = []
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        modified_time = obj['LastModified']
                        if modified_time.tzinfo is None:
                            modified_time = modified_time.replace(tzinfo=timezone.utc)
                        
                        if modified_time < cutoff_time:
                            objects_to_delete.append({'Key': obj['Key']})
            
            # Delete objects in batches (S3 limit is 1000 per request)
            batch_size = 1000
            for i in range(0, len(objects_to_delete), batch_size):
                batch = objects_to_delete[i:i + batch_size]
                
                if batch:
                    response = self.s3_client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': batch}
                    )
                    
                    deleted_count += len(response.get('Deleted', []))
                    
                    if 'Errors' in response:
                        for error in response['Errors']:
                            logger.error(f"Error deleting S3 object {error['Key']}: {error['Message']}")
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old files from S3")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Error during S3 cleanup: {e}")
            return 0
