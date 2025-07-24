"""
Abstract transport interface for storing and retrieving files.
Provides a unified interface for local filesystem and cloud storage (S3).
"""

import os
import pickle
import json
import pandas as pd
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TransportInterface(ABC):
    """Abstract base class for storage transports."""
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists at the given key."""
        pass
    
    @abstractmethod
    def save_pickle(self, key: str, data: Any) -> bool:
        """Save data as pickle file."""
        pass
    
    @abstractmethod
    def load_pickle(self, key: str) -> Optional[Any]:
        """Load pickle data from key."""
        pass
    
    @abstractmethod
    def save_text(self, key: str, content: str) -> bool:
        """Save text content to key."""
        pass
    
    @abstractmethod
    def load_text(self, key: str) -> Optional[str]:
        """Load text content from key."""
        pass
    
    @abstractmethod
    def save_json(self, key: str, data: Dict[str, Any]) -> bool:
        """Save JSON data to key."""
        pass
    
    @abstractmethod
    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Load JSON data from key."""
        pass
    
    @abstractmethod
    def save_csv(self, key: str, data: Any) -> bool:
        """Save DataFrame as CSV file."""
        pass
    
    @abstractmethod
    def load_csv(self, key: str) -> Optional[Any]:
        """Load CSV data as DataFrame."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete file at key."""
        pass
    
    @abstractmethod
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with given prefix."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get transport information (size, file count, etc.)."""
        pass
    
    @abstractmethod
    def cleanup(self, max_age_days: int = 30) -> int:
        """Clean up old files, return number of files deleted."""
        pass


class LocalTransport(TransportInterface):
    """Local filesystem transport implementation."""
    
    def __init__(self, base_dir: Union[str, Path]):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"LocalTransport initialized with directory: {self.base_dir}")
    
    def _get_path(self, key: str) -> Path:
        """Convert key to filesystem path."""
        # Ensure key doesn't try to escape base directory
        clean_key = key.strip('/').replace('../', '').replace('..\\', '')
        return self.base_dir / clean_key
    
    def exists(self, key: str) -> bool:
        """Check if a file exists at the given key."""
        return self._get_path(key).exists()
    
    def save_pickle(self, key: str, data: Any) -> bool:
        """Save data as pickle file."""
        try:
            file_path = self._get_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.debug(f"Saved pickle to {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving pickle to {key}: {e}")
            return False
    
    def load_pickle(self, key: str) -> Optional[Any]:
        """Load pickle data from key."""
        try:
            file_path = self._get_path(key)
            if not file_path.exists():
                return None
                
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
                
            logger.debug(f"Loaded pickle from {key}")
            return data
        except Exception as e:
            logger.error(f"Error loading pickle from {key}: {e}")
            return None
    
    def save_text(self, key: str, content: str) -> bool:
        """Save text content to key."""
        try:
            file_path = self._get_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Saved text to {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving text to {key}: {e}")
            return False
    
    def load_text(self, key: str) -> Optional[str]:
        """Load text content from key."""
        try:
            file_path = self._get_path(key)
            if not file_path.exists():
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            logger.debug(f"Loaded text from {key}")
            return content
        except Exception as e:
            logger.error(f"Error loading text from {key}: {e}")
            return None
    
    def save_json(self, key: str, data: Dict[str, Any]) -> bool:
        """Save JSON data to key."""
        try:
            file_path = self._get_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved JSON to {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving JSON to {key}: {e}")
            return False
    
    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Load JSON data from key."""
        try:
            file_path = self._get_path(key)
            if not file_path.exists():
                return None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logger.debug(f"Loaded JSON from {key}")
            return data
        except Exception as e:
            logger.error(f"Error loading JSON from {key}: {e}")
            return None
    
    def save_csv(self, key: str, data: pd.DataFrame) -> bool:
        """Save DataFrame as CSV file."""
        try:
            file_path = self._get_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            data.to_csv(file_path, index=False)
            
            logger.debug(f"Saved CSV to {key}")
            return True
        except Exception as e:
            logger.error(f"Error saving CSV to {key}: {e}")
            return False
    
    def load_csv(self, key: str) -> Optional[pd.DataFrame]:
        """Load CSV data as DataFrame."""
        try:
            file_path = self._get_path(key)
            if not file_path.exists():
                return None
                
            data = pd.read_csv(file_path)
            
            logger.debug(f"Loaded CSV from {key}")
            return data
        except Exception as e:
            logger.error(f"Error loading CSV from {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete file at key."""
        try:
            file_path = self._get_path(key)
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {key}: {e}")
            return False
    
    def list_keys(self, prefix: str = "") -> List[str]:
        """List all keys with given prefix."""
        try:
            keys = []
            search_path = self._get_path(prefix) if prefix else self.base_dir
            
            if search_path.is_file():
                return [prefix] if prefix else []
            
            if search_path.is_dir():
                for file_path in search_path.rglob('*'):
                    if file_path.is_file():
                        # Convert back to relative key
                        relative_path = file_path.relative_to(self.base_dir)
                        keys.append(str(relative_path).replace('\\', '/'))
            
            return sorted(keys)
        except Exception as e:
            logger.error(f"Error listing keys with prefix '{prefix}': {e}")
            return []
    
    def get_info(self) -> Dict[str, Any]:
        """Get transport information (size, file count, etc.)."""
        try:
            total_size = 0
            total_files = 0
            files_info = []
            
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file():
                    total_files += 1
                    size = file_path.stat().st_size
                    total_size += size
                    
                    # Get file age
                    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    age_hours = (datetime.now() - modified_time).total_seconds() / 3600
                    
                    files_info.append({
                        'key': str(file_path.relative_to(self.base_dir)).replace('\\', '/'),
                        'size_bytes': size,
                        'age_hours': age_hours,
                        'modified_time': modified_time.isoformat()
                    })
            
            return {
                'transport_type': 'local',
                'base_directory': str(self.base_dir),
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'files': files_info
            }
        except Exception as e:
            logger.error(f"Error getting transport info: {e}")
            return {'transport_type': 'local', 'error': str(e)}
    
    def cleanup(self, max_age_days: int = 30) -> int:
        """Clean up old files, return number of files deleted."""
        try:
            deleted_count = 0
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
            
            for file_path in self.base_dir.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
