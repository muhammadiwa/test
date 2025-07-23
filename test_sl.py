from core.sell_strategy_manager import SellStrategyManager
from api.mexc_api import MexcAPI
from core.order_executor import OrderExecutor
import asyncio
from loguru import logger

# A simple function to log the sell callbacks
async def log_sell_callback(symbol, buy_price, sell_price, quantity, reason):
    """A test callback that just logs the sell details"""
    await asyncio.sleep(0.1)  # To make this a proper async function
    logger.info(f"CALLBACK: Sold {quantity} {symbol} at {sell_price:.8f}")
    logger.info(f"CALLBACK: Buy price: {buy_price:.8f}, Reason: {reason}")
    logger.info(f"CALLBACK: Profit/Loss: {((sell_price - buy_price) / buy_price * 100):.2f}%")

async def test_stop_loss():
    """Test the stop loss functionality"""
    # Initialize components
    api = MexcAPI()
    order_exec = OrderExecutor(api)
    manager = SellStrategyManager(api, order_exec)
    
    # Register our callback
    manager.register_sell_callback(log_sell_callback)
    
    print('\nSTOP LOSS TEST')
    strategy_config = {
        'take_profit_percentage': 10,
        'stop_loss_percentage': 5,
        'tp_sell_percentage': 100,
        'trailing_stop_percentage': 0,
        'tsl_min_activation_percentage': 0,
        'time_based_minutes': 0
    }
    
    strategy_id = manager.add_strategy('BTCUSDT', 100.0, 0.01, strategy_config)
    print('Strategy ID:', strategy_id)
    
    strat = manager.active_strategies[strategy_id]
    print('Buy Price:', strat['buy_price'])
    print('Stop Loss Price:', strat['stop_loss_price'])
    print('Take Profit Price:', strat['take_profit_price'])
    
    # Test the sell logic
    test_price = 94.0  # Below stop loss
    should_sell = manager._should_sell(strategy_id, test_price)
    reason = manager._get_sell_reason(strategy_id, test_price)
    print(f'Would sell at price {test_price}?', should_sell)
    print('Sell reason:', reason)
    
    # Test direct execution of a stop loss
    print("\n--- TESTING STOP LOSS EXECUTION ---")
    print("Executing sell with STOP_LOSS reason:")
    # We directly execute the sell with the STOP_LOSS reason
    await manager._execute_sell(strategy_id, "STOP_LOSS")
    
    # If we reach here, the test is complete
    print("\nTest completed")

if __name__ == "__main__":
    asyncio.run(test_stop_loss())
