# Telegram Bot Integration

This documentation covers the Telegram bot integration for the Mean Reversion Trading Strategy. The bot sends real-time trading signals to subscribed users.

## Related Documentation

- **[Bot Docker Instructions](BOT_DOCKER_INSTRUCTIONS.md)** - Container setup and deployment for the bot
- **[Signal Cache Persistence](signal_cache_persistence.md)** - Persistent storage for duplicate signal prevention
- **[Telegram DynamoDB Persistence](telegram_dynamodb_persistence.md)** - DynamoDB storage for chat management
- **[Strategy Documentation](STRATEGY_DOCUMENTATION.md)** - Core strategy implementation
- **[Container Documentation](CONTAINER.md)** - General container usage and deployment

## Features

- 📱 **Real-time Notifications**: Receive trading signals instantly via Telegram
- 🔔 **Signal Formatting**: Beautiful, formatted messages with all trade details
- 👥 **Multi-user Support**: Manage multiple subscribers with in-memory chat storage
- 🛡️ **Error Handling**: Robust error handling and automatic chat cleanup
- ⚙️ **Easy Setup**: Simple configuration via environment variables

## Quick Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for `@BotFather`
2. Send `/start` to @BotFather
3. Send `/newbot` and follow the instructions
4. Choose a name and username for your bot
5. Copy the bot token provided

### 2. Configure Environment

Add your bot token to the `.env` file:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 3. Install Dependencies

```bash
pip install python-telegram-bot>=21.0
```

### 4. Test the Bot

Run the test script to verify everything works:

```bash
python tests/test_telegram_bot.py
```

## File Structure

```
src/bot/
├── __init__.py                     # Package initialization
├── telegram_bot.py                 # Main bot class and integration
├── telegram_chat_manager.py        # Chat subscription management (in-memory)
├── telegram_message_templates.py   # Message formatting and templates
├── telegram_signal_notifier.py     # Signal notification handling
└── live_signal_detector.py        # Signal detection for live trading

live_strategy_scheduler.py         # Main scheduler (project root)

tests/
└── test_telegram_bot.py           # Bot testing script

docs/
├── TELEGRAM_BOT_INTEGRATION.md    # This documentation
└── BOT_DOCKER_INSTRUCTIONS.md     # Container deployment guide
```

## Components

### TelegramMessageTemplates

Manages message templates and formatting for different types of notifications:

- **Welcome messages** for new users
- **Trading signals** with formatted trade details
- **Help and status** messages
- **Error notifications**

### TelegramChatManager

Handles chat subscriptions and user management:

- **In-memory storage** of active chats
- **User metadata** tracking (join date, activity, etc.)
- **Cleanup tools** for inactive chats

### TelegramSignalNotifier

Sends notifications to subscribed users:

- **Signal notifications** with trade details
- **Error handling** for blocked/invalid chats
- **Rate limiting** to avoid Telegram API limits

### MeanReversionTelegramBot

Main bot class that ties everything together:

- **Command handlers** (/start, /stop, /help, /status)
- **Async integration** with the trading strategy
- **Context management** for proper startup/shutdown
- **Statistics tracking** and reporting

## Bot Commands

Users can interact with your bot using these commands:

- `/start` - Start receiving trading signals
- `/stop` - Stop receiving notifications
- `/help` - Show available commands
- `/status` - Display bot status and statistics

## Integration with Live Strategy

The bot is automatically integrated with the live strategy scheduler. When enabled:

1. **Signal Detection**: When the strategy detects a trading signal, it automatically sends a formatted notification to all active chats
2. **Error Notifications**: Critical errors are reported to subscribers
3. **Graceful Shutdown**: Bot stops cleanly when the strategy scheduler stops

## Message Examples

### Trading Signal

```
📈 LONG SIGNAL

🎯 Symbol: EURUSD
💰 Entry Price: 1.1234
🛑 Stop Loss: 1.1200
🎯 Take Profit: 1.1300
📊 Position Size: 1.5
💸 Risk Amount: $50.00
⚖️ Risk/Reward: 1:2.0

📋 Strategy Details:
• BB Period: 20 | Std: 2.0
• VWAP Period: 50 | Std: 1.5
• ATR Period: 14

⏰ Time: 2025-01-15 14:30:00 UTC
```

## Testing

### Automatic Test

Run the test script and follow the prompts:

```bash
python tests/test_telegram_bot.py
```

Choose option 1 for automatic testing, which will:
1. Verify bot token
2. Initialize the bot
3. Send test signals
4. Display statistics

### Interactive Test

Choose option 2 for interactive testing:
1. Send test signals manually
2. Send custom messages
3. View bot statistics

## Configuration Options

### Environment Variables

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional - for data persistence
TELEGRAM_CHAT_PERSISTENCE_FILE=/path/to/chat_data.json
```

### Live Strategy Integration

In your live strategy scheduler:

```python
# Enable/disable Telegram notifications
scheduler = LiveStrategyScheduler(enable_telegram=True)

# Or disable Telegram
scheduler = LiveStrategyScheduler(enable_telegram=False)
```

## Error Handling

The bot includes comprehensive error handling:

- **Blocked Users**: Automatically removes users who block the bot
- **Invalid Chats**: Handles deleted or inaccessible chats
- **Network Issues**: Retries failed sends with exponential backoff
- **Rate Limits**: Respects Telegram API rate limits
- **Graceful Degradation**: Continues trading even if notifications fail

## Signal Cache Persistence

The bot includes an intelligent signal cache system to prevent duplicate notifications:

- **Duplicate Detection**: Prevents sending the same signal multiple times within 24 hours
- **Price Tolerance**: Accounts for small price fluctuations (configurable threshold)
- **Persistent Storage**: Uses DynamoDB to maintain cache across restarts and multiple instances
- **Automatic Cleanup**: Old signals are automatically removed after expiration

For detailed configuration and troubleshooting, see **[Signal Cache Persistence](signal_cache_persistence.md)**.

## Security Considerations

- **Token Security**: Keep your bot token secure and never commit it to version control
- **User Privacy**: Chat data is stored locally and not transmitted elsewhere
- **Access Control**: Only users who send `/start` receive notifications
- **Data Cleanup**: Inactive chats are automatically cleaned up

## Troubleshooting

### Bot Not Starting

1. Check that `TELEGRAM_BOT_TOKEN` is set correctly
2. Verify the token with @BotFather
3. Check network connectivity
4. Review logs for specific error messages

### No Notifications Received

1. Send `/start` to your bot first
2. Check that the bot is running and connected
3. Verify trading hours (6:00-17:00 UTC)
4. Check logs for delivery errors

### Messages Not Formatted

1. Ensure `parse_mode='Markdown'` is working
2. Check for special characters in messages
3. Review template formatting

## Advanced Usage

### Custom Message Templates

```python
from bot.telegram_message_templates import TelegramMessageTemplates

templates = TelegramMessageTemplates()
templates.add_custom_template(
    'my_template',
    '*Custom Alert*\n\nMessage: {message}',
    'Markdown'
)
```

### Manual Notifications

```python
from bot.telegram_bot import create_telegram_bot_from_env

bot = create_telegram_bot_from_env()
await bot.send_custom_message("Manual alert message")
```

### Chat Statistics

```python
stats = bot.get_bot_statistics()
print(f"Active chats: {stats['active_chats']}")
print(f"Total commands: {stats['total_commands']}")
```

## Contributing

When adding new features:

1. Update message templates in `telegram_message_templates.py`
2. Add new notification types in `telegram_signal_notifier.py`
3. Update command handlers in `telegram_bot.py`
4. Add tests to `test_telegram_bot.py`
5. Update this README

## Support

For issues or questions:

1. Check the logs in `live_logs/scheduler.log`
2. Run the test script to diagnose problems
3. Review Telegram Bot API documentation
4. Check the error handling in the code
