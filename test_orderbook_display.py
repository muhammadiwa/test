#!/usr/bin/env python3
"""
Test script untuk menguji orderbook display dengan persentase perubahan harga
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_module.telegram_bot import TelegramBot
from api.mexc_api import MexcAPI

async def test_orderbook_display():
    """Test the orderbook display with percentage change."""
    print("🧪 Testing orderbook display...")
    
    # Initialize components
    mexc_api = MexcAPI()
    telegram_bot = TelegramBot(mexc_api, None, None, None)
    
    # Test with one pair
    pair = "BTCUSDT"
    
    print(f"\n📊 Testing orderbook display for {pair}:")
    
    try:
        result, error = await telegram_bot._get_orderbook_display(pair)
        if result:
            print("✅ Orderbook result:")
            print(result)
        if error:
            print(f"❌ Error: {error}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_orderbook_display())
