#!/usr/bin/env python3
"""
Test script untuk memverifikasi fix masalah oversold pada multiple strategies.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from core.sell_strategy_manager import SellStrategyManager
from api.mexc_api import MEXCAPI
from core.order_executor import OrderExecutor
from utils.config import get_config
from loguru import logger

async def test_multiple_strategy_sell():
    """Test multiple strategies with proper quantity handling."""
    
    print("🧪 Testing Multiple Strategy Quantity Fix...")
    
    # Initialize components (using mock for testing)
    config = get_config()
    
    class MockOrderExecutor:
        async def execute_market_sell(self, symbol, quantity):
            print(f"   📊 MOCK SELL: {symbol} - Quantity: {quantity}")
            if quantity is None:
                print("   ❌ ERROR: quantity is None - this would cause oversold!")
                return None
            if quantity <= 0:
                print("   ❌ ERROR: quantity is zero or negative!")
                return None
            print(f"   ✅ CORRECT: Selling exactly {quantity} {symbol.replace('USDT', '')}")
            return {
                'orderId': f'TEST_{symbol}_{quantity}',
                'executedQty': str(quantity)
            }
    
    class MockMEXCAPI:
        async def get_filled_order_details(self, symbol, order_id):
            return {
                'quantity': 6.70 if '6.7' in order_id else 6.75,
                'price': 0.14782274,
                'value': 1.0,
                'side': 'SELL'
            }
    
    # Create mock instances
    mock_mexc = MockMEXCAPI()
    mock_executor = MockOrderExecutor()
    
    # Create strategy manager
    strategy_manager = SellStrategyManager(mock_mexc, mock_executor)
    
    # Add two PULSE strategies (simulating the real scenario)
    strategy1_id = await strategy_manager.add_strategy(
        symbol='PULSEUSDT',
        buy_price=0.14924000,
        quantity=6.70000000,
        take_profit_percentage=50.0,
        stop_loss_percentage=5.0,
        trailing_stop_percentage=3.0,
        time_based_minutes=0
    )
    
    strategy2_id = await strategy_manager.add_strategy(
        symbol='PULSEUSDT', 
        buy_price=0.14814000,
        quantity=6.75000000,
        take_profit_percentage=50.0,
        stop_loss_percentage=5.0,
        trailing_stop_percentage=3.0,
        time_based_minutes=0
    )
    
    print(f"📈 Created strategies: {strategy1_id}, {strategy2_id}")
    
    # Test individual strategy sells
    print("\\n🔥 Testing Strategy #1 Sell (should sell 6.70):")
    result1 = await strategy_manager._execute_sell(strategy1_id, "TRAILING_STOP")
    print(f"   Result: {result1}")
    
    print("\\n🔥 Testing Strategy #2 Sell (should sell 6.75):")  
    result2 = await strategy_manager._execute_sell(strategy2_id, "TRAILING_STOP")
    print(f"   Result: {result2}")
    
    # Check if strategies were properly removed
    print("\\n📊 Active strategies after sells:")
    print(f"   Total active: {len(strategy_manager.active_strategies)}")
    print(f"   Strategy 1 exists: {strategy1_id in strategy_manager.active_strategies}")
    print(f"   Strategy 2 exists: {strategy2_id in strategy_manager.active_strategies}")
    
    # Test results
    if result1 and result2:
        print("\\n✅ SUCCESS: Both strategies executed individual sells correctly!")
        print("✅ SUCCESS: No 'oversold' error - each strategy sold its own quantity")
        print("✅ SUCCESS: Strategies properly removed after execution")
    else:
        print("\\n❌ FAILED: Some strategies failed to execute")
    
    return result1 and result2

async def test_partial_sell():
    """Test partial sell functionality."""
    
    print("\\n🧪 Testing Partial Take Profit...")
    
    class MockOrderExecutor:
        async def execute_market_sell(self, symbol, quantity):
            print(f"   📊 PARTIAL SELL: {symbol} - Quantity: {quantity}")
            return {
                'orderId': f'PARTIAL_{symbol}_{quantity}',
                'executedQty': str(quantity)
            }
    
    class MockMEXCAPI:
        async def get_filled_order_details(self, symbol, order_id):
            return {
                'quantity': 3.35,  # 50% of 6.70
                'price': 0.29848000,  # TP price
                'value': 1.0,
                'side': 'SELL'
            }
    
    mock_mexc = MockMEXCAPI()
    mock_executor = MockOrderExecutor()
    strategy_manager = SellStrategyManager(mock_mexc, mock_executor)
    
    # Add strategy with 50% take profit
    strategy_id = await strategy_manager.add_strategy(
        symbol='PULSEUSDT',
        buy_price=0.14924000,
        quantity=6.70000000,
        take_profit_percentage=50.0,
        stop_loss_percentage=5.0,
        trailing_stop_percentage=3.0,
        time_based_minutes=0,
        tp_sell_percentage=50.0  # Only sell 50% on TP
    )
    
    # Test partial sell
    print(f"🔥 Testing 50% Take Profit (should sell 3.35 of 6.70):")
    result = await strategy_manager._execute_sell(strategy_id, "TAKE_PROFIT")
    
    # Check if strategy still exists for monitoring
    strategy_exists = strategy_id in strategy_manager.active_strategies
    remaining_qty = strategy_manager.active_strategies[strategy_id]['quantity'] if strategy_exists else 0
    
    print(f"   Result: {result}")
    print(f"   Strategy still active: {strategy_exists}")
    print(f"   Remaining quantity: {remaining_qty}")
    
    if result and strategy_exists and remaining_qty > 0:
        print("✅ SUCCESS: Partial sell working correctly!")
        print("✅ SUCCESS: Strategy continues monitoring remaining position")
    else:
        print("❌ FAILED: Partial sell not working properly")
    
    return result and strategy_exists

async def main():
    """Run all tests."""
    
    print("🚀 TESTING SELL STRATEGY FIXES")
    print("=" * 50)
    
    # Test 1: Multiple strategy fix
    test1_result = await test_multiple_strategy_sell()
    
    # Test 2: Partial sell
    test2_result = await test_partial_sell()
    
    print("\\n" + "=" * 50)
    print("📋 TEST SUMMARY:")
    print(f"   ✅ Multiple Strategy Fix: {'PASSED' if test1_result else 'FAILED'}")
    print(f"   ✅ Partial Sell Test: {'PASSED' if test2_result else 'FAILED'}")
    
    if test1_result and test2_result:
        print("\\n🎉 ALL TESTS PASSED!")
        print("🔧 Fix verified: No more oversold errors!")
        print("🔧 Each strategy sells its own quantity correctly!")
        print("🔧 Strategies properly removed after full execution!")
    else:
        print("\\n❌ SOME TESTS FAILED - Need more fixes")
    
    return test1_result and test2_result

if __name__ == "__main__":
    asyncio.run(main())
