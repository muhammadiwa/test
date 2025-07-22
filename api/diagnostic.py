import asyncio
from loguru import logger
from api.mexc_api import MexcAPI
from utils.config import Config

async def diagnose_api_connection():
    """Test the connection to MEXC API and diagnose any issues."""
    logger.info("Starting MEXC API diagnosis...")
    
    # Initialize API
    mexc_api = MexcAPI()
    
    # Set global constants
    MEXC_MIN_ORDER_USDT = 1.0  # Minimum order size for MEXC is 1 USDT
    
    # Test basic non-authenticated endpoint
    logger.info("Testing basic non-authenticated endpoints...")
    try:
        exchange_info = await mexc_api.get_exchange_info()
        if exchange_info:
            logger.success("✅ Successfully connected to MEXC API and retrieved exchange information")
            symbols_count = len(exchange_info.get('symbols', []))
            logger.info(f"Found {symbols_count} trading pairs")
            
            # Extract trading limits for some common pairs
            for symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']:
                symbol_info = next((s for s in exchange_info.get('symbols', []) if s.get('symbol') == symbol), None)
                if symbol_info:
                    filters = symbol_info.get('filters', [])
                    min_notional_filter = next((f for f in filters if f.get('filterType') == 'MIN_NOTIONAL'), None)
                    if min_notional_filter:
                        min_notional = float(min_notional_filter.get('minNotional', 0))
                        logger.info(f"Minimum order value for {symbol}: {min_notional} USDT")
        else:
            logger.error("❌ Failed to retrieve exchange information. API responded with empty data.")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to connect to MEXC API: {str(e)}")
        return False
    
    # Test authenticated endpoints
    logger.info("Testing authenticated endpoints...")
    
    # Test getting account information
    try:
        account_info = await mexc_api.get_account_info()
        if account_info:
            logger.success("✅ Successfully authenticated and retrieved account information")
            balances = account_info.get('balances', [])
            non_zero_balances = [b for b in balances if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0]
            logger.info(f"Found {len(non_zero_balances)} assets with non-zero balances")
            
            # Log some assets for verification
            for balance in non_zero_balances[:5]:  # Show top 5
                asset = balance.get('asset', 'UNKNOWN')
                free = float(balance.get('free', 0))
                locked = float(balance.get('locked', 0))
                logger.info(f"Asset: {asset}, Free: {free}, Locked: {locked}")
        else:
            logger.error("❌ Failed to retrieve account information. This usually indicates an authentication issue.")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to authenticate with MEXC API: {str(e)}")
        return False
    
    # Test getting open orders
    try:
        open_orders = await mexc_api.get_open_orders()
        logger.success(f"✅ Successfully retrieved open orders. Found {len(open_orders)} open orders.")
    except Exception as e:
        logger.error(f"❌ Failed to retrieve open orders: {str(e)}")
        return False
    
    # Test getting ticker price
    try:
        btc_price = await mexc_api.get_ticker_price("BTCUSDT")
        if btc_price:
            logger.success(f"✅ Successfully retrieved BTC price: {btc_price}")
        else:
            logger.error("❌ Failed to retrieve BTC price")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to retrieve ticker price: {str(e)}")
        return False
    
    # Test minimum order requirements
    logger.info("Testing minimum order requirements...")
    try:
        # Check MEXC minimum order amount
        logger.info(f"MEXC requires a minimum order amount of {MEXC_MIN_ORDER_USDT} USDT for market orders")
        logger.info("For sell orders, requirements depend on the specific trading pair")
        
        # You can uncomment this to actually test a small order, but be aware it will use real funds
        # small_amount = 1.0  # Minimum 1 USDT
        # test_symbol = "BTCUSDT"
        # logger.info(f"Testing market buy with minimum amount: {small_amount} USDT for {test_symbol}")
        # result = await mexc_api.create_market_buy_order(test_symbol, small_amount)
        # if result:
        #     logger.success(f"✅ Successfully placed minimum test order: {result}")
        # else:
        #     logger.error(f"❌ Failed to place minimum test order")
    except Exception as e:
        logger.error(f"❌ Error testing minimum orders: {str(e)}")
        logger.info("Continuing with validation anyway as this was just an informational check")
    
    logger.success("✅ All API tests passed. MEXC API connection is working correctly!")
    return True

def test_min_order_requirements():
    """Test minimum order requirements specifically."""
    logger.info("=== Testing Minimum Order Requirements ===")
    
    logger.info("MEXC requires a minimum order amount of 1.0 USDT for market orders")
    logger.info("This means:")
    logger.info("- Orders below 1.0 USDT will be rejected")
    logger.info("- For market buys, you need to specify at least 1.0 USDT")
    logger.info("- For market sells, the value depends on the asset price")
    logger.info("- When the bot detects a small order, it should automatically adjust to the minimum")
    
    logger.info("\nRecommendations:")
    logger.info("1. Make sure all market buy orders are at least 1.0 USDT")
    logger.info("2. Check that the bot correctly handles and adjusts small orders")
    logger.info("3. Consider increasing your default order sizes to avoid issues")
    
    logger.info("\nNOTE: No actual orders were placed during this test.")
    return True

async def main():
    """Run the diagnosis tool."""
    logger.info("=== MEXC API Diagnosis Tool ===")
    
    # Validate configuration first
    if not Config.validate():
        logger.error("Configuration is invalid. Please check your .env file.")
        return 1
    
    # Run basic diagnosis
    success = await diagnose_api_connection()
    
    if not success:
        logger.error("Basic API diagnosis failed. Please check the errors above.")
        return 1
    
    # Ask if user wants to test minimum order requirements
    logger.info("\nShowing minimum order requirements information:")
    test_min_order_requirements()
    
    logger.success("Diagnosis completed successfully. Your API connection is working!")
    return 0

if __name__ == "__main__":
    asyncio.run(main())
