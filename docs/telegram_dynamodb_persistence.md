# Telegram Bot DynamoDB Persistence

## Overview

The Telegram bot now supports persistent storage of chat IDs using AWS DynamoDB. This ensures that registered users continue receiving trading signals even after bot restarts or deployments.

## Features

- **Automatic Chat Persistence**: Chat IDs are automatically saved to DynamoDB when users send `/start` or any message
- **Auto-Registration**: New chats are automatically registered when they send any message (configurable)
- **Chat Loading on Startup**: All active chats are loaded from DynamoDB during bot initialization
- **Soft Delete**: Chats are marked as inactive (not deleted) when users send `/stop`
- **Activity Tracking**: Last activity timestamps and message counts are tracked
- **Automatic Cleanup**: Inactive chats can be cleaned up after a specified period
- **Fallback Mode**: Falls back to in-memory storage if DynamoDB is unavailable

## DynamoDB Table Structure

The system creates a DynamoDB table with the following schema:

- **Table Name**: `telegram-chats` (configurable via `TELEGRAM_CHATS_TABLE` env var)
- **Primary Key**: `chat_id` (Number)
- **Billing Mode**: Pay-per-request (on-demand)

### Item Attributes

```json
{
  "chat_id": 123456789,
  "is_active": true,
  "added_at": "2024-01-15T10:30:00Z",
  "last_active": "2024-01-15T14:45:00Z",
  "message_count": 42,
  "user_info": {
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "user_id": 987654321
  },
  "removed_at": null
}
```

## Configuration

### Environment Variables

```bash
# Required for Telegram bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional DynamoDB configuration
TELEGRAM_CHATS_TABLE=telegram-chats  # Default: telegram-chats
AWS_REGION=us-east-1                  # Default: us-east-1
TELEGRAM_AUTO_REGISTER=true           # Default: true (auto-register new chats)

# AWS credentials (required for DynamoDB)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### Programmatic Configuration

```python
from src.bot.telegram_bot import MeanReversionTelegramBot

# Create bot with DynamoDB persistence and auto-registration
bot = MeanReversionTelegramBot(
    bot_token="your_token",
    use_dynamodb=True,              # Enable DynamoDB (default: True)
    table_name="telegram-chats",    # Optional custom table name
    region_name="us-east-1",         # Optional AWS region
    auto_register_chats=True         # Auto-register on any message (default: True)
)

# Initialize bot (loads existing chats)
await bot.initialize()

# Start bot
await bot.start_bot()
```

## Usage

### Auto-Registration Behavior

With auto-registration enabled (default), the bot will:

1. **On any message from a new chat**: Automatically register the chat and save to DynamoDB
2. **On `/start` command**: Register the chat with a welcome message
3. **On `/stop` command**: Mark the chat as inactive (soft delete)
4. **On bot restart**: Load all active chats from DynamoDB

This ensures users don't need to explicitly send `/start` - any interaction registers them for signals.

### Starting the Bot with Persistence

```python
from src.bot.telegram_bot import create_telegram_bot_from_env

# Create bot with auto-registration and DynamoDB enabled
bot = create_telegram_bot_from_env(
    use_dynamodb=True,           # Enable DynamoDB persistence
    auto_register_chats=True     # Auto-register on any message
)

# Initialize (loads chats from DynamoDB)
await bot.initialize()

# The bot now has all previously registered chats loaded
# and will persist new registrations automatically
```

### Testing the Persistence

Run the test script to verify DynamoDB persistence:

```bash
python test_telegram_persistence.py
```

This will:
1. Connect to DynamoDB
2. Load existing chats
3. Display statistics
4. Send a test broadcast to all registered chats

### Manual Chat Management

```python
from src.bot.telegram_dynamodb_storage import TelegramDynamoDBStorage

# Create storage instance
storage = TelegramDynamoDBStorage()

# Load all active chats
active_chats = storage.load_active_chats()
print(f"Active chats: {active_chats}")

# Get statistics
stats = storage.get_statistics()
print(f"Total chats: {stats['total_chats']}")
print(f"Active chats: {stats['active_chats']}")

# Manually add a chat
storage.save_chat(
    chat_id=123456789,
    user_info={
        'username': 'testuser',
        'first_name': 'Test'
    }
)

# Deactivate a chat
storage.deactivate_chat(123456789)

# Reactivate a chat
storage.reactivate_chat(123456789)

# Cleanup inactive chats (older than 30 days)
cleaned = storage.cleanup_inactive_chats(days_threshold=30)
print(f"Cleaned up {cleaned} inactive chats")
```

## Live Strategy Integration

The live trading scheduler automatically uses DynamoDB persistence:

```python
# In live_strategy_scheduler.py
self.telegram_bot = create_telegram_bot_from_env(use_dynamodb=True)
```

When the scheduler starts:
1. Loads all registered chats from DynamoDB
2. Sends trading signals to all active chats
3. Automatically persists new registrations

## AWS Permissions

The IAM user or role needs the following DynamoDB permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/telegram-chats"
      ]
    }
  ]
}
```

## Cost Considerations

- **DynamoDB On-Demand**: Pay only for what you use
- **Free Tier**: 25 GB storage, 2.5M read requests/month
- **Typical Usage**: A bot with 1000 active users generating 100 signals/day would cost < $1/month

## Monitoring

View DynamoDB metrics in AWS Console:
- Table overview: Item count, size
- CloudWatch metrics: Read/write capacity, throttles
- Item explorer: View individual chat records

## Troubleshooting

### Bot falls back to in-memory storage

Check:
1. AWS credentials are configured
2. IAM permissions include DynamoDB access
3. Table name and region are correct
4. Network connectivity to AWS

### Chats not persisting

Verify:
1. `use_dynamodb=True` is set
2. DynamoDB table exists
3. No errors in logs during `save_chat()` calls

### High DynamoDB costs

Consider:
1. Implementing cleanup for inactive chats
2. Reducing message count updates
3. Using batch operations for bulk updates

## Benefits

1. **Reliability**: Users stay subscribed across bot restarts
2. **Scalability**: DynamoDB handles millions of chats
3. **Analytics**: Track user engagement and activity
4. **Compliance**: Soft delete preserves audit trail
5. **Cost-Effective**: Pay-per-request pricing