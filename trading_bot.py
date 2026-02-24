#!/usr/bin/env python3
"""
Unified Trading Bot

Main entry point for the unified trading bot that runs multiple strategies
in parallel with shared infrastructure.

Features:
- Runs every 5 minutes (synchronized to :00, :05, :10, etc.)
- Parallel execution of multiple strategies
- Shared Telegram bot and signal cache
- Error isolation (one strategy failure doesn't stop others)
- Configurable enable/disable per strategy
- Trading hours validation (6:00-19:00 UTC by default)
- Real-time logging and monitoring
- Telegram notifications for trading signals
- Signal caching to prevent duplicate notifications
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.bot.scheduler import BotOrchestrator

# Configure logging
logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging for the bot"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Suppress verbose logs from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def check_environment():
    """Check required environment variables"""
    logger.info("🔍 Checking environment variables...")
    
    required_env_vars = [
        'CAPITAL_COM_API_KEY',
        'CAPITAL_COM_PASSWORD', 
        'CAPITAL_COM_IDENTIFIER'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these in your .env file or environment")
        return False
    
    logger.info("✅ Environment variables verified")
    return True


async def main():
    """Main entry point"""
    setup_logging()
    
    logger.info("="*80)
    logger.info("🤖 Unified Trading Bot - Multiple Strategies in Parallel")
    logger.info("="*80)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create orchestrator
    try:
        config_path = os.getenv('BOT_CONFIG_PATH')  # Optional: override config path
        orchestrator = BotOrchestrator(config_path)
        
        # Initialize
        if not await orchestrator.initialize():
            logger.error("❌ Failed to initialize bot")
            sys.exit(1)
        
        # Start bot
        await orchestrator.start()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Program interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
