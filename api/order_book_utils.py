import asyncio
from loguru import logger
from decimal import Decimal, getcontext

# Set high precision for decimal calculations
getcontext().prec = 10

async def calculate_buy_from_orderbook(mexc_api, symbol, usdt_amount):
    """
    Calculate optimal buy quantity and price based on order book depth.
    This is especially useful for new listings where market data might be limited.
    
    Args:
        mexc_api: The MEXC API client instance
        symbol: Trading pair symbol (e.g. "BTCUSDT")
        usdt_amount: Amount in USDT to spend
    
    Returns:
        tuple: (expected_quantity, average_price)
    """
    try:
        # Get order book with sufficient depth
        depth = 100  # Request a good depth to see more price levels
        order_book = await mexc_api.get_order_book(symbol, depth)
        
        if not order_book or 'asks' not in order_book:
            logger.warning(f"Could not get order book for {symbol}")
            return None, None
        
        asks = order_book['asks']
        if not asks:
            logger.warning(f"No sell orders found in order book for {symbol}")
            return None, None
        
        # Calculate how many tokens we can buy with the USDT amount
        usdt_remaining = Decimal(str(usdt_amount))
        total_quantity = Decimal('0')
        total_cost = Decimal('0')
        
        for price_level in asks:
            price = Decimal(str(price_level[0]))
            available_qty = Decimal(str(price_level[1]))
            
            # Calculate how much we can buy at this price level
            cost_at_level = price * available_qty
            
            if usdt_remaining >= cost_at_level:
                # We can buy the entire level
                total_quantity += available_qty
                total_cost += cost_at_level
                usdt_remaining -= cost_at_level
            else:
                # We can only buy part of this level
                partial_qty = usdt_remaining / price
                total_quantity += partial_qty
                total_cost += usdt_remaining
                usdt_remaining = Decimal('0')
                break
                
        if total_quantity > 0:
            avg_price = total_cost / total_quantity
            logger.info(f"Order book calculation for {symbol}: {float(total_quantity)} tokens at avg price {float(avg_price)}")
            return float(total_quantity), float(avg_price)
        else:
            logger.warning(f"Could not calculate buy quantity from order book for {symbol}")
            return None, None
            
    except Exception as e:
        logger.error(f"Error calculating from order book for {symbol}: {str(e)}")
        return None, None

async def simulate_market_buy(mexc_api, symbol, usdt_amount):
    """
    Simulate a market buy to estimate execution price and quantity.
    Useful for new listings or low liquidity pairs.
    
    Args:
        mexc_api: The MEXC API client instance
        symbol: Trading pair symbol
        usdt_amount: Amount in USDT to spend
    
    Returns:
        dict: Simulated order result with estimated price and quantity
    """
    quantity, avg_price = await calculate_buy_from_orderbook(mexc_api, symbol, usdt_amount)
    
    if quantity is None:
        return None
        
    # Create a simulated order result
    return {
        'symbol': symbol,
        'side': 'BUY',
        'type': 'MARKET',
        'estimatedPrice': avg_price,
        'estimatedQuantity': quantity,
        'totalCost': usdt_amount,
        'isSimulation': True
    }
