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

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class TelegramDynamoDBStorage:
    """DynamoDB storage manager for Telegram chat IDs and metadata"""
    
    def __init__(self, table_name: str = None, region_name: str = None):
        """
        Initialize DynamoDB storage
        
        Args:
            table_name: DynamoDB table name (defaults to env var TELEGRAM_CHATS_TABLE)
            region_name: AWS region (defaults to env var AWS_REGION or us-east-1)
        """
        self.table_name = table_name or os.getenv('TELEGRAM_CHATS_TABLE', 'telegram-chats')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize DynamoDB client and resource
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
            self.table = self.dynamodb.Table(self.table_name)
            logger.info(f"Connected to DynamoDB table: {self.table_name} in region {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            raise
    
    def create_table_if_not_exists(self):
        """Create DynamoDB table if it doesn't exist"""
        try:
            # Check if table exists
            self.table.load()
            logger.info(f"Table {self.table_name} already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Table doesn't exist, create it
                logger.info(f"Creating DynamoDB table: {self.table_name}")
                try:
                    table = self.dynamodb.create_table(
                        TableName=self.table_name,
                        KeySchema=[
                            {
                                'AttributeName': 'chat_id',
                                'KeyType': 'HASH'  # Partition key
                            }
                        ],
                        AttributeDefinitions=[
                            {
                                'AttributeName': 'chat_id',
                                'AttributeType': 'N'  # Number type for chat ID
                            }
                        ],
                        BillingMode='PAY_PER_REQUEST'  # On-demand pricing
                    )
                    
                    # Wait for table to be created
                    table.wait_until_exists()
                    logger.info(f"Successfully created table: {self.table_name}")
                    return True
                except ClientError as create_error:
                    logger.error(f"Failed to create table: {create_error}")
                    return False
            else:
                logger.error(f"Error checking table existence: {e}")
                return False
    
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
            
            # Put item to DynamoDB
            self.table.put_item(Item=item)
            logger.info(f"Saved chat {chat_id} to DynamoDB")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to save chat {chat_id} to DynamoDB: {e}")
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
            
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.debug(f"Updated activity for chat {chat_id}")
            return True
            
        except ClientError as e:
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
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression="SET is_active = :inactive, removed_at = :now",
                ExpressionAttributeValues={
                    ':inactive': False,
                    ':now': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Deactivated chat {chat_id} in DynamoDB")
            return True
            
        except ClientError as e:
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
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression="SET is_active = :active, last_active = :now REMOVE removed_at",
                ExpressionAttributeValues={
                    ':active': True,
                    ':now': datetime.now(timezone.utc).isoformat()
                }
            )
            
            logger.info(f"Reactivated chat {chat_id} in DynamoDB")
            return True
            
        except ClientError as e:
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
            # Scan table for active chats
            response = self.table.scan(
                FilterExpression='is_active = :active',
                ExpressionAttributeValues={
                    ':active': True
                },
                ProjectionExpression='chat_id'
            )
            
            # Process results
            for item in response.get('Items', []):
                chat_id = int(item.get('chat_id', 0))
                if chat_id:
                    active_chats.add(chat_id)
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='is_active = :active',
                    ExpressionAttributeValues={
                        ':active': True
                    },
                    ProjectionExpression='chat_id',
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response.get('Items', []):
                    chat_id = int(item.get('chat_id', 0))
                    if chat_id:
                        active_chats.add(chat_id)
            
            logger.info(f"Loaded {len(active_chats)} active chats from DynamoDB")
            return active_chats
            
        except ClientError as e:
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
            # Scan entire table
            response = self.table.scan()
            
            # Process results
            for item in response.get('Items', []):
                chat_id = int(item.get('chat_id', 0))
                if chat_id:
                    # Convert Decimal to int/float for JSON compatibility
                    if 'message_count' in item and isinstance(item['message_count'], Decimal):
                        item['message_count'] = int(item['message_count'])
                    
                    chat_metadata[chat_id] = item
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                
                for item in response.get('Items', []):
                    chat_id = int(item.get('chat_id', 0))
                    if chat_id:
                        if 'message_count' in item and isinstance(item['message_count'], Decimal):
                            item['message_count'] = int(item['message_count'])
                        chat_metadata[chat_id] = item
            
            logger.info(f"Loaded metadata for {len(chat_metadata)} chats from DynamoDB")
            return chat_metadata
            
        except ClientError as e:
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
            response = self.table.get_item(
                Key={'chat_id': chat_id}
            )
            
            item = response.get('Item')
            if item:
                # Convert Decimal to int/float
                if 'message_count' in item and isinstance(item['message_count'], Decimal):
                    item['message_count'] = int(item['message_count'])
                return item
            
            return None
            
        except ClientError as e:
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
            response = self.table.get_item(
                Key={'chat_id': chat_id},
                ProjectionExpression='chat_id'
            )
            return 'Item' in response
            
        except ClientError as e:
            logger.error(f"Failed to check if chat {chat_id} exists: {e}")
            return False