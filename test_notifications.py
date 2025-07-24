from telegram_module.telegram_bot import TelegramBot
from api.mexc_api import MexcAPI
from core.order_executor import OrderExecutor
from core.sell_strategy_manager import SellStrategyManager
import asyncio
import time

async def test_telegram_notifications():
    # Initialize components
    api = MexcAPI()
    order_exec = OrderExecutor(api)
    sell_manager = SellStrategyManager(api, order_exec)
    telegram_bot = TelegramBot(api, None, order_exec, sell_manager)
    
    # Set up the bot
    await telegram_bot.setup()
    
    # Test profit notification
    print("\nTesting TAKE_PROFIT notification:")
    await telegram_bot.send_profit_notification("BTCUSDT", 65000.0, 70000.0, 0.1, "TAKE_PROFIT")
    await asyncio.sleep(2)
    
    # Test stop loss notification
    print("\nTesting STOP_LOSS notification:")
    await telegram_bot.send_profit_notification("ETHUSDT", 3000.0, 2850.0, 1.0, "STOP_LOSS")
    await asyncio.sleep(2)
    
    # Test failed stop loss notification with our new format
    print("\nTesting STOP_LOSS_FAILED notification:")
    await telegram_bot.send_profit_notification("DOGEUSDT", 0.12, 0.12, 1000.0, "STOP_LOSS_FAILED")
    await asyncio.sleep(2)
    
    print("\nAll notifications have been sent!")

if __name__ == "__main__":
    asyncio.run(test_telegram_notifications())
