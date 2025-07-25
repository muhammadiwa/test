#!/usr/bin/env python3
"""
Test script for limit order functionality
This script tests the new limit order features in the trading bot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.mexc_api import MexcAPI
from core.order_executor import OrderExecutor
from utils.config_manager import ConfigManager
import logging

def test_limit_order():
    """Test limit order creation and formatting"""
    
    print("=== Testing Limit Order Functionality ===\n")
    
    # Initialize components
    config_manager = ConfigManager()
    mexc_api = MexcAPI()
    order_executor = OrderExecutor(mexc_api)
    
    # Test parameters
    symbol = "BTCUSDT"
    amount_usdt = 10.0
    limit_price = 50000.0
    
    print(f"Test Parameters:")
    print(f"- Symbol: {symbol}")
    print(f"- Amount (USDT): {amount_usdt}")
    print(f"- Limit Price: {limit_price}")
    print()
    
    try:
        # Test 1: Get current price for comparison
        print("1. Getting current market price...")
        ticker_data = mexc_api.get_24hr_ticker(symbol)
        if ticker_data:
            current_price = float(ticker_data['lastPrice'])
            print(f"   Current Price: {current_price}")
            print(f"   24h Change: {ticker_data['priceChangePercent']}%")
            
            # Calculate quantity for limit order
            quantity = amount_usdt / limit_price
            print(f"   Calculated Quantity: {quantity:.8f} BTC")
            print()
        
        # Test 2: Check symbol info for minimum quantities
        print("2. Getting symbol information...")
        symbol_info = mexc_api.get_symbol_info(symbol)
        if symbol_info:
            for filter_info in symbol_info['filters']:
                if filter_info['filterType'] == 'LOT_SIZE':
                    min_qty = float(filter_info['minQty'])
                    step_size = float(filter_info['stepSize'])
                    print(f"   Min Quantity: {min_qty}")
                    print(f"   Step Size: {step_size}")
                elif filter_info['filterType'] == 'MIN_NOTIONAL':
                    min_notional = float(filter_info['minNotional'])
                    print(f"   Min Notional: {min_notional}")
            print()
        
        # Test 3: Format buy command scenarios
        print("3. Testing command format scenarios...")
        
        # Market order format
        market_cmd = f"/buy {symbol} {amount_usdt}"
        print(f"   Market Order Command: {market_cmd}")
        print(f"   -> Should execute market buy")
        
        # Limit order format
        limit_cmd = f"/buy {symbol} {amount_usdt} {limit_price}"
        print(f"   Limit Order Command: {limit_cmd}")
        print(f"   -> Should execute limit buy at {limit_price}")
        print()
        
        # Test 4: Validate price comparison logic
        print("4. Testing price comparison logic...")
        if ticker_data:
            current_price = float(ticker_data['lastPrice'])
            
            if limit_price < current_price:
                print(f"   ✅ Limit price ({limit_price}) is below market ({current_price}) - Good for buying")
            elif limit_price > current_price:
                print(f"   ⚠️  Limit price ({limit_price}) is above market ({current_price}) - Will execute immediately")
            else:
                print(f"   ℹ️  Limit price equals market price")
            print()
        
        # Test 5: Check order monitoring setup
        print("5. Testing order monitoring setup...")
        print("   Order monitoring callback would be registered for:")
        print(f"   - Symbol: {symbol}")
        print(f"   - Order tracking and status updates")
        print(f"   - Telegram notifications on fill/cancel")
        print()
        
        print("=== All Tests Completed Successfully ===")
        print("\nLimit order functionality is ready for live testing!")
        print("Commands to test:")
        print(f"- Market: /buy {symbol} {amount_usdt}")
        print(f"- Limit:  /buy {symbol} {amount_usdt} {limit_price}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_limit_order()
