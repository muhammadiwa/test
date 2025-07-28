import asyncio
import time
from datetime import datetime
from loguru import logger
from api.mexc_api import MexcAPI
from core.order_executor import OrderExecutor
from utils.config import Config
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.database_manager import DatabaseManager

class SellStrategyManager:
    """
    Sell Strategy Manager for handling different selling strategies.
    
    This module is responsible for:
    - Implementing take profit strategies
    - Implementing stop loss strategies
    - Implementing trailing stop strategies
    - Time-based selling
    - Persistent storage of strategies in database
    """
    
    def __init__(self, mexc_api: MexcAPI, order_executor: 'OrderExecutor', database_manager = None):
        """Initialize the Sell Strategy Manager with the MEXC API client, Order Executor, and Database Manager."""
        self.mexc_api = mexc_api
        self.order_executor = order_executor
        self.database_manager = database_manager
        self.active_strategies = {}  # Track active selling strategies (cached from DB)
        self.monitoring_tasks = {}  # Track price monitoring tasks
        self.sell_callbacks = []  # Callbacks for when a sell is executed
        
        # Load active strategies from database if available
        if self.database_manager:
            asyncio.create_task(self._load_strategies_from_db())
    
    async def _load_strategies_from_db(self):
        """Load active strategies from database on startup."""
        try:
            if not self.database_manager:
                return
                
            logger.info("Loading active strategies from database...")
            strategies = await self.database_manager.load_active_strategies()
            
            for strategy_id, strategy_data in strategies.items():
                self.active_strategies[strategy_id] = strategy_data
                # Restart monitoring for each strategy
                monitoring_task = asyncio.create_task(self._monitor_price(strategy_id))
                self.monitoring_tasks[strategy_id] = monitoring_task
                
            logger.info(f"Loaded {len(strategies)} active strategies from database")
            
        except Exception as e:
            logger.error(f"Failed to load strategies from database: {e}")
    
    async def _save_strategy_to_db(self, strategy_id: str):
        """Save strategy to database."""
        if not self.database_manager or strategy_id not in self.active_strategies:
            return
            
        try:
            strategy_data = self.active_strategies[strategy_id]
            await self.database_manager.save_strategy(strategy_id, strategy_data)
            logger.debug(f"Strategy {strategy_id} saved to database")
        except Exception as e:
            logger.error(f"Failed to save strategy {strategy_id} to database: {e}")
    
    async def _remove_strategy_from_db(self, strategy_id: str):
        """Remove strategy from database."""
        if not self.database_manager:
            return
            
        try:
            await self.database_manager.remove_strategy(strategy_id)
            logger.debug(f"Strategy {strategy_id} removed from database")
        except Exception as e:
            logger.error(f"Failed to remove strategy {strategy_id} from database: {e}")
    
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
                'tp_sell_percentage': Config.TP_SELL_PERCENTAGE,
                'stop_loss_percentage': Config.STOP_LOSS_PERCENTAGE,
                'trailing_stop_percentage': Config.TRAILING_STOP_PERCENTAGE,
                'tsl_min_activation_percentage': Config.TSL_MIN_ACTIVATION_PERCENTAGE,
                'time_based_minutes': Config.TIME_BASED_SELL_MINUTES
            }
        
        strategy_id = f"{symbol}_{int(time.time())}"
        
        # Calculate target prices
        take_profit_price = buy_price * (1 + strategy_config['take_profit_percentage'] / 100)
        stop_loss_price = buy_price * (1 - strategy_config['stop_loss_percentage'] / 100)
        tsl_activation_price = buy_price * (1 + strategy_config['tsl_min_activation_percentage'] / 100)
        
        # Store strategy details
        self.active_strategies[strategy_id] = {
            'symbol': symbol,
            'buy_price': buy_price,
            'quantity': quantity,
            'original_quantity': quantity,  # Keep track of original quantity for partial sells
            'take_profit_price': take_profit_price,
            'tp_sell_percentage': strategy_config['tp_sell_percentage'],
            'tp_executed': False,  # Track if take profit has been executed
            'stop_loss_price': stop_loss_price,
            'trailing_stop_percentage': strategy_config['trailing_stop_percentage'],
            'trailing_stop_price': None,  # Will be set when activation condition is met
            'tsl_min_activation_percentage': strategy_config['tsl_min_activation_percentage'],
            'tsl_activation_price': tsl_activation_price,
            'tsl_activated': False,  # Track if TSL has been activated
            'highest_price': buy_price,
            'time_based_minutes': strategy_config['time_based_minutes'],
            'start_time': datetime.now(),
            'status': 'ACTIVE',
            'executed': False
        }
        
        # Save to database
        asyncio.create_task(self._save_strategy_to_db(strategy_id))
        
        # Log details with TSL activation price
        logger.info(f"Added sell strategy for {symbol}: TP={take_profit_price:.8f} ({strategy_config['tp_sell_percentage']}%), " +
                    f"SL={stop_loss_price:.8f}, TSL={strategy_config['trailing_stop_percentage']}% " +
                    f"(activates at {tsl_activation_price:.8f})")
        
        # Start price monitoring for this strategy
        monitoring_task = asyncio.create_task(self._monitor_price(strategy_id))
        self.monitoring_tasks[strategy_id] = monitoring_task
        
        return strategy_id
    
    def register_sell_callback(self, callback):
        """
        Register a callback to be called when a sell order is executed.
        
        Args:
            callback: Async function to call with (symbol, buy_price, sell_price, quantity, reason)
        """
        self.sell_callbacks.append(callback)
        logger.debug(f"Registered sell callback, total callbacks: {len(self.sell_callbacks)}")
        
    def has_strategy_for_symbol(self, symbol):
        """
        Check if a strategy already exists for the given symbol.
        NOTE: This function is now mainly for backwards compatibility.
        With multiple strategies support, this returns True if ANY active strategy exists for the symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            bool: True if any active strategy exists, False otherwise
        """
        # Check all active strategies for this symbol
        for strategy_id, strategy in self.active_strategies.items():
            if strategy['symbol'] == symbol and strategy['status'] == 'ACTIVE' and not strategy['executed']:
                return True
        return False
    
    def get_strategies_for_symbol(self, symbol):
        """
        Get all active strategies for a given symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            dict: Dictionary of strategy_id -> strategy for the symbol
        """
        strategies = {}
        for strategy_id, strategy in self.active_strategies.items():
            if strategy['symbol'] == symbol and strategy['status'] == 'ACTIVE' and not strategy['executed']:
                strategies[strategy_id] = strategy
        return strategies
    
    def get_total_quantity_for_symbol(self, symbol):
        """
        Get total quantity across all active strategies for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            float: Total quantity being monitored for this symbol
        """
        total_qty = 0.0
        for strategy_id, strategy in self.active_strategies.items():
            if strategy['symbol'] == symbol and strategy['status'] == 'ACTIVE' and not strategy['executed']:
                total_qty += strategy['quantity']
        return total_qty
    
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
            
            # Remove from database
            asyncio.create_task(self._remove_strategy_from_db(strategy_id))
            
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
        update_needed = False
        
        # Update highest price tracking
        if current_price > strategy['highest_price']:
            strategy['highest_price'] = current_price
            update_needed = True
            
            # Check if TSL activation condition is met
            if not strategy['tsl_activated'] and strategy['trailing_stop_percentage'] > 0:
                # If price has risen enough to activate TSL
                if current_price >= strategy['tsl_activation_price']:
                    # Calculate trailing stop price based on current price
                    trailing_stop = current_price * (1 - strategy['trailing_stop_percentage'] / 100)
                    strategy['trailing_stop_price'] = trailing_stop
                    strategy['tsl_activated'] = True
                    update_needed = True
                    logger.info(f"{symbol} TSL activated! Price {current_price:.8f} >= activation {strategy['tsl_activation_price']:.8f}, " +
                               f"setting trailing stop at {trailing_stop:.8f}")
            
            # If TSL is already active, update the trailing stop as price goes higher
            elif strategy['tsl_activated'] and strategy['trailing_stop_percentage'] > 0:
                # Calculate new trailing stop based on new highest price
                new_trailing_stop = current_price * (1 - strategy['trailing_stop_percentage'] / 100)
                
                # Only update if new trailing stop is higher than current one
                if not strategy['trailing_stop_price'] or new_trailing_stop > strategy['trailing_stop_price']:
                    strategy['trailing_stop_price'] = new_trailing_stop
                    update_needed = True
                    logger.debug(f"{symbol} updated trailing stop to {new_trailing_stop:.8f} as price reached {current_price:.8f}")
        
        # Update strategy in memory
        if update_needed:
            self.active_strategies[strategy_id] = strategy
            # Save price data and strategy update to database
            if self.database_manager:
                asyncio.create_task(self.database_manager.save_price_data(symbol, current_price))
                asyncio.create_task(self._save_strategy_to_db(strategy_id))
    
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
        
        # Log detailed strategy parameters for better understanding
        tsl_config = f"TSL {strategy['trailing_stop_percentage']}% (activates at {strategy['tsl_activation_price']:.8f})"
        tp_config = f"TP {strategy['take_profit_price']:.8f} (sell {strategy['tp_sell_percentage']}%)"
        sl_config = f"SL {strategy['stop_loss_price']:.8f}"
        logger.info(f"Starting price monitoring for {symbol} with strategy {strategy_id}: {tp_config}, {sl_config}, {tsl_config}")
        
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
                
                # Update price tracking data and trailing stop if needed
                self._update_price_tracking(strategy_id, current_price)
                
                # Refetch the strategy to get updated values
                strategy = self.active_strategies[strategy_id]
                
                # Check if price triggers a sell (either TP, SL, or TSL)
                if self._should_sell(strategy_id, current_price):
                    reason = self._get_sell_reason(strategy_id, current_price)
                    result = await self._execute_sell(strategy_id, reason)
                    
                    # Check if strategy still exists (it might have been removed in _execute_sell)
                    if strategy_id not in self.active_strategies:
                        logger.info(f"Strategy {strategy_id} was removed, stopping monitoring")
                        break
                        
                    # Refresh strategy state after sell execution
                    strategy = self.active_strategies[strategy_id]
                    
                    # If it was a full sell or the sell failed, break the loop
                    if not result or strategy['executed']:
                        break
                    # Otherwise, it was a partial sell and we continue monitoring
                
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
        
        # Check stop loss (always sells everything)
        if current_price <= strategy['stop_loss_price']:
            return True
        
        # Check trailing stop if activated (sells remaining position)
        if strategy['tsl_activated'] and strategy['trailing_stop_price'] and current_price <= strategy['trailing_stop_price']:
            return True
        
        # Check take profit (sells percentage defined in tp_sell_percentage)
        if not strategy['tp_executed'] and current_price >= strategy['take_profit_price']:
            return True
        
        return False
    
    def _get_sell_reason(self, strategy_id, current_price):
        """Get the reason for selling."""
        if strategy_id not in self.active_strategies:
            return "UNKNOWN"
        
        strategy = self.active_strategies[strategy_id]
        
        if current_price <= strategy['stop_loss_price']:
            return "STOP_LOSS"
        
        if strategy['tsl_activated'] and strategy['trailing_stop_price'] and current_price <= strategy['trailing_stop_price']:
            return "TRAILING_STOP"
        
        if current_price >= strategy['take_profit_price']:
            # If selling less than 100%, indicate partial TP
            if strategy['tp_sell_percentage'] < 100:
                return f"TAKE_PROFIT_PARTIAL_{strategy['tp_sell_percentage']}PCT"
            else:
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
        buy_price = strategy['buy_price']
        
        # Determine sell quantity based on reason and configuration
        is_partial_sell = False
        sell_percentage = 100.0
        current_quantity = strategy['quantity']
        
        # For take profit with partial selling
        if reason.startswith("TAKE_PROFIT") and not strategy['tp_executed'] and strategy['tp_sell_percentage'] < 100:
            is_partial_sell = True
            sell_percentage = strategy['tp_sell_percentage']
            # Calculate exact quantity to sell for partial TP
            sell_quantity = current_quantity * (sell_percentage / 100.0)
            logger.info(f"Partial take profit: selling {sell_percentage}% of position ({sell_quantity} of {current_quantity})")
        else:
            # For all other sells (stop loss, trailing stop, etc.), sell the exact strategy quantity
            sell_quantity = current_quantity
            logger.info(f"Full sell: selling entire strategy position ({sell_quantity} of {current_quantity})")
            
        logger.info(f"Executing sell for {symbol} ({strategy_id}) - Reason: {reason} - Quantity: {sell_quantity}")
        
        try:
            # Execute market sell order - pass calculated quantity for partial sells
            sell_order = await self.order_executor.execute_market_sell(symbol, sell_quantity)
            
            if sell_order and sell_order.get('orderId'):
                order_id = sell_order['orderId']
                
                # Register callback to handle sell order completion
                def create_sell_callback(strategy_id, reason, is_partial):
                    async def sell_callback(symbol, executed_qty, avg_price, total_value):
                        try:
                            logger.info(f"Sell callback triggered for {symbol}: {executed_qty} at {avg_price}, total: {total_value}")
                            await self._handle_sell_completion(strategy_id, reason, is_partial, executed_qty, avg_price, total_value)
                        except Exception as e:
                            logger.error(f"Error in sell callback for {strategy_id}: {e}")
                    return sell_callback
                
                # Register the callback
                self.order_executor.register_order_callback(order_id, create_sell_callback(strategy_id, reason, is_partial_sell))
                logger.info(f"Registered sell callback for order {order_id}, strategy {strategy_id}")
                
                # Return immediately - actual processing will happen in callback
                return True
            else:
                logger.error(f"Failed to execute sell for {symbol}")
                
                # Still notify with failure information so UI can be updated
                for callback in self.sell_callbacks:
                    try:
                        # We still want to notify even if the order failed
                        # Use buy_price as sell_price to indicate no profit/loss
                        await callback(symbol, buy_price, buy_price, strategy['quantity'], f"{reason}_FAILED")
                    except Exception as e:
                        logger.error(f"Error executing sell callback for failed order: {e}")
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute sell for {symbol}: {e}")
            return False

    async def _handle_sell_completion(self, strategy_id, reason, is_partial_sell, executed_qty, avg_price, total_value):
        """
        Handle the completion of a sell order with actual execution details.
        
        Args:
            strategy_id: Strategy ID
            reason: Sell reason 
            is_partial_sell: Whether this was a partial sell
            executed_qty: Actual executed quantity
            avg_price: Actual average execution price
            total_value: Total value of the sell
        """
        if strategy_id not in self.active_strategies:
            logger.error(f"Strategy {strategy_id} not found for sell completion")
            return
            
        strategy = self.active_strategies[strategy_id]
        symbol = strategy['symbol']
        buy_price = strategy['buy_price']
        
        logger.info(f"Processing sell completion for {symbol} ({strategy_id}): {executed_qty} at {avg_price:.8f}")
        
        # Update strategy with actual sell details
        strategy['sell_price'] = avg_price
        strategy['sell_quantity'] = executed_qty
        strategy['sell_value'] = total_value
        strategy['sell_reason'] = reason
        strategy['sell_time'] = datetime.now()
        
        # Calculate profit/loss
        profit_percentage = ((avg_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
        
        if is_partial_sell:
            strategy['tp_executed'] = True
            
            # For partial sells, update remaining quantity
            if strategy['quantity'] > executed_qty:
                strategy['quantity'] -= executed_qty
                strategy['status'] = 'PARTIAL_EXECUTED'
                logger.info(f"Partial sell completed. Remaining position: {strategy['quantity']}")
            else:
                # If we sold everything, mark as fully executed
                strategy['status'] = 'EXECUTED'
                strategy['executed'] = True
                
            # Get percentage sold
            original_qty = strategy.get('original_quantity', strategy['quantity'] + executed_qty)
            sold_pct = (executed_qty / original_qty) * 100 if original_qty > 0 else 0
            
            logger.success(f"Partial sell: {executed_qty} of {symbol.replace('USDT', '')} ({sold_pct:.1f}%) at {avg_price:.8f} " +
                          f"USDT ({profit_percentage:.2f}% {'profit' if profit_percentage >= 0 else 'loss'})")
        else:
            # For full sells
            strategy['status'] = 'EXECUTED'
            strategy['executed'] = True
            
            logger.success(f"Sold {executed_qty} {symbol.replace('USDT', '')} at {avg_price:.8f} " +
                          f"USDT ({profit_percentage:.2f}% {'profit' if profit_percentage >= 0 else 'loss'})")
        
        # Update the strategy in memory and database
        self.active_strategies[strategy_id] = strategy
        
        # Save strategy update to database
        asyncio.create_task(self._save_strategy_to_db(strategy_id))
        
        # Execute registered callbacks with actual data
        for callback in self.sell_callbacks:
            try:
                if is_partial_sell:
                    await callback(symbol, buy_price, avg_price, executed_qty, f"{reason} ({executed_qty} sold)")
                else:
                    await callback(symbol, buy_price, avg_price, executed_qty, reason)
            except Exception as e:
                logger.error(f"Error executing sell callback: {e}")
        
        # If fully executed, clean up
        if strategy['executed']:
            logger.info(f"Strategy {strategy_id} fully executed, removing from active strategies")
            
            # Cancel monitoring task for this strategy
            if strategy_id in self.monitoring_tasks:
                self.monitoring_tasks[strategy_id].cancel()
                del self.monitoring_tasks[strategy_id]
            
            # Remove from active strategies (but keep in database for history)
            if strategy_id in self.active_strategies:
                del self.active_strategies[strategy_id]
