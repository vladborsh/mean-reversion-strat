#!/usr/bin/env python3
"""
Telemetry File Utilities

Provides atomic file writing, compression, and file rotation utilities
for the file-based telemetry system.
"""

import json
import gzip
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def atomic_write_json(filepath: Path, data: Dict[str, Any], compress: bool = False):
    """
    Atomically write JSON data to file
    
    Uses temp file + rename to ensure atomic writes and prevent partial reads.
    
    Args:
        filepath: Target file path
        data: Data to write
        compress: Whether to compress with gzip
    """
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temp file in same directory (ensures same filesystem for atomic rename)
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=filepath.parent,
            delete=False,
            suffix='.tmp'
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
            if compress:
                # Write compressed JSON
                with gzip.open(tmp_path, 'wt', encoding='utf-8') as gz_file:
                    json.dump(data, gz_file, indent=2, default=str)
            else:
                # Write regular JSON
                json.dump(data, tmp_file, indent=2, default=str)
        
        # Atomic rename (overwrites existing file)
        os.replace(tmp_path, filepath)
        
    except Exception as e:
        logger.error(f"Failed to write {filepath}: {e}")
        # Clean up temp file if it exists
        if 'tmp_path' in locals() and tmp_path.exists():
            tmp_path.unlink()
        raise


def read_json(filepath: Path, compressed: bool = False) -> Dict[str, Any]:
    """
    Read JSON data from file
    
    Args:
        filepath: File path to read
        compressed: Whether file is gzip compressed
        
    Returns:
        Parsed JSON data
    """
    try:
        if not filepath.exists():
            return {}
        
        if compressed:
            with gzip.open(filepath, 'rt', encoding='utf-8') as gz_file:
                return json.load(gz_file)
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
                
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}")
        return {}


def rotate_files(directory: Path, pattern: str, max_count: int, compress_old: bool = True):
    """
    Rotate files in directory, keeping only the most recent files
    
    Args:
        directory: Directory containing files
        pattern: Glob pattern to match files (e.g., "signal_*.json")
        max_count: Maximum number of files to keep
        compress_old: Whether to compress old files before keeping them
    """
    try:
        if not directory.exists():
            return
        
        # Get all matching files sorted by modification time (newest first)
        files = sorted(
            directory.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        if len(files) <= max_count:
            return
        
        # Files to keep (most recent)
        files_to_keep = files[:max_count]
        
        # Files to delete (older)
        files_to_delete = files[max_count:]
        
        # Optionally compress files before deletion
        if compress_old:
            # Compress the oldest files that will be kept
            for file in files_to_keep[-10:]:  # Compress last 10 of kept files
                if not file.name.endswith('.gz'):
                    try:
                        compress_file(file)
                    except Exception as e:
                        logger.warning(f"Failed to compress {file}: {e}")
        
        # Delete old files
        for file in files_to_delete:
            try:
                file.unlink()
                logger.debug(f"Deleted old telemetry file: {file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {file}: {e}")
        
        if files_to_delete:
            logger.info(f"Rotated {len(files_to_delete)} old files from {directory}")
            
    except Exception as e:
        logger.error(f"Failed to rotate files in {directory}: {e}")


def compress_file(filepath: Path):
    """
    Compress a file with gzip and replace original
    
    Args:
        filepath: File to compress
    """
    if filepath.name.endswith('.gz'):
        return  # Already compressed
    
    gz_path = filepath.with_suffix(filepath.suffix + '.gz')
    
    try:
        with open(filepath, 'rb') as f_in:
            with gzip.open(gz_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove original file
        filepath.unlink()
        logger.debug(f"Compressed {filepath.name}")
        
    except Exception as e:
        # Clean up partial compressed file
        if gz_path.exists():
            gz_path.unlink()
        raise


def get_file_mtime(filepath: Path) -> float:
    """
    Get file modification time, returns 0 if file doesn't exist
    
    Args:
        filepath: File path
        
    Returns:
        Modification time as timestamp, or 0 if file doesn't exist
    """
    try:
        if filepath.exists():
            return filepath.stat().st_mtime
        return 0.0
    except Exception:
        return 0.0


def ensure_telemetry_structure(base_path: Path):
    """
    Ensure telemetry directory structure exists
    
    Args:
        base_path: Base telemetry directory
    """
    try:
        base_path.mkdir(parents=True, exist_ok=True)
        (base_path / 'signals').mkdir(exist_ok=True)
        (base_path / 'cycles').mkdir(exist_ok=True)
        (base_path / 'errors').mkdir(exist_ok=True)
        logger.debug(f"Telemetry directory structure ensured at {base_path}")
    except Exception as e:
        logger.error(f"Failed to create telemetry directories: {e}")
        raise


def generate_timestamped_filename(prefix: str, extension: str = 'json') -> str:
    """
    Generate a filename with timestamp and unique identifier
    
    Args:
        prefix: Filename prefix (e.g., 'signal', 'cycle')
        extension: File extension (default: 'json')
        
    Returns:
        Filename string like "signal_20260106_230512_123.json"
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    # Add microseconds for uniqueness
    unique_id = datetime.now(timezone.utc).strftime('%f')[:3]
    return f"{prefix}_{timestamp}_{unique_id}.{extension}"


def list_recent_files(directory: Path, pattern: str, limit: int) -> List[Path]:
    """
    List most recent files matching pattern
    
    Args:
        directory: Directory to search
        pattern: Glob pattern
        limit: Maximum number of files to return
        
    Returns:
        List of file paths sorted by modification time (newest first)
    """
    try:
        if not directory.exists():
            return []
        
        files = sorted(
            directory.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        return files[:limit]
        
    except Exception as e:
        logger.error(f"Failed to list files in {directory}: {e}")
        return []
