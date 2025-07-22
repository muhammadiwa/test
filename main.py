import asyncio
import signal
import sys
from loguru import logger
from utils.config import Config
from api.mexc_api import MexcAPI
from core.sniper_engine import SniperEngine
from core.order_executor import OrderExecutor
from core.sell_strategy_manager import SellStrategyManager
from telegram_module.telegram_bot import TelegramBot
from dashboard.dashboard_manager import DashboardManager

# Global variables to track components
mexc_api = None
sniper_engine = None
order_executor = None
sell_strategy_manager = None
telegram_bot = None
dashboard_manager = None

async def setup():
    """Set up and initialize all components."""
    global mexc_api, sniper_engine, order_executor, sell_strategy_manager, telegram_bot, dashboard_manager
    
    # Validate configuration
    if not Config.validate():
        logger.error("Invalid configuration. Please check your .env file.")
        return False
    
    # Initialize API
    logger.info("Initializing MEXC API...")
    mexc_api = MexcAPI()
    
    # Test API connection
    try:
        exchange_info = await mexc_api.get_exchange_info()
        if not exchange_info:
            logger.error("Could not connect to MEXC API. Please check your credentials.")
            return False
        logger.success("Successfully connected to MEXC API")
    except Exception as e:
        logger.error(f"Error connecting to MEXC API: {e}")
        return False
    
    # Initialize components
    logger.info("Initializing bot components...")
    order_executor = OrderExecutor(mexc_api)
    sniper_engine = SniperEngine(mexc_api)
    sell_strategy_manager = SellStrategyManager(mexc_api, order_executor)
    
    # Initialize Dashboard
    dashboard_manager = DashboardManager(
        mexc_api, sniper_engine, order_executor, sell_strategy_manager
    )
    logger.info("Dashboard initialized")
    
    # Initialize Telegram bot
    if Config.TELEGRAM_BOT_TOKEN and Config.TELEGRAM_CHAT_ID:
        logger.info("Setting up Telegram bot...")
        telegram_bot = TelegramBot(mexc_api, sniper_engine, order_executor, sell_strategy_manager)
        
        if not await telegram_bot.setup():
            logger.warning("Could not set up Telegram bot. Continuing without notifications.")
    else:
        logger.warning("Telegram notifications are disabled. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file to enable.")
    
    return True

async def start():
    """Start all components."""
    logger.info("Starting Sniper Bot...")
    
    # Start Telegram bot if available
    if telegram_bot:
        await telegram_bot.start()
    
    # Start Sniper Engine if available
    if sniper_engine:
        await sniper_engine.start()
    
    logger.success("Sniper Bot is running")
    
    # Display dashboard status
    if dashboard_manager:
        dashboard_manager.display_status()
    
    # Keep running until signal
    await wait_for_signal()

async def stop():
    """Stop all components."""
    logger.info("Stopping Sniper Bot...")
    
    # Stop Sniper Engine
    if sniper_engine:
        await sniper_engine.stop()
    
    # Stop Telegram bot
    if telegram_bot:
        await telegram_bot.stop()
    
    # Close WebSocket connection
    if mexc_api:
        await mexc_api.close_websocket()
    
    logger.success("Sniper Bot has been stopped")

async def wait_for_signal():
    """Wait for termination signal."""
    loop = asyncio.get_running_loop()
    stop_future = loop.create_future()
    
    def signal_handler():
        if not stop_future.done():
            stop_future.set_result(None)
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    await stop_future

async def main():
    """Main function to run the bot."""
    try:
        # Set up components
        if not await setup():
            logger.error("Setup failed. Exiting...")
            return 1
        
        # Start bot
        await start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        # Stop bot
        await stop()
    
    return 0

if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
