#!/usr/bin/env python3
"""
Telegram Chat Management

This module handles the management of active Telegram chats, including storing
chat IDs in memory, handling user subscriptions, and managing chat state.
"""

import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime

from .telegram_dynamodb_storage import TelegramDynamoDBStorage

logger = logging.getLogger(__name__)


class TelegramChatManager:
    """Class for managing active Telegram chats and user subscriptions"""
    
    def __init__(self, use_dynamodb: bool = True, table_name: str = None, region_name: str = None):
        """Initialize the chat manager
        
        Args:
            use_dynamodb: Whether to use DynamoDB for persistence (default: True)
            table_name: DynamoDB table name (optional)
            region_name: AWS region (optional)
        """
        self.active_chats: Set[int] = set()
        self.chat_metadata: Dict[int, Dict[str, Any]] = {}
        self.use_dynamodb = use_dynamodb
        self.db_storage = None
        
        # Initialize DynamoDB storage if enabled
        if self.use_dynamodb:
            try:
                self.db_storage = TelegramDynamoDBStorage(table_name, region_name)
                # Create table if it doesn't exist
                self.db_storage.create_table_if_not_exists()
                logger.info("Chat manager initialized with DynamoDB storage")
            except Exception as e:
                logger.error(f"Failed to initialize DynamoDB storage, falling back to in-memory: {e}")
                self.use_dynamodb = False
                self.db_storage = None
        
        if not self.use_dynamodb:
            logger.info("Chat manager initialized with in-memory storage only")
    
    def load_chats_from_storage(self) -> int:
        """
        Load active chats from DynamoDB storage
        
        Returns:
            Number of chats loaded
        """
        if not self.use_dynamodb or not self.db_storage:
            logger.info("DynamoDB not configured, skipping chat loading")
            return 0
        
        try:
            # Load active chats
            loaded_chats = self.db_storage.load_active_chats()
            self.active_chats = loaded_chats
            
            # Load metadata
            all_metadata = self.db_storage.load_all_chat_metadata()
            
            # Convert DynamoDB format to internal format
            for chat_id, metadata in all_metadata.items():
                if metadata.get('is_active', False):
                    self.chat_metadata[chat_id] = {
                        'added_at': metadata.get('added_at'),
                        'last_active': metadata.get('last_active'),
                        'message_count': metadata.get('message_count', 0),
                        'user_info': metadata.get('user_info', {}),
                        'status': 'active' if metadata.get('is_active') else 'inactive'
                    }
            
            logger.info(f"Loaded {len(self.active_chats)} active chats from DynamoDB")
            return len(self.active_chats)
            
        except Exception as e:
            logger.error(f"Failed to load chats from DynamoDB: {e}")
            return 0
    
    def add_chat(self, chat_id: int, user_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a new chat to active chats (triggered by /start command)
        
        Args:
            chat_id: Telegram chat ID
            user_info: Optional user information (username, first_name, etc.)
            
        Returns:
            True if chat was newly added, False if already existed
        """
        was_new = chat_id not in self.active_chats
        
        self.active_chats.add(chat_id)
        
        # Update metadata
        current_time = datetime.now().isoformat()
        if chat_id not in self.chat_metadata:
            self.chat_metadata[chat_id] = {
                'added_at': current_time,
                'last_active': current_time,
                'message_count': 0,
                'user_info': user_info or {}
            }
        else:
            self.chat_metadata[chat_id]['last_active'] = current_time
            if user_info:
                self.chat_metadata[chat_id]['user_info'].update(user_info)
        
        # Sync with DynamoDB if enabled
        if self.use_dynamodb and self.db_storage:
            try:
                if self.db_storage.check_chat_exists(chat_id):
                    # Reactivate existing chat
                    self.db_storage.reactivate_chat(chat_id)
                else:
                    # Save new chat
                    self.db_storage.save_chat(chat_id, user_info)
            except Exception as e:
                logger.error(f"Failed to sync chat {chat_id} to DynamoDB: {e}")
        
        if was_new:
            logger.info(f"Added new chat: {chat_id}")
            if user_info:
                username = user_info.get('username', 'Unknown')
                first_name = user_info.get('first_name', 'Unknown')
                logger.info(f"  User: @{username} ({first_name})")
        else:
            logger.debug(f"Chat {chat_id} already active, updated metadata")
        
        return was_new
    
    def remove_chat(self, chat_id: int) -> bool:
        """
        Remove a chat from active chats (triggered by /stop command)
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if chat was removed, False if didn't exist
        """
        if chat_id in self.active_chats:
            self.active_chats.remove(chat_id)
            
            # Update metadata but keep it for reference
            if chat_id in self.chat_metadata:
                self.chat_metadata[chat_id]['removed_at'] = datetime.now().isoformat()
                self.chat_metadata[chat_id]['status'] = 'inactive'
            
            # Sync with DynamoDB if enabled
            if self.use_dynamodb and self.db_storage:
                try:
                    self.db_storage.deactivate_chat(chat_id)
                except Exception as e:
                    logger.error(f"Failed to deactivate chat {chat_id} in DynamoDB: {e}")
            
            logger.info(f"Removed chat: {chat_id}")
            return True
        
        return False
    
    def is_chat_active(self, chat_id: int) -> bool:
        """
        Check if a chat is active
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if chat is active
        """
        return chat_id in self.active_chats
    
    def get_active_chats(self) -> Set[int]:
        """
        Get set of all active chat IDs
        
        Returns:
            Set of active chat IDs
        """
        return self.active_chats.copy()
    
    def get_active_chat_count(self) -> int:
        """
        Get count of active chats
        
        Returns:
            Number of active chats
        """
        return len(self.active_chats)
    
    def update_chat_activity(self, chat_id: int, message_type: str = 'command'):
        """
        Update last activity for a chat
        
        Args:
            chat_id: Telegram chat ID
            message_type: Type of activity (command, signal, etc.)
        """
        if chat_id in self.chat_metadata:
            self.chat_metadata[chat_id]['last_active'] = datetime.now().isoformat()
            self.chat_metadata[chat_id]['message_count'] += 1
            
            # Track message types
            if 'activity_log' not in self.chat_metadata[chat_id]:
                self.chat_metadata[chat_id]['activity_log'] = {}
            
            activity_log = self.chat_metadata[chat_id]['activity_log']
            activity_log[message_type] = activity_log.get(message_type, 0) + 1
            
            # Sync with DynamoDB if enabled
            if self.use_dynamodb and self.db_storage:
                try:
                    self.db_storage.update_chat_activity(
                        chat_id, 
                        increment_message_count=True
                    )
                except Exception as e:
                    logger.error(f"Failed to update activity for chat {chat_id} in DynamoDB: {e}")
    
    def get_chat_info(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific chat
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Chat metadata or None if not found
        """
        return self.chat_metadata.get(chat_id)
    
    def get_all_chat_info(self) -> Dict[int, Dict[str, Any]]:
        """
        Get metadata for all chats
        
        Returns:
            Dictionary mapping chat IDs to metadata
        """
        return self.chat_metadata.copy()
    
    def cleanup_inactive_chats(self, days_threshold: int = 30):
        """
        Clean up chats that have been inactive for a specified number of days
        
        Args:
            days_threshold: Number of days of inactivity before cleanup
        """
        current_time = datetime.now()
        chats_to_remove = []
        
        for chat_id, metadata in self.chat_metadata.items():
            if chat_id not in self.active_chats:
                continue
            
            last_active_str = metadata.get('last_active')
            if last_active_str:
                try:
                    last_active = datetime.fromisoformat(last_active_str)
                    days_inactive = (current_time - last_active).days
                    
                    if days_inactive > days_threshold:
                        chats_to_remove.append(chat_id)
                except ValueError:
                    logger.warning(f"Invalid date format for chat {chat_id}: {last_active_str}")
        
        # Remove inactive chats
        for chat_id in chats_to_remove:
            self.remove_chat(chat_id)
            logger.info(f"Cleaned up inactive chat: {chat_id}")
        
        if chats_to_remove:
            logger.info(f"Cleaned up {len(chats_to_remove)} inactive chats")
        
        return len(chats_to_remove)
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about chat usage
        
        Returns:
            Dictionary with chat statistics
        """
        stats = {
            'total_active_chats': len(self.active_chats),
            'total_registered_chats': len(self.chat_metadata),
            'inactive_chats': len(self.chat_metadata) - len(self.active_chats),
            'total_messages_sent': sum(
                metadata.get('message_count', 0) 
                for metadata in self.chat_metadata.values()
            ),
            'average_messages_per_chat': 0,
            'storage_type': 'DynamoDB' if self.use_dynamodb else 'In-Memory'
        }
        
        if stats['total_registered_chats'] > 0:
            stats['average_messages_per_chat'] = stats['total_messages_sent'] / stats['total_registered_chats']
        
        # Activity breakdown
        activity_breakdown = {}
        for metadata in self.chat_metadata.values():
            activity_log = metadata.get('activity_log', {})
            for activity_type, count in activity_log.items():
                activity_breakdown[activity_type] = activity_breakdown.get(activity_type, 0) + count
        
        stats['activity_breakdown'] = activity_breakdown
        
        # Add DynamoDB statistics if available
        if self.use_dynamodb and self.db_storage:
            try:
                db_stats = self.db_storage.get_statistics()
                stats['dynamodb_stats'] = db_stats
            except Exception as e:
                logger.error(f"Failed to get DynamoDB statistics: {e}")
                stats['dynamodb_stats'] = {'error': str(e)}
        
        return stats
