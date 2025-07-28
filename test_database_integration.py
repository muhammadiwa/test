#!/usr/bin/env python3
"""
Test script untuk menguji integrasi database SQLite
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager
from loguru import logger

async def test_database_integration():
    """Test database integration with all components."""
    
    # Initialize database
    logger.info("Initializing database manager...")
    db_manager = DatabaseManager("data/test_tradebot.db")
    await db_manager.initialize()
    
    # Test saving strategy
    logger.info("Testing strategy saving...")
    strategy_data = {
        'symbol': 'BTCUSDT',
        'buy_price': 50000.0,
        'quantity': 0.001,
        'original_quantity': 0.001,
        'take_profit_price': 55000.0,
        'tp_sell_percentage': 100.0,
        'tp_executed': False,
        'stop_loss_price': 45000.0,
        'trailing_stop_percentage': 5.0,
        'trailing_stop_price': None,
        'tsl_activation_price': 52000.0,
        'tsl_activated': False,
        'highest_price': 50000.0,
        'time_based_minutes': 30,
        'start_time': datetime.now(),
        'status': 'ACTIVE',
        'executed': False
    }
    
    strategy_id = "BTCUSDT_1641234567"
    success = await db_manager.save_strategy(strategy_id, strategy_data)
    logger.info(f"Strategy save result: {success}")
    
    # Test loading strategy
    logger.info("Testing strategy loading...")
    loaded_strategy = await db_manager.load_strategy(strategy_id)
    logger.info(f"Loaded strategy: {loaded_strategy}")
    
    # Test saving order
    logger.info("Testing order saving...")
    order_data = {
        'id': 'buy_12345_1641234567',
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'type': 'MARKET',
        'quantity': 0.001,
        'usdt_amount': 50.0,
        'status': 'FILLED',
        'order_id': '12345',
        'strategy_id': strategy_id
    }
    
    success = await db_manager.save_order(order_data)
    logger.info(f"Order save result: {success}")
    
    # Test saving trade
    logger.info("Testing trade saving...")
    trade_data = {
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'quantity': 0.001,
        'price': 50000.0,
        'value': 50.0,
        'order_id': '12345',
        'strategy_id': strategy_id,
        'timestamp': datetime.now().isoformat()
    }
    
    success = await db_manager.save_trade(trade_data)
    logger.info(f"Trade save result: {success}")
    
    # Test saving configuration
    logger.info("Testing configuration saving...")
    success = await db_manager.save_config('test_param', 100.0, 'Test parameter')
    logger.info(f"Config save result: {success}")
    
    loaded_config = await db_manager.load_config('test_param')
    logger.info(f"Loaded config: {loaded_config}")
    
    # Test loading active strategies
    logger.info("Testing active strategies loading...")
    active_strategies = await db_manager.load_active_strategies()
    logger.info(f"Active strategies: {len(active_strategies)} found")
    
    # Test trading statistics
    logger.info("Testing trading statistics...")
    stats = await db_manager.get_trading_stats(7)
    logger.info(f"Trading stats: {stats}")
    
    # Close database
    await db_manager.close()
    
    logger.success("Database integration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_database_integration())
