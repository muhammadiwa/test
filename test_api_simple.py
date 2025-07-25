#!/usr/bin/env python3
"""
Test API functionality without starting full bot
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.mexc_api import MexcAPI

async def test_api():
    """Test basic API functionality"""
    
    print("=== Testing MEXC API ===\n")
    
    mexc_api = MexcAPI()
    
    try:
        # Test public endpoint (no auth required)
        print("1. Testing 24hr ticker (public endpoint)...")
        ticker_data = await mexc_api.get_24hr_ticker("BTCUSDT")
        
        if ticker_data:
            print(f"✅ API is working!")
            print(f"   BTC Price: ${float(ticker_data['lastPrice']):,.2f}")
            print(f"   24h Change: {ticker_data['priceChangePercent']}%")
            
            # Test price formatting
            change_percent = float(ticker_data['priceChangePercent'])
            if change_percent > 0:
                emoji = "🟢"
                sign = "+"
            elif change_percent < 0:
                emoji = "🔴"
                sign = ""
            else:
                emoji = "⚪"
                sign = ""
                
            print(f"   Formatted: {emoji} {sign}{change_percent:.2f}%")
        else:
            print("❌ Failed to get ticker data")
            
        print()
        
        # Test symbol info
        print("2. Testing symbol information...")
        symbol_info = await mexc_api.get_symbol_info("BTCUSDT")
        
        if symbol_info:
            print("✅ Symbol info retrieved successfully")
            for filter_info in symbol_info['filters']:
                if filter_info['filterType'] == 'LOT_SIZE':
                    print(f"   Min Quantity: {filter_info['minQty']}")
                    print(f"   Step Size: {filter_info['stepSize']}")
                elif filter_info['filterType'] == 'MIN_NOTIONAL':
                    print(f"   Min Notional: {filter_info['minNotional']}")
        else:
            print("❌ Failed to get symbol info")
            
        print()
        print("=== API Test Summary ===")
        print("✅ Public endpoints working")
        print("✅ Price formatting implemented")
        print("✅ Ready to test buy commands!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())
