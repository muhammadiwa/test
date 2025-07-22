import asyncio
from loguru import logger
from api.mexc_api import MexcAPI
from utils.config import Config

class SniperEngine:
    """
    Sniper Engine for executing rapid buy orders on newly listed tokens.
    
    This module is responsible for:
    - Monitoring for new token listings
    - Executing rapid buy orders with configurable frequency
    - Implementing retry logic for failed orders
    """
    
    def __init__(self, mexc_api: MexcAPI):
        """Initialize the Sniper Engine with the MEXC API client."""
        self.mexc_api = mexc_api
        self.running = False
        self.target_pairs = []  # List of trading pairs to target
        self.active_tasks = {}  # Dictionary to track active sniping tasks
        
    def add_target_pair(self, pair, usdt_amount):
        """Add a trading pair to the target list with specified USDT amount."""
        logger.info(f"Adding target pair: {pair} with {usdt_amount} USDT")
        self.target_pairs.append({
            "pair": pair,
            "usdt_amount": usdt_amount,
            "frequency_ms": Config.BUY_FREQUENCY_MS,
            "max_retries": Config.MAX_RETRY_ATTEMPTS
        })
    
    def remove_target_pair(self, pair):
        """Remove a trading pair from the target list."""
        for i, target in enumerate(self.target_pairs):
            if target["pair"] == pair:
                logger.info(f"Removing target pair: {pair}")
                self.target_pairs.pop(i)
                
                # Cancel any active sniping task for this pair
                if pair in self.active_tasks:
                    self.active_tasks[pair].cancel()
                    del self.active_tasks[pair]
                return True
        return False
    
    async def start(self):
        """Start the Sniper Engine and begin monitoring for new listings."""
        if self.running:
            logger.warning("Sniper Engine is already running")
            return
        
        self.running = True
        logger.info("Starting Sniper Engine...")
        
        # Start monitoring WebSocket for new listings
        self.monitor_task = asyncio.create_task(self._monitor_listings())
        
        # Start sniping tasks for pre-configured pairs
        for target in self.target_pairs:
            await self._start_sniping(target)
    
    async def stop(self):
        """Stop the Sniper Engine and cancel all active tasks."""
        if not self.running:
            logger.warning("Sniper Engine is not running")
            return
        
        logger.info("Stopping Sniper Engine...")
        self.running = False
        
        # Cancel monitor task if it exists
        if hasattr(self, 'monitor_task') and self.monitor_task:
            self.monitor_task.cancel()
        
        # Cancel all active sniping tasks
        for pair, task in self.active_tasks.items():
            logger.info(f"Cancelling sniping task for {pair}")
            task.cancel()
        
        self.active_tasks = {}
    
    async def _monitor_listings(self):
        """Monitor for new token listings via WebSocket."""
        logger.info("Starting to monitor for new token listings...")
        
        async def ws_message_handler(message):
            """Handle incoming WebSocket messages."""
            # Check if this is a new listing notification
            # Note: The exact format depends on MEXC's WebSocket API
            if 'e' in message and message['e'] == 'newListing':
                symbol = message.get('s')  # Symbol of the newly listed token
                logger.info(f"New token listing detected: {symbol}")
                
                # Automatically start sniping the new listing
                target = {
                    "pair": symbol,
                    "usdt_amount": Config.DEFAULT_USDT_AMOUNT,
                    "frequency_ms": Config.BUY_FREQUENCY_MS,
                    "max_retries": Config.MAX_RETRY_ATTEMPTS
                }
                await self._start_sniping(target)
        
        try:
            # Connect to WebSocket and subscribe to relevant channels
            await self.mexc_api.connect_websocket(ws_message_handler)
            await self.mexc_api.subscribe_to_new_listings()
            
            # Keep the WebSocket connection alive
            while self.running:
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Error in WebSocket monitoring: {e}")
            if self.running:
                # Try to reconnect if we're still supposed to be running
                await asyncio.sleep(5)
                self.monitor_task = asyncio.create_task(self._monitor_listings())
    
    async def _start_sniping(self, target):
        """Start a sniping task for a specific trading pair."""
        pair = target["pair"]
        usdt_amount = target["usdt_amount"]
        frequency_ms = target["frequency_ms"]
        
        logger.info(f"Starting sniping for {pair} with {usdt_amount} USDT at {frequency_ms}ms frequency")
        
        # Cancel any existing task for this pair
        if pair in self.active_tasks:
            self.active_tasks[pair].cancel()
        
        # Create and store the new task
        task = asyncio.create_task(self._snipe_pair(target))
        self.active_tasks[pair] = task
        
        # Wait briefly to ensure the task is started
        await asyncio.sleep(0.1)
    
    async def _get_price_and_quantity(self, pair, usdt_amount):
        """Get price and calculate quantity for a trading pair."""
        # First, get ticker price to calculate quantity
        ticker_info = await self.mexc_api.get_ticker_price(pair)
        if not ticker_info:
            logger.warning(f"Could not get price for {pair}, checking order book")
            
            # If ticker price is not available (new listing), check order book
            order_book = await self.mexc_api.get_order_book(pair)
            if not order_book or not order_book.get('asks') or not order_book['asks']:
                logger.error(f"Could not get order book for {pair}")
                return None, None
            
            # Use first ask price as reference
            price = float(order_book['asks'][0][0])
        else:
            price = float(ticker_info[0]['price'] if isinstance(ticker_info, list) else ticker_info['price'])
        
        # Calculate quantity based on USDT amount
        quantity = usdt_amount / price
        
        # Format quantity according to exchange requirements (adjust precision)
        quantity = round(quantity, 6)  # Adjust based on exchange requirements
        
        logger.info(f"Calculated quantity: {quantity} at price {price}")
        return price, quantity
    
    async def _execute_buy_order(self, pair, quantity, max_retries, frequency_ms):
        """Execute buy order with retry logic."""
        retry_count = 0
        
        while self.running and retry_count < max_retries:
            try:
                # Execute market buy order
                order_result = await self.mexc_api.create_market_buy_order(pair, quantity)
                
                if order_result and order_result.get('orderId'):
                    logger.success(f"Successfully placed order for {pair}: Order ID {order_result['orderId']}")
                    return True, order_result
                else:
                    logger.warning(f"Order placement failed for {pair}: {order_result}")
                    
            except Exception as e:
                logger.error(f"Error placing order for {pair}: {e}")
            
            retry_count += 1
            # Wait for the specified frequency before trying again
            await asyncio.sleep(frequency_ms / 1000)
        
        return False, None
    
    async def _snipe_pair(self, target):
        """Execute the sniping strategy for a specific pair."""
        pair = target["pair"]
        usdt_amount = target["usdt_amount"]
        frequency_ms = target["frequency_ms"]
        max_retries = target["max_retries"]
        
        logger.info(f"Sniping {pair} with {usdt_amount} USDT")
        
        try:
            # Get price and calculate quantity
            price, quantity = await self._get_price_and_quantity(pair, usdt_amount)
            if price is None or quantity is None:
                return False
            
            # Execute buy order
            success, _ = await self._execute_buy_order(pair, quantity, max_retries, frequency_ms)
            
            if not success:
                logger.error(f"Failed to place order for {pair} after {max_retries} attempts")
            
            return success
            
        except Exception as e:
            logger.error(f"Error in sniping {pair}: {e}")
            return False
