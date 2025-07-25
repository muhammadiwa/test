#!/usr/bin/env python3
"""
Test script untuk menguji format persentase perubahan harga yang sudah diperbaiki
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_module.telegram_bot import TelegramBot
from api.mexc_api import MexcAPI

async def test_formatted_price():
    """Test the formatted price display with percentage change."""
    print("🧪 Testing formatted price display...")
    
    # Initialize components
    mexc_api = MexcAPI()
    telegram_bot = TelegramBot(mexc_api, None, None, None)
    
    # Test pairs
    test_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for pair in test_pairs:
        print(f"\n📊 Testing formatted display for {pair}:")
        
        try:
            result, error = await telegram_bot._get_formatted_price_for_pair(pair)
            if result:
                print(f"  ✅ Result: {result}")
            if error:
                print(f"  ❌ Error: {error}")
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_formatted_price())
