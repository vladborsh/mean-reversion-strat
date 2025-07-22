"""
Transport factory for creating appropriate transport instances based on configuration.
"""

import os
from typing import Optional
from pathlib import Path
import logging

from .transport import TransportInterface, LocalTransport
from .s3_transport import S3Transport

logger = logging.getLogger(__name__)


def create_cache_transport(base_dir: Optional[str] = None, transport_type: Optional[str] = None) -> TransportInterface:
    """
    Create cache transport based on transport_type parameter or CACHE_TRANSPORT environment variable.
    
    Args:
        base_dir: Base directory for local transport (optional)
        transport_type: Transport type ('local' or 's3'). If None, uses CACHE_TRANSPORT env var.
    
    Returns:
        TransportInterface: Configured transport instance
    """
    if transport_type is None:
        transport_type = os.getenv('CACHE_TRANSPORT', 'local')
    transport_type = transport_type.lower()
    
    if transport_type == 's3':
        # S3 configuration
        bucket = os.getenv('AWS_S3_BUCKET')
        if not bucket:
            logger.warning("AWS_S3_BUCKET not set, falling back to local cache transport")
            transport_type = 'local'
        else:
            prefix = os.getenv('AWS_S3_PREFIX', 'mean-reversion-strat/')
            if not prefix.endswith('/'):
                prefix += '/'
            prefix += 'cache/'
            
            try:
                return S3Transport(
                    bucket_name=bucket,
                    prefix=prefix,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
            except Exception as e:
                logger.error(f"Failed to create S3 cache transport: {e}")
                logger.warning("Falling back to local cache transport")
                transport_type = 'local'
    
    # Default to local transport
    if base_dir is None:
        project_root = Path(__file__).parent.parent
        base_dir = project_root / 'cache'
    
    return LocalTransport(base_dir)


def create_log_transport(base_dir: Optional[str] = None, transport_type: Optional[str] = None) -> TransportInterface:
    """
    Create log transport based on transport_type parameter or LOG_TRANSPORT environment variable.
    
    Args:
        base_dir: Base directory for local transport (optional)
        transport_type: Transport type ('local' or 's3'). If None, uses LOG_TRANSPORT env var.
    
    Returns:
        TransportInterface: Configured transport instance
    """
    if transport_type is None:
        transport_type = os.getenv('LOG_TRANSPORT', 'local')
    transport_type = transport_type.lower()
    
    if transport_type == 's3':
        # S3 configuration
        bucket = os.getenv('AWS_S3_BUCKET')
        if not bucket:
            logger.warning("AWS_S3_BUCKET not set, falling back to local log transport")
            transport_type = 'local'
        else:
            prefix = os.getenv('AWS_S3_PREFIX', 'mean-reversion-strat/')
            if not prefix.endswith('/'):
                prefix += '/'
            prefix += 'logs/'
            
            try:
                return S3Transport(
                    bucket_name=bucket,
                    prefix=prefix,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
            except Exception as e:
                logger.error(f"Failed to create S3 log transport: {e}")
                logger.warning("Falling back to local log transport")
                transport_type = 'local'
    
    # Default to local transport
    if base_dir is None:
        project_root = Path(__file__).parent.parent
        base_dir = project_root / 'optimization'
    
    return LocalTransport(base_dir)


def create_optimization_transport(optimization_dir: Optional[str] = None, transport_type: Optional[str] = None) -> TransportInterface:
    """
    Create optimization transport for logs, results, plots, etc.
    
    Args:
        optimization_dir: Base optimization directory for local transport (optional)
        transport_type: Transport type ('local' or 's3'). If None, uses LOG_TRANSPORT env var.
    
    Returns:
        TransportInterface: Configured transport instance
    """
    if transport_type is None:
        transport_type = os.getenv('LOG_TRANSPORT', 'local')
    transport_type = transport_type.lower()
    
    if transport_type == 's3':
        # S3 configuration
        bucket = os.getenv('AWS_S3_BUCKET')
        if not bucket:
            logger.warning("AWS_S3_BUCKET not set, falling back to local optimization transport")
            transport_type = 'local'
        else:
            prefix = os.getenv('AWS_S3_PREFIX', 'mean-reversion-strat/')
            if not prefix.endswith('/'):
                prefix += '/'
            prefix += 'optimization/'
            
            try:
                return S3Transport(
                    bucket_name=bucket,
                    prefix=prefix,
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
            except Exception as e:
                logger.error(f"Failed to create S3 optimization transport: {e}")
                logger.warning("Falling back to local optimization transport")
                transport_type = 'local'
    
    # Default to local transport
    if optimization_dir is None:
        project_root = Path(__file__).parent.parent
        optimization_dir = project_root / 'optimization'
    
    return LocalTransport(optimization_dir)
