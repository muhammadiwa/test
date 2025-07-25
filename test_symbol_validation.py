#!/usr/bin/env python3
"""
Test symbol validation for MEXC
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.mexc_api import MexcAPI

async def test_symbol_validation():
    """Test if symbols are valid on MEXC"""
    
    print("=== Testing Symbol Validation ===\n")
    
    mexc_api = MexcAPI()
    
    test_symbols = ["PULSEUSDT", "BTCUSDT", "ETHUSDT", "ADAUSDT"]
    
    for symbol in test_symbols:
        print(f"Testing symbol: {symbol}")
        try:
            ticker_data = await mexc_api.get_24hr_ticker(symbol)
            if ticker_data:
                price = float(ticker_data['lastPrice'])
                change = ticker_data['priceChangePercent']
                print(f"  ✅ Valid symbol - Price: {price}, Change: {change}%")
            else:
                print(f"  ❌ Invalid symbol or no data")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()
    
    print("=== Command Parsing Test ===")
    cmd = "/buy pulseusdt 2 0.09"
    parts = cmd.split()
    pair = parts[1].upper()
    amount = float(parts[2])
    price = float(parts[3])
    
    print(f"Original command: {cmd}")
    print(f"Parsed pair: {pair}")
    print(f"Parsed amount: {amount}")
    print(f"Parsed price: {price}")
    print(f"Estimated quantity: {amount/price:.8f}")

if __name__ == "__main__":
    asyncio.run(test_symbol_validation())
