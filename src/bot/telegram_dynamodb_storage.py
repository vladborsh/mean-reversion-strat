#!/usr/bin/env python3
"""
DynamoDB Storage for Telegram Chat IDs

This module provides persistent storage for Telegram chat IDs using AWS DynamoDB.
Chat IDs are saved to DynamoDB and loaded during startup for broadcasting.
"""

import logging
import os
from typing import Set, Dict, Any, Optional, List
from datetime import datetime, timezone
from decimal import Decimal

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

from .dynamodb_base import DynamoDBBase

logger = logging.getLogger(__name__)


class TelegramDynamoDBStorage(DynamoDBBase):
    """DynamoDB storage manager for Telegram chat IDs and metadata"""
    
    def __init__(self, table_name: str = None, region_name: str = None):
        """
        Initialize DynamoDB storage
        
        Args:
            table_name: DynamoDB table name (defaults to env var TELEGRAM_CHATS_TABLE)
            region_name: AWS region (defaults to env var AWS_REGION or us-east-1)
        """
        # Set table name
        table_name = table_name or os.getenv('TELEGRAM_CHATS_TABLE', 'telegram-chats')
        
        # Initialize base class
        super().__init__(table_name=table_name, region_name=region_name)
        
        # Create table if it doesn't exist
        self.create_table_if_not_exists()
    
    def create_table_if_not_exists(self):
        """Create DynamoDB table if it doesn't exist"""
        if not self.table_exists():
            logger.info(f"Creating DynamoDB table: {self.table_name}")
            
            # Create table
            return self.create_table(
                table_name=self.table_name,
                key_schema=[
                    {
                        'AttributeName': 'chat_id',
                        'KeyType': 'HASH'  # Partition key
                    }
                ],
                attribute_definitions=[
                    {
                        'AttributeName': 'chat_id',
                        'AttributeType': 'N'  # Number type for chat ID
                    }
                ],
                billing_mode='PAY_PER_REQUEST'
            )
        else:
            logger.info(f"Table {self.table_name} already exists")
            return True
    
    def save_chat(self, chat_id: int, user_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a chat ID to DynamoDB
        
        Args:
            chat_id: Telegram chat ID
            user_info: Optional user information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            item = {
                'chat_id': chat_id,
                'is_active': True,
                'added_at': datetime.now(timezone.utc).isoformat(),
                'last_active': datetime.now(timezone.utc).isoformat(),
                'message_count': 0
            }
            
            # Add user info if provided
            if user_info:
                item['user_info'] = {
                    k: v for k, v in user_info.items() if v is not None
                }
            
            # Put item to DynamoDB using base class method
            if self.put_item(item):
                logger.info(f"Saved chat {chat_id} to DynamoDB")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to save chat {chat_id}: {e}")
            return False
    
    def update_chat_activity(self, chat_id: int, increment_message_count: bool = False) -> bool:
        """
        Update chat activity timestamp and optionally increment message count
        
        Args:
            chat_id: Telegram chat ID
            increment_message_count: Whether to increment the message count
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_expression = "SET last_active = :now"
            expression_values = {
                ':now': datetime.now(timezone.utc).isoformat()
            }
            
            if increment_message_count:
                update_expression += ", message_count = message_count + :inc"
                expression_values[':inc'] = 1
            
            # Use base class update method
            if self.update_item(
                key={'chat_id': chat_id},
                update_expression=update_expression,
                expression_values=expression_values
            ):
                logger.debug(f"Updated activity for chat {chat_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to update chat {chat_id} activity: {e}")
            return False
    
    def deactivate_chat(self, chat_id: int) -> bool:
        """
        Mark a chat as inactive (soft delete)
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use base class update method
            if self.update_item(
                key={'chat_id': chat_id},
                update_expression="SET is_active = :inactive, removed_at = :now",
                expression_values={
                    ':inactive': False,
                    ':now': datetime.now(timezone.utc).isoformat()
                }
            ):
                logger.info(f"Deactivated chat {chat_id} in DynamoDB")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to deactivate chat {chat_id}: {e}")
            return False
    
    def reactivate_chat(self, chat_id: int) -> bool:
        """
        Reactivate a previously deactivated chat
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use base class update method
            if self.update_item(
                key={'chat_id': chat_id},
                update_expression="SET is_active = :active, last_active = :now REMOVE removed_at",
                expression_values={
                    ':active': True,
                    ':now': datetime.now(timezone.utc).isoformat()
                }
            ):
                logger.info(f"Reactivated chat {chat_id} in DynamoDB")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to reactivate chat {chat_id}: {e}")
            return False
    
    def load_active_chats(self) -> Set[int]:
        """
        Load all active chat IDs from DynamoDB
        
        Returns:
            Set of active chat IDs
        """
        active_chats = set()
        
        try:
            # Use base class scan method
            items = self.scan_with_filter(
                filter_expression=Attr('is_active').eq(True),
                projection_expression='chat_id'
            )
            
            # Process results
            for item in items:
                chat_id = int(item.get('chat_id', 0))
                if chat_id:
                    active_chats.add(chat_id)
            
            logger.info(f"Loaded {len(active_chats)} active chats from DynamoDB")
            return active_chats
            
        except Exception as e:
            logger.error(f"Failed to load active chats from DynamoDB: {e}")
            return set()
    
    def load_all_chat_metadata(self) -> Dict[int, Dict[str, Any]]:
        """
        Load all chat metadata from DynamoDB
        
        Returns:
            Dictionary mapping chat IDs to their metadata
        """
        chat_metadata = {}
        
        try:
            # Use base class scan method (no filter to get all)
            items = self.scan_with_filter()
            
            # Process results
            for item in items:
                # Convert using base class method
                item = self.convert_decimal_to_number(item)
                chat_id = int(item.get('chat_id', 0))
                if chat_id:
                    chat_metadata[chat_id] = item
            
            logger.info(f"Loaded metadata for {len(chat_metadata)} chats from DynamoDB")
            return chat_metadata
            
        except Exception as e:
            logger.error(f"Failed to load chat metadata from DynamoDB: {e}")
            return {}
    
    def get_chat_info(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific chat
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            Chat metadata or None if not found
        """
        try:
            # Use base class get_item method
            item = self.get_item({'chat_id': chat_id})
            
            if item:
                # Convert Decimal types
                return self.convert_decimal_to_number(item)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get info for chat {chat_id}: {e}")
            return None
    
    def check_chat_exists(self, chat_id: int) -> bool:
        """
        Check if a chat exists in DynamoDB
        
        Args:
            chat_id: Telegram chat ID
            
        Returns:
            True if chat exists, False otherwise
        """
        try:
            # Use base class get_item method
            item = self.get_item({'chat_id': chat_id})
            return item is not None
            
        except Exception as e:
            logger.error(f"Failed to check if chat {chat_id} exists: {e}")
            return False
    
    def get_chat_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored chats
        
        Returns:
            Dictionary with chat statistics
        """
        try:
            all_chats = self.load_all_chat_metadata()
            
            active_count = sum(1 for chat in all_chats.values() if chat.get('is_active', False))
            inactive_count = len(all_chats) - active_count
            
            total_messages = sum(chat.get('message_count', 0) for chat in all_chats.values())
            
            stats = {
                'total_chats': len(all_chats),
                'active_chats': active_count,
                'inactive_chats': inactive_count,
                'total_messages_sent': total_messages,
                'average_messages_per_chat': total_messages / len(all_chats) if all_chats else 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get chat statistics: {e}")
            return {}