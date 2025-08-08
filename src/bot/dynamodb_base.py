#!/usr/bin/env python3
"""
Base DynamoDB Storage Class

This module provides a base class for DynamoDB operations that can be inherited
by specific storage implementations (Telegram chats, signal cache, etc.)
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class DynamoDBBase:
    """Base class for DynamoDB operations"""
    
    def __init__(self, table_name: str = None, region_name: str = None):
        """
        Initialize DynamoDB base
        
        Args:
            table_name: DynamoDB table name
            region_name: AWS region (defaults to env var AWS_REGION or us-east-1)
        """
        self.table_name = table_name
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize DynamoDB client and resource
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region_name)
            self.dynamodb_client = boto3.client('dynamodb', region_name=self.region_name)
            if self.table_name:
                self.table = self.dynamodb.Table(self.table_name)
                logger.info(f"Connected to DynamoDB table: {self.table_name} in region {self.region_name}")
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB: {e}")
            raise
    
    def table_exists(self, table_name: str = None) -> bool:
        """
        Check if a table exists
        
        Args:
            table_name: Table name to check (defaults to self.table_name)
            
        Returns:
            True if table exists, False otherwise
        """
        table_to_check = table_name or self.table_name
        if not table_to_check:
            return False
            
        try:
            table = self.dynamodb.Table(table_to_check)
            table.load()
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            logger.error(f"Error checking table existence: {e}")
            return False
    
    def create_table(self, table_name: str, key_schema: List[Dict], 
                    attribute_definitions: List[Dict], 
                    ttl_attribute: Optional[str] = None,
                    billing_mode: str = 'PAY_PER_REQUEST') -> bool:
        """
        Create a DynamoDB table
        
        Args:
            table_name: Name of the table to create
            key_schema: Key schema definition
            attribute_definitions: Attribute definitions
            ttl_attribute: Optional TTL attribute name for automatic expiration
            billing_mode: Billing mode (PAY_PER_REQUEST or PROVISIONED)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create table
            table = self.dynamodb.create_table(
                TableName=table_name,
                KeySchema=key_schema,
                AttributeDefinitions=attribute_definitions,
                BillingMode=billing_mode
            )
            
            # Wait for table to be created
            table.wait_until_exists()
            logger.info(f"Successfully created table: {table_name}")
            
            # Enable TTL if specified
            if ttl_attribute:
                self.enable_ttl(table_name, ttl_attribute)
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table {table_name} already exists")
                return True
            logger.error(f"Failed to create table: {e}")
            return False
    
    def enable_ttl(self, table_name: str, ttl_attribute: str) -> bool:
        """
        Enable TTL (Time To Live) on a table
        
        Args:
            table_name: Table name
            ttl_attribute: Attribute name to use for TTL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.dynamodb_client.update_time_to_live(
                TableName=table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': ttl_attribute
                }
            )
            logger.info(f"TTL enabled on {table_name} using attribute {ttl_attribute}")
            return True
        except ClientError as e:
            if 'ValidationException' in str(e):
                # TTL might already be enabled
                logger.info(f"TTL already configured on {table_name}")
                return True
            logger.error(f"Failed to enable TTL: {e}")
            return False
    
    def put_item(self, item: Dict[str, Any], table_name: str = None) -> bool:
        """
        Put an item into DynamoDB
        
        Args:
            item: Item to store
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name) if table_name else self.table
            table.put_item(Item=item)
            return True
        except ClientError as e:
            logger.error(f"Failed to put item: {e}")
            return False
    
    def get_item(self, key: Dict[str, Any], table_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Get an item from DynamoDB
        
        Args:
            key: Primary key of the item
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            Item if found, None otherwise
        """
        try:
            table = self.dynamodb.Table(table_name) if table_name else self.table
            response = table.get_item(Key=key)
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Failed to get item: {e}")
            return None
    
    def update_item(self, key: Dict[str, Any], update_expression: str,
                   expression_values: Dict[str, Any], 
                   condition_expression: str = None,
                   table_name: str = None) -> bool:
        """
        Update an item in DynamoDB
        
        Args:
            key: Primary key of the item
            update_expression: Update expression
            expression_values: Expression attribute values
            condition_expression: Optional condition expression
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name) if table_name else self.table
            
            kwargs = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values
            }
            
            if condition_expression:
                kwargs['ConditionExpression'] = condition_expression
            
            table.update_item(**kwargs)
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.debug(f"Condition check failed for update: {e}")
            else:
                logger.error(f"Failed to update item: {e}")
            return False
    
    def delete_item(self, key: Dict[str, Any], table_name: str = None) -> bool:
        """
        Delete an item from DynamoDB
        
        Args:
            key: Primary key of the item
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            table = self.dynamodb.Table(table_name) if table_name else self.table
            table.delete_item(Key=key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete item: {e}")
            return False
    
    def scan_with_filter(self, filter_expression: Any = None, 
                        projection_expression: str = None,
                        table_name: str = None) -> List[Dict[str, Any]]:
        """
        Scan table with optional filter
        
        Args:
            filter_expression: Optional filter expression
            projection_expression: Optional projection expression
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            List of items
        """
        items = []
        
        try:
            table = self.dynamodb.Table(table_name) if table_name else self.table
            
            # Build scan kwargs
            scan_kwargs = {}
            if filter_expression:
                scan_kwargs['FilterExpression'] = filter_expression
            if projection_expression:
                scan_kwargs['ProjectionExpression'] = projection_expression
            
            # Initial scan
            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                response = table.scan(**scan_kwargs)
                items.extend(response.get('Items', []))
            
            return items
            
        except ClientError as e:
            logger.error(f"Failed to scan table: {e}")
            return []
    
    def query_by_key(self, key_condition: Any, filter_expression: Any = None,
                    projection_expression: str = None, 
                    scan_forward: bool = True,
                    limit: int = None,
                    table_name: str = None) -> List[Dict[str, Any]]:
        """
        Query table by key condition
        
        Args:
            key_condition: Key condition expression
            filter_expression: Optional filter expression
            projection_expression: Optional projection expression
            scan_forward: Sort order (True for ascending, False for descending)
            limit: Maximum number of items to return
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            List of items
        """
        items = []
        
        try:
            table = self.dynamodb.Table(table_name) if table_name else self.table
            
            # Build query kwargs
            query_kwargs = {
                'KeyConditionExpression': key_condition,
                'ScanIndexForward': scan_forward
            }
            
            if filter_expression:
                query_kwargs['FilterExpression'] = filter_expression
            if projection_expression:
                query_kwargs['ProjectionExpression'] = projection_expression
            if limit:
                query_kwargs['Limit'] = limit
            
            # Execute query
            response = table.query(**query_kwargs)
            items.extend(response.get('Items', []))
            
            # Handle pagination if no limit specified
            if not limit:
                while 'LastEvaluatedKey' in response:
                    query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                    response = table.query(**query_kwargs)
                    items.extend(response.get('Items', []))
            
            return items
            
        except ClientError as e:
            logger.error(f"Failed to query table: {e}")
            return []
    
    def batch_write_items(self, items: List[Dict[str, Any]], 
                         table_name: str = None) -> bool:
        """
        Batch write multiple items to DynamoDB
        
        Args:
            items: List of items to write
            table_name: Optional table name (defaults to self.table_name)
            
        Returns:
            True if all items written successfully, False otherwise
        """
        if not items:
            return True
            
        table_name = table_name or self.table_name
        
        try:
            # Process in batches of 25 (DynamoDB limit)
            for i in range(0, len(items), 25):
                batch = items[i:i+25]
                
                with self.table.batch_writer() as batch_writer:
                    for item in batch:
                        batch_writer.put_item(Item=item)
            
            logger.info(f"Successfully wrote {len(items)} items in batch")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to batch write items: {e}")
            return False
    
    def convert_decimal_to_number(self, obj: Any) -> Any:
        """
        Convert DynamoDB Decimal types to Python int/float
        
        Args:
            obj: Object to convert
            
        Returns:
            Converted object
        """
        if isinstance(obj, list):
            return [self.convert_decimal_to_number(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.convert_decimal_to_number(v) for k, v in obj.items()}
        elif isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        else:
            return obj