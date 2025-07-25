#!/usr/bin/env python3
"""
Test script untuk menguji MBGUSDT secara spesifik
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_module.telegram_bot import TelegramBot
from api.mexc_api import MexcAPI

async def test_mbg_display():
    """Test the MBGUSDT display."""
    print("🧪 Testing MBGUSDT display...")
    
    # Initialize components
    mexc_api = MexcAPI()
    telegram_bot = TelegramBot(mexc_api, None, None, None)
    
    # Test with MBGUSDT
    pair = "MBGUSDT"
    
    print(f"\n📊 Testing 24hr ticker for {pair}:")
    
    try:
        # Test 24hr ticker first
        ticker_24hr = await mexc_api.get_24hr_ticker(pair)
        if ticker_24hr:
            print(f"24hr ticker data: {ticker_24hr}")
            if isinstance(ticker_24hr, dict):
                print(f"  Symbol: {ticker_24hr.get('symbol')}")
                print(f"  Last Price: {ticker_24hr.get('lastPrice')}")
                print(f"  Price Change %: {ticker_24hr.get('priceChangePercent')}")
        
        print(f"\n📊 Testing formatted price for {pair}:")
        result, error = await telegram_bot._get_formatted_price_for_pair(pair)
        if result:
            print(f"Formatted price: {result}")
        if error:
            print(f"Error: {error}")
        
        print(f"\n📊 Testing orderbook display for {pair}:")
        result, error = await telegram_bot._get_orderbook_display(pair)
        if result:
            print("Orderbook result:")
            print(result)
        if error:
            print(f"Error: {error}")
            
    except Exception as e:
        print(f"Exception: {str(e)}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_mbg_display())
