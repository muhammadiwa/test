import asyncio
import sys
from loguru import logger
from utils.config import Config
from api.mexc_api import MexcAPI

async def test_api_connection():
    """Test connection to MEXC API."""
    logger.info("Testing connection to MEXC API...")
    
    # Validate configuration
    if not Config.validate():
        logger.error("Invalid configuration. Please check your .env file.")
        return False
    
    # Initialize API
    mexc_api = MexcAPI()
    
    try:
        # Test public endpoint
        exchange_info = await mexc_api.get_exchange_info()
        if not exchange_info:
            logger.error("Could not connect to MEXC API.")
            return False
        
        logger.success("Successfully connected to MEXC API")
        logger.info(f"Found {len(exchange_info.get('symbols', []))} trading pairs")
        
        # Test ticker price
        ticker = await mexc_api.get_ticker_price("BTCUSDT")
        if ticker:
            price = float(ticker[0]['price'] if isinstance(ticker, list) else ticker['price'])
            logger.info(f"Current BTC price: {price} USDT")
        
        # Test authenticated endpoint
        if mexc_api.api_key and mexc_api.api_secret:
            account_info = await mexc_api.get_account_info()
            if account_info and 'balances' in account_info:
                non_zero = [b for b in account_info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
                logger.info(f"Account has {len(non_zero)} assets with non-zero balance")
                
                for balance in non_zero[:5]:  # Show top 5
                    logger.info(f"  {balance['asset']}: {balance['free']} (free) + {balance['locked']} (locked)")
                
                if len(non_zero) > 5:
                    logger.info(f"  ... and {len(non_zero) - 5} more assets")
            else:
                logger.warning("Could not retrieve account info. API key may not have sufficient permissions.")
        else:
            logger.warning("API key not configured. Skipping authenticated endpoint test.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error connecting to MEXC API: {e}")
        return False
    finally:
        # Close WebSocket connection if it exists
        if hasattr(mexc_api, 'ws') and mexc_api.ws:
            await mexc_api.close_websocket()

async def test_websocket():
    """Test WebSocket connection to MEXC."""
    logger.info("Testing WebSocket connection to MEXC...")
    
    # Initialize API
    mexc_api = MexcAPI()
    
    try:
        # Define a simple message handler
        async def ws_message_handler(message):
            logger.info(f"WebSocket message received: {message}")
        
        # Connect to WebSocket
        await mexc_api.connect_websocket(ws_message_handler)
        
        # Subscribe to ticker updates for BTC
        await mexc_api.subscribe_to_ticker("BTCUSDT")
        
        logger.success("WebSocket connection established")
        logger.info("Waiting for messages (Ctrl+C to exit)...")
        
        # Keep the connection open for a while
        try:
            await asyncio.sleep(30)  # Wait for 30 seconds
        except asyncio.CancelledError:
            logger.info("WebSocket test cancelled")
            raise  # Re-raise for proper cleanup
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing WebSocket: {e}")
        return False
    finally:
        # Close WebSocket connection if it exists
        if hasattr(mexc_api, 'ws') and mexc_api.ws:
            await mexc_api.close_websocket()

async def main():
    """Run tests."""
    try:
        # Test API connection
        if not await test_api_connection():
            return 1
        
        # Ask if user wants to test WebSocket
        print("\nDo you want to test WebSocket connection? (y/n): ", end="")
        response = await asyncio.to_thread(input)
        response = response.strip().lower()
        
        if response == 'y' and not await test_websocket():
            return 1
        
        logger.success("All tests completed")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
