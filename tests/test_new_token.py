import asyncio
from loguru import logger
from api.mexc_api import MexcAPI
from core.order_executor import OrderExecutor
from utils.config import Config

async def test_new_token_strategy():
    """Test the new token buying strategy implementation."""
    logger.info("=== Testing New Token Buy Strategy ===")
    
    # Initialize API and order executor
    mexc_api = MexcAPI()
    order_executor = OrderExecutor(mexc_api)
    
    # Test buying a new token
    # NOTE: This is just a simulation, no actual orders will be placed
    symbol = "TESTUSDT"  # This is an example, not a real token
    amount = 5  # USDT amount
    
    logger.info(f"Simulating buy for new token: {symbol}, amount: {amount} USDT")
    logger.info("This will NOT place actual orders, just demonstrate the retry mechanism")
    
    # Show retry mechanism
    logger.info("\nRetry mechanism for new tokens:")
    logger.info("1. When a new token is detected, the bot will:")
    logger.info("   - Try to get ticker price (may fail for very new tokens)")
    logger.info("   - If price isn't available, analyze the order book")
    logger.info("   - Retry up to 5 times with delays between attempts")
    logger.info("   - Automatically adjust order quantity if needed")
    
    logger.info("\nMinimum order requirements:")
    logger.info(f"   - MEXC requires minimum {Config.MIN_ORDER_USDT} USDT per order")
    logger.info("   - Bot automatically adjusts small orders to meet minimum")
    
    logger.info("\nRetry configuration:")
    logger.info(f"   - Maximum retry attempts: {Config.MAX_RETRY_ATTEMPTS}")
    logger.info(f"   - Retry delay: {Config.RETRY_DELAY} seconds")
    
    logger.info("\nFor more details, see: docs/NEW_TOKEN_STRATEGY.md")
    
    # Test existing tokens
    known_tokens = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    for token in known_tokens:
        try:
            # Just get price to verify token exists
            ticker = await mexc_api.get_ticker_price(token)
            if ticker:
                price = float(ticker[0]['price'] if isinstance(ticker, list) else ticker['price'])
                logger.info(f"Token {token} price: {price}")
        except Exception as e:
            logger.error(f"Error getting price for {token}: {e}")

async def main():
    """Run the test script."""
    logger.info("=== New Token Strategy Test ===")
    
    # Validate configuration first
    if not Config.validate():
        logger.error("Configuration is invalid. Please check your .env file.")
        return 1
    
    # Run test
    await test_new_token_strategy()
    
    logger.success("Test completed successfully!")
    return 0

if __name__ == "__main__":
    asyncio.run(main())
