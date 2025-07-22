import asyncio
import time
from datetime import datetime
from loguru import logger
from api.mexc_api import MexcAPI
from core.order_executor import OrderExecutor
from utils.config import Config

class SellStrategyManager:
    """
    Sell Strategy Manager for handling different selling strategies.
    
    This module is responsible for:
    - Implementing take profit strategies
    - Implementing stop loss strategies
    - Implementing trailing stop strategies
    - Time-based selling
    """
    
    def __init__(self, mexc_api: MexcAPI, order_executor: OrderExecutor):
        """Initialize the Sell Strategy Manager with the MEXC API client and Order Executor."""
        self.mexc_api = mexc_api
        self.order_executor = order_executor
        self.active_strategies = {}  # Track active selling strategies
        self.monitoring_tasks = {}  # Track price monitoring tasks
    
    def add_strategy(self, symbol, buy_price, quantity, strategy_config=None):
        """
        Add a new sell strategy for a specific trading pair.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            buy_price: Price at which the asset was bought
            quantity: Quantity of the asset
            strategy_config: Dict with strategy parameters, or None to use defaults
        
        Returns:
            str: Strategy ID
        """
        if not strategy_config:
            strategy_config = {
                'take_profit_percentage': Config.PROFIT_TARGET_PERCENTAGE,
                'stop_loss_percentage': Config.STOP_LOSS_PERCENTAGE,
                'trailing_stop_percentage': Config.TRAILING_STOP_PERCENTAGE,
                'time_based_minutes': Config.TIME_BASED_SELL_MINUTES
            }
        
        strategy_id = f"{symbol}_{int(time.time())}"
        
        # Calculate target prices
        take_profit_price = buy_price * (1 + strategy_config['take_profit_percentage'] / 100)
        stop_loss_price = buy_price * (1 - strategy_config['stop_loss_percentage'] / 100)
        
        # Store strategy details
        self.active_strategies[strategy_id] = {
            'symbol': symbol,
            'buy_price': buy_price,
            'quantity': quantity,
            'take_profit_price': take_profit_price,
            'stop_loss_price': stop_loss_price,
            'trailing_stop_percentage': strategy_config['trailing_stop_percentage'],
            'trailing_stop_price': None,  # Will be set when take profit is hit
            'highest_price': buy_price,
            'time_based_minutes': strategy_config['time_based_minutes'],
            'start_time': datetime.now(),
            'status': 'ACTIVE',
            'executed': False
        }
        
        logger.info(f"Added sell strategy for {symbol}: TP={take_profit_price:.8f}, SL={stop_loss_price:.8f}")
        
        # Start price monitoring for this strategy
        monitoring_task = asyncio.create_task(self._monitor_price(strategy_id))
        self.monitoring_tasks[strategy_id] = monitoring_task
        
        return strategy_id
    
    def remove_strategy(self, strategy_id):
        """
        Remove a sell strategy.
        
        Args:
            strategy_id: ID of the strategy to remove
        
        Returns:
            bool: True if successful, False otherwise
        """
        if strategy_id in self.active_strategies:
            # Cancel monitoring task
            if strategy_id in self.monitoring_tasks:
                self.monitoring_tasks[strategy_id].cancel()
                del self.monitoring_tasks[strategy_id]
            
            # Remove strategy
            del self.active_strategies[strategy_id]
            logger.info(f"Removed sell strategy {strategy_id}")
            return True
        
        logger.warning(f"Strategy {strategy_id} not found")
        return False
    
    async def _check_time_based_selling(self, strategy_id):
        """Check if time-based selling should be triggered."""
        strategy = self.active_strategies[strategy_id]
        symbol = strategy['symbol']
        
        if strategy['time_based_minutes'] > 0:
            elapsed_minutes = (datetime.now() - strategy['start_time']).total_seconds() / 60
            if elapsed_minutes >= strategy['time_based_minutes']:
                logger.info(f"Time-based selling triggered for {symbol} after {elapsed_minutes:.1f} minutes")
                await self._execute_sell(strategy_id, "TIME_BASED")
                return True
        return False
    
    def _update_price_tracking(self, strategy_id, current_price):
        """Update highest price and trailing stop if needed."""
        strategy = self.active_strategies[strategy_id]
        symbol = strategy['symbol']
        
        if current_price > strategy['highest_price']:
            strategy['highest_price'] = current_price
            self.active_strategies[strategy_id] = strategy
            
            # If take profit was hit, set trailing stop
            if not strategy['trailing_stop_price'] and current_price >= strategy['take_profit_price']:
                trailing_stop = current_price * (1 - strategy['trailing_stop_percentage'] / 100)
                strategy['trailing_stop_price'] = trailing_stop
                self.active_strategies[strategy_id] = strategy
                logger.info(f"{symbol} hit take profit! Setting trailing stop at {trailing_stop:.8f}")
    
    async def _get_current_price(self, symbol):
        """Get current price for a symbol."""
        ticker = await self.mexc_api.get_ticker_price(symbol)
        if not ticker:
            return None
        
        return float(ticker[0]['price'] if isinstance(ticker, list) else ticker['price'])
    
    async def _monitor_price(self, strategy_id):
        """
        Monitor price and execute strategy when conditions are met.
        
        Args:
            strategy_id: ID of the strategy to monitor
        """
        if strategy_id not in self.active_strategies:
            logger.error(f"Strategy {strategy_id} not found")
            return
        
        strategy = self.active_strategies[strategy_id]
        symbol = strategy['symbol']
        
        logger.info(f"Starting price monitoring for {symbol} with strategy {strategy_id}")
        
        try:
            while strategy_id in self.active_strategies and not strategy['executed']:
                # Check if time-based selling is due
                if await self._check_time_based_selling(strategy_id):
                    break
                
                # Get current price
                current_price = await self._get_current_price(symbol)
                if not current_price:
                    logger.warning(f"Could not get price for {symbol}, retrying in 1s...")
                    await asyncio.sleep(1)
                    continue
                
                # Update price tracking data
                self._update_price_tracking(strategy_id, current_price)
                
                # Check if price triggers a sell
                if self._should_sell(strategy_id, current_price):
                    reason = self._get_sell_reason(strategy_id, current_price)
                    await self._execute_sell(strategy_id, reason)
                    break
                
                # Wait before checking again
                await asyncio.sleep(0.5)
                
        except asyncio.CancelledError:
            logger.info(f"Price monitoring for {symbol} cancelled")
            raise  # Re-raise CancelledError after logging
        except Exception as e:
            logger.error(f"Error in price monitoring for {symbol}: {e}")
    
    def _should_sell(self, strategy_id, current_price):
        """
        Determine if a strategy should trigger a sell at the current price.
        
        Args:
            strategy_id: Strategy ID
            current_price: Current price of the asset
            
        Returns:
            bool: True if should sell, False otherwise
        """
        if strategy_id not in self.active_strategies:
            return False
        
        strategy = self.active_strategies[strategy_id]
        
        # Check stop loss
        if current_price <= strategy['stop_loss_price']:
            return True
        
        # Check trailing stop if activated
        if strategy['trailing_stop_price'] and current_price <= strategy['trailing_stop_price']:
            return True
        
        # Check take profit if no trailing stop is set
        if not strategy['trailing_stop_price'] and current_price >= strategy['take_profit_price']:
            return True
        
        return False
    
    def _get_sell_reason(self, strategy_id, current_price):
        """Get the reason for selling."""
        if strategy_id not in self.active_strategies:
            return "UNKNOWN"
        
        strategy = self.active_strategies[strategy_id]
        
        if current_price <= strategy['stop_loss_price']:
            return "STOP_LOSS"
        
        if strategy['trailing_stop_price'] and current_price <= strategy['trailing_stop_price']:
            return "TRAILING_STOP"
        
        if current_price >= strategy['take_profit_price']:
            return "TAKE_PROFIT"
        
        return "UNKNOWN"
    
    async def _execute_sell(self, strategy_id, reason):
        """
        Execute a sell order for a strategy.
        
        Args:
            strategy_id: Strategy ID
            reason: Reason for selling
        """
        if strategy_id not in self.active_strategies:
            logger.error(f"Strategy {strategy_id} not found")
            return False
        
        strategy = self.active_strategies[strategy_id]
        symbol = strategy['symbol']
        quantity = strategy['quantity']
        buy_price = strategy['buy_price']
        
        logger.info(f"Executing sell for {symbol} ({strategy_id}) - Reason: {reason}")
        
        try:
            # Execute market sell order
            sell_order = await self.order_executor.execute_market_sell(symbol, quantity)
            
            if sell_order and sell_order.get('orderId'):
                # Mark strategy as executed
                strategy['status'] = 'EXECUTED'
                strategy['executed'] = True
                strategy['sell_reason'] = reason
                strategy['sell_time'] = datetime.now()
                self.active_strategies[strategy_id] = strategy
                
                # Get execution details for profit calculation
                sell_price = float(sell_order.get('price', 0))
                profit_percentage = ((sell_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                
                logger.success(f"Sold {symbol} at {sell_price:.8f} ({profit_percentage:.2f}% {'profit' if profit_percentage >= 0 else 'loss'})")
                
                return True
            else:
                logger.error(f"Failed to execute sell for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing sell for {symbol}: {e}")
            return False
