#!/usr/bin/env python3
"""
Test script untuk menguji multiple pairs dengan 24hr high/low data
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_module.telegram_bot import TelegramBot
from api.mexc_api import MexcAPI

async def test_multiple_pairs():
    """Test multiple pairs with 24hr high/low display."""
    print("🧪 Testing multiple pairs with 24hr high/low...")
    
    # Initialize components
    mexc_api = MexcAPI()
    telegram_bot = TelegramBot(mexc_api, None, None, None)
    
    # Test pairs
    test_pairs = ["BTCUSDT", "ETHUSDT", "MBGUSDT"]
    
    print("\n📊 Testing formatted prices:")
    for pair in test_pairs:
        try:
            result, error = await telegram_bot._get_formatted_price_for_pair(pair)
            if result:
                print(f"{result}")
            if error:
                print(f"Error {pair}: {error}")
        except Exception as e:
            print(f"Exception {pair}: {str(e)}")
    
    print("\n📊 Testing orderbook display for BTCUSDT:")
    try:
        result, error = await telegram_bot._get_orderbook_display("BTCUSDT")
        if result:
            print(result)
        if error:
            print(f"Error: {error}")
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_multiple_pairs())
