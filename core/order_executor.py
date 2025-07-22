import asyncio
from loguru import logger
from api.mexc_api import MexcAPI
from utils.config import Config

class OrderExecutor:
    """
    Order Executor for executing and managing cryptocurrency orders.
    
    This module is responsible for:
    - Executing market orders
    - Handling order filling and retries
    - Tracking order status
    """
    
    def __init__(self, mexc_api: MexcAPI):
        """Initialize the Order Executor with the MEXC API client."""
        self.mexc_api = mexc_api
        self.active_orders = {}  # Track active orders by order ID
        self.monitor_tasks = {}  # Track monitoring tasks by order ID
    
    async def execute_market_buy(self, symbol, usdt_amount):
        """
        Execute a market buy order for the specified symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            usdt_amount: Amount in USDT to spend
            
        Returns:
            Dict containing order details or None if failed
        """
        try:
            # Check minimum order amount from Config
            min_order_usdt = Config.MIN_ORDER_USDT
            if usdt_amount < min_order_usdt:
                logger.warning(f"Order amount {usdt_amount} USDT is below minimum of {min_order_usdt} USDT. Adjusting to minimum.")
                usdt_amount = min_order_usdt
            
            # Initialize variables for order processing

            # Get max retries and retry delay from config
            max_retries = Config.MAX_RETRY_ATTEMPTS
            retry_count = 0            # Initialize order variable
            order = None
            
            while retry_count <= max_retries:
                try:
                    logger.info(f"Executing market buy for {symbol}: {usdt_amount} USDT (attempt {retry_count+1}/{max_retries+1})")
                    
                    # Place market buy order (using USDT amount directly)
                    # Our improved create_market_buy_order will handle new tokens
                    order = await self.mexc_api.create_market_buy_order(symbol, usdt_amount)
                    
                    # If successful, break the retry loop
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Error on market buy attempt {retry_count+1}: {error_msg}")
                    
                    # Check if error is related to token not being available yet
                    if "Invalid symbol" in error_msg or "float division by zero" in error_msg:
                        if retry_count < max_retries:
                            retry_count += 1
                            retry_delay = Config.RETRY_DELAY
                            logger.info(f"Token may be new or not fully listed. Retrying in {retry_delay} seconds... ({retry_count}/{max_retries})")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"Max retries reached for {symbol}. Token may not be available for trading.")
                            return None
                    else:
                        # For other errors, just raise
                        logger.error(f"Error executing market buy: {error_msg}")
                        raise
            
            if order and order.get('orderId'):
                order_id = order['orderId']
                logger.success(f"Market buy order placed: {order_id}")
                
                # Get executed quantity from the order response if available
                executed_qty = float(order.get('executedQty', 0))
                
                # Track this order
                self.active_orders[order_id] = {
                    'symbol': symbol,
                    'side': 'BUY',
                    'quantity': executed_qty,  # Use executed quantity from response
                    'usdt_amount': usdt_amount,
                    'status': 'NEW',
                    'filled': False
                }
                
                # Start order monitoring
                asyncio.create_task(self._monitor_order_status(symbol, order_id))
                
                return order
            else:
                logger.error(f"Failed to place market buy order: {order}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing market buy for {symbol}: {e}")
            return None
    
    async def execute_market_sell(self, symbol, quantity):
        """
        Execute a market sell order for the specified symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            quantity: Amount of the base asset to sell
            
        Returns:
            Dict containing order details or None if failed
        """
        try:
            logger.info(f"Executing market sell for {symbol}: {quantity}")
            
            # Place market sell order
            order = await self.mexc_api.create_market_sell_order(symbol, quantity)
            
            if order and order.get('orderId'):
                order_id = order['orderId']
                logger.success(f"Market sell order placed: {order_id}")
                
                # Track this order
                self.active_orders[order_id] = {
                    'symbol': symbol,
                    'side': 'SELL',
                    'quantity': quantity,
                    'status': 'NEW',
                    'filled': False
                }
                
                # Start order monitoring
                asyncio.create_task(self._monitor_order_status(symbol, order_id))
                
                return order
            else:
                logger.error(f"Failed to place market sell order: {order}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing market sell for {symbol}: {e}")
            return None
    
    async def _monitor_order_status(self, symbol, order_id):
        """
        Monitor the status of an order until it's filled or fails.
        Implement retry logic for failed orders.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to monitor
        """
        max_retries = Config.MAX_RETRY_ATTEMPTS
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Check order status
                order_status = await self.mexc_api.get_order_status(symbol, order_id)
                
                if not order_status:
                    logger.warning(f"Could not get status for order {order_id}")
                    await asyncio.sleep(1)
                    continue
                
                # Update order status in our tracking
                if order_id in self.active_orders:
                    self.active_orders[order_id]['status'] = order_status.get('status', 'UNKNOWN')
                
                status = order_status.get('status')
                
                if status == 'FILLED':
                    logger.success(f"Order {order_id} for {symbol} has been filled!")
                    
                    if order_id in self.active_orders:
                        self.active_orders[order_id]['filled'] = True
                    
                    # Calculate and log execution details
                    executed_qty = float(order_status.get('executedQty', 0))
                    cummulative_quote_qty = float(order_status.get('cummulativeQuoteQty', 0))
                    
                    if executed_qty > 0:
                        avg_price = cummulative_quote_qty / executed_qty
                        logger.info(f"Order {order_id} executed at avg price: {avg_price} USDT")
                    
                    return True
                    
                elif status == 'PARTIALLY_FILLED':
                    # Order is in progress
                    executed_qty = float(order_status.get('executedQty', 0))
                    orig_qty = float(order_status.get('origQty', 0))
                    fill_percentage = (executed_qty / orig_qty) * 100 if orig_qty > 0 else 0
                    
                    logger.info(f"Order {order_id} is {fill_percentage:.2f}% filled. Waiting...")
                    
                elif status in ['REJECTED', 'EXPIRED', 'CANCELED']:
                    logger.warning(f"Order {order_id} has status: {status}. Attempting retry...")
                    
                    # If order failed, try again
                    if retry_count < max_retries:
                        retry_count += 1
                        
                        # Retry the order
                        if order_id in self.active_orders:
                            side = self.active_orders[order_id]['side']
                            quantity = self.active_orders[order_id]['quantity']
                            
                            logger.info(f"Retry attempt {retry_count}/{max_retries} for {symbol} {side}")
                            
                            # Place new order
                            new_order = None
                            if side == 'BUY':
                                usdt_amount = self.active_orders[order_id].get('usdt_amount')
                                if usdt_amount:
                                    new_order = await self.execute_market_buy(symbol, usdt_amount)
                            else:  # SELL
                                new_order = await self.execute_market_sell(symbol, quantity)
                            
                            # If retry succeeded, stop monitoring this order
                            if new_order:
                                return True
                    else:
                        logger.error(f"Order {order_id} failed after {max_retries} retries")
                        return False
                
                # Wait before checking again
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error monitoring order {order_id}: {e}")
                await asyncio.sleep(1)
        
        return False
