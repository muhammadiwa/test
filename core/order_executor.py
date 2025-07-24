import asyncio
import time
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
        self.sell_strategy_manager = None  # Will be set after initialization
        self.order_callbacks = {}  # Callbacks to be executed after order is filled
    
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
                
                # Check for executed quantity in the response
                executed_qty = 0.0
                
                # Try to get the quantity from different fields in the response
                if 'executedQty' in order and order['executedQty']:
                    executed_qty = float(order['executedQty'])
                elif 'origQty' in order and order['origQty']:
                    # For market orders with quoteOrderQty, origQty might be calculated
                    executed_qty = float(order['origQty'])
                
                # If quantity is still 0, we need to fetch it from the order status
                if executed_qty <= 0:
                    logger.warning("Could not determine quantity from order response, fetching order status")
                    order_status = await self.mexc_api.get_order_status(symbol, order_id)
                    if order_status and 'executedQty' in order_status:
                        executed_qty = float(order_status['executedQty'])
                
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
    
    async def execute_market_sell(self, symbol, quantity=None, max_retries=3):
        """
        Execute a market sell order for the specified symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            quantity: Amount of the base asset to sell (optional, if None, will sell all available)
            max_retries: Maximum number of retries for API calls
            
        Returns:
            Dict containing order details or None if failed
        """
        retries = 0
        while retries <= max_retries:
            try:
                logger.info(f"Executing market sell for {symbol}: {quantity if quantity else 'all available'}")
                
                # Place market sell order - if quantity is None, the API will use all available balance
                order = await self.mexc_api.create_market_sell_order(symbol, quantity)
                
                if order and order.get('orderId'):
                    order_id = order['orderId']
                    logger.success(f"Market sell order placed: {order_id}")
                    
                    # Initialize executed_qty
                    executed_qty = 0.0
                    
                    # Try to get the quantity from different fields in the response
                    if 'executedQty' in order and order['executedQty']:
                        executed_qty = float(order['executedQty'])
                    elif 'origQty' in order and order['origQty']:
                        executed_qty = float(order['origQty'])
                    
                    # If quantity is still 0, and we had a quantity parameter, use that
                    if executed_qty <= 0 and quantity:
                        executed_qty = float(quantity)
                    
                    # If we still don't have a quantity, fetch from order status
                    if executed_qty <= 0:
                        logger.warning("Could not determine quantity from sell order response, fetching order status")
                        order_status = await self.mexc_api.get_order_status(symbol, order_id)
                        if order_status and 'executedQty' in order_status:
                            executed_qty = float(order_status['executedQty'])
                    
                    # Track this order
                    self.active_orders[order_id] = {
                        'symbol': symbol,
                        'side': 'SELL',
                        'quantity': executed_qty,
                        'status': 'NEW',
                        'filled': False
                    }
                    
                    # Start order monitoring
                    asyncio.create_task(self._monitor_order_status(symbol, order_id))
                    
                    return order
                else:
                    # If order is None or doesn't have an orderId, retry
                    retries += 1
                    if retries <= max_retries:
                        logger.warning(f"Failed to place market sell order. Retrying ({retries}/{max_retries})...")
                        await asyncio.sleep(1.0)  # Wait before retrying
                    else:
                        logger.error(f"Failed to place market sell order after {max_retries} attempts: {order}")
                        return None
                        
            except Exception as e:
                retries += 1
                if retries <= max_retries:
                    logger.warning(f"Error executing market sell for {symbol}: {e}. Retrying ({retries}/{max_retries})...")
                    await asyncio.sleep(1.0)  # Wait before retrying
                else:
                    logger.error(f"Error executing market sell for {symbol} after {max_retries} attempts: {e}")
                    return None
                    
        # This should not be reached due to the returns above, but just in case
        return None
    
    async def _monitor_order_status(self, symbol, order_id):
        """
        Monitor the status of an order until it's filled or fails.
        Implement retry logic for failed orders.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to monitor
        """
        # Log all currently registered callbacks at start of monitoring
        logger.info(f"Starting to monitor order {order_id} - Registered callbacks: {list(self.order_callbacks.keys())}")
        max_retries = Config.MAX_RETRY_ATTEMPTS
        retry_count = 0
        
        # Set a maximum monitoring time (300 seconds = 5 minutes)
        max_monitoring_time = 300  # seconds
        start_time = time.time()
        
        while retry_count <= max_retries:
            try:
                # Check if we've exceeded the maximum monitoring time
                if time.time() - start_time > max_monitoring_time:
                    logger.warning(f"Exceeded maximum monitoring time ({max_monitoring_time}s) for order {order_id}. Aborting.")
                    if order_id in self.active_orders:
                        self.active_orders[order_id]['status'] = 'TIMEOUT'
                    return False
                
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
                    
                    # Get detailed order information
                    order_details = await self.mexc_api.get_filled_order_details(symbol, order_id)
                    
                    if order_details:
                        executed_qty = order_details['quantity']
                        avg_price = order_details['price']
                        quote_qty = order_details['value']
                        
                        # Update our tracking with actual executed quantity
                        if order_id in self.active_orders:
                            self.active_orders[order_id]['filled'] = True
                            self.active_orders[order_id]['quantity'] = executed_qty
                            
                            # If this is a buy order, add sell strategy with ACCURATE execution price
                            # ONLY if no strategy exists for this symbol yet (prevent double strategy)
                            if self.active_orders[order_id]['side'] == 'BUY' and self.sell_strategy_manager:
                                # Check if a strategy already exists for this symbol
                                if not self.sell_strategy_manager.has_strategy_for_symbol(symbol):
                                    # Only create strategy if it's a buy order and we have a strategy manager
                                    try:
                                        # Use the ACTUAL executed average price for setting up sell strategy
                                        self.sell_strategy_manager.add_strategy(symbol, avg_price, executed_qty)
                                        logger.info(f"Added sell strategy for {symbol} based on execution price {avg_price:.8f}")
                                    except Exception as e:
                                        logger.error(f"Error adding sell strategy for {symbol}: {e}")
                                else:
                                    logger.info(f"Strategy for {symbol} already exists, not creating a new one")
                            
                        logger.info(f"Order {order_id} executed: {executed_qty} {symbol.replace('USDT', '')} at avg price: {avg_price:.8f} USDT, total: {quote_qty:.2f} USDT")
                        
                        # Convert order_id to string for consistent lookup
                        str_order_id = str(order_id)
                        
                        # Execute any registered callbacks with the ACTUAL execution price and quantity
                        if str_order_id in self.order_callbacks:
                            logger.info(f"Found {len(self.order_callbacks[str_order_id])} callbacks for order {str_order_id}")
                            for callback in self.order_callbacks[str_order_id]:
                                try:
                                    logger.info(f"Executing callback for order {str_order_id} with {symbol}, {executed_qty}, {avg_price}, {quote_qty}")
                                    await callback(symbol, executed_qty, avg_price, quote_qty)
                                    logger.info(f"Callback execution completed for order {str_order_id}")
                                except Exception as e:
                                    logger.error(f"Error executing callback for order {str_order_id}: {e}", exc_info=True)
                            # Clear callbacks after execution
                            del self.order_callbacks[str_order_id]
                            logger.info(f"Cleared callbacks for order {str_order_id}")
                        else:
                            # Check if maybe the order_id is not a string in the dictionary
                            logger.warning(f"No callbacks found for order {str_order_id} - Available order_ids: {list(self.order_callbacks.keys())}")
                    else:
                        # Fall back to order status response if detailed info not available
                        if order_id in self.active_orders:
                            self.active_orders[order_id]['filled'] = True
                        
                        executed_qty = float(order_status.get('executedQty', 0))
                        cummulative_quote_qty = float(order_status.get('cummulativeQuoteQty', 0))
                        
                        if executed_qty > 0:
                            avg_price = cummulative_quote_qty / executed_qty
                            logger.info(f"Order {order_id} executed at avg price: {avg_price} USDT")
                            
                            # Execute callbacks even if we had to fall back to basic order info
                            if order_id in self.order_callbacks:
                                for callback in self.order_callbacks[order_id]:
                                    try:
                                        await callback(symbol, executed_qty, avg_price, cummulative_quote_qty)
                                    except Exception as e:
                                        logger.error(f"Error executing callback for order {order_id}: {e}")
                                # Clear callbacks after execution
                                del self.order_callbacks[order_id]
                    
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
        
    def register_order_callback(self, order_id, callback):
        """
        Register a callback to be executed when an order is filled.
        
        Args:
            order_id: The order ID (string or int)
            callback: Async function to call with (symbol, quantity, price, total) when order is filled.
                      Must be defined with: async def callback(symbol, executed_qty, avg_price, total_value)
        
        Note:
            This method accepts and stores an async callback function, but does not call it.
            The callback will be invoked when the order is detected as filled in _monitor_order_status.
        """
        # Convert order_id to string for consistency
        order_id = str(order_id)
        
        if order_id not in self.order_callbacks:
            self.order_callbacks[order_id] = []
        
        self.order_callbacks[order_id].append(callback)
        logger.info(f"Registered callback for order {order_id} - Current callbacks: {len(self.order_callbacks[order_id])}")
        
        # Log all currently registered callbacks for debugging
        logger.info(f"Active callbacks for orders: {list(self.order_callbacks.keys())}")
        return True  # Return immediately for synchronous operation
