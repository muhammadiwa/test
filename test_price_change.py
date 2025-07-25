#!/usr/bin/env python3
"""
Test script untuk menguji fungsi 24hr ticker dan persentase perubahan harga
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.mexc_api import MexcAPI

async def test_24hr_ticker():
    """Test the new 24hr ticker functionality."""
    print("🧪 Testing 24hr ticker functionality...")
    
    # Initialize MEXC API
    mexc_api = MexcAPI()
    
    # Test pairs
    test_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for pair in test_pairs:
        print(f"\n📊 Testing {pair}:")
        
        try:
            # Test regular ticker price
            print("  Regular price:")
            ticker_price = await mexc_api.get_ticker_price(pair)
            if ticker_price:
                if isinstance(ticker_price, dict):
                    print(f"    Price: {ticker_price.get('price', 'N/A')}")
                else:
                    print(f"    Response: {type(ticker_price)} with {len(ticker_price) if isinstance(ticker_price, list) else 'unknown'} items")
            else:
                print("    ❌ No data received")
            
            # Test 24hr ticker
            print("  24hr ticker:")
            ticker_24hr = await mexc_api.get_24hr_ticker(pair)
            if ticker_24hr:
                if isinstance(ticker_24hr, dict):
                    print(f"    Symbol: {ticker_24hr.get('symbol', 'N/A')}")
                    print(f"    Last Price: {ticker_24hr.get('lastPrice', 'N/A')}")
                    print(f"    Price Change: {ticker_24hr.get('priceChange', 'N/A')}")
                    print(f"    Price Change %: {ticker_24hr.get('priceChangePercent', 'N/A')}%")
                    print(f"    High 24h: {ticker_24hr.get('highPrice', 'N/A')}")
                    print(f"    Low 24h: {ticker_24hr.get('lowPrice', 'N/A')}")
                    print(f"    Volume: {ticker_24hr.get('volume', 'N/A')}")
                elif isinstance(ticker_24hr, list) and ticker_24hr:
                    item = ticker_24hr[0]  # Take first item
                    print(f"    Symbol: {item.get('symbol', 'N/A')}")
                    print(f"    Last Price: {item.get('lastPrice', 'N/A')}")
                    print(f"    Price Change: {item.get('priceChange', 'N/A')}")
                    print(f"    Price Change %: {item.get('priceChangePercent', 'N/A')}%")
                    print(f"    High 24h: {item.get('highPrice', 'N/A')}")
                    print(f"    Low 24h: {item.get('lowPrice', 'N/A')}")
                    print(f"    Volume: {item.get('volume', 'N/A')}")
                else:
                    print(f"    Response: {type(ticker_24hr)} - {ticker_24hr}")
            else:
                print("    ❌ No 24hr data received")
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_24hr_ticker())
