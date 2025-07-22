import time
from loguru import logger
from api.mexc_api import MexcAPI
from core.sniper_engine import SniperEngine
from core.order_executor import OrderExecutor
from core.sell_strategy_manager import SellStrategyManager

class DashboardManager:
    """
    Dashboard Manager for logging and displaying bot performance.
    
    This module is responsible for:
    - Logging trade performance
    - Displaying real-time status
    """
    
    def __init__(self, mexc_api: MexcAPI, sniper_engine: SniperEngine, 
                 order_executor: OrderExecutor, sell_strategy_manager: SellStrategyManager):
        """Initialize the Dashboard Manager with bot components."""
        self.mexc_api = mexc_api
        self.sniper_engine = sniper_engine
        self.order_executor = order_executor
        self.sell_strategy_manager = sell_strategy_manager
        self.trades = []  # List to track trades
    
    def log_trade(self, trade_type, symbol, quantity, price, order_id=None):
        """
        Log a trade in the dashboard.
        
        Args:
            trade_type: Type of trade (BUY/SELL)
            symbol: Trading pair symbol
            quantity: Quantity traded
            price: Price at which the trade was executed
            order_id: Optional order ID
        """
        trade = {
            'id': len(self.trades) + 1,
            'timestamp': time.time(),
            'type': trade_type,
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'total': price * quantity,
            'order_id': order_id
        }
        
        self.trades.append(trade)
        logger.info(f"Trade logged: {trade_type} {symbol} {quantity} at {price}")
        
        # Log to console with color
        if trade_type == "BUY":
            logger.info(f"🟢 BUY: {symbol} - {quantity:.8f} at {price:.8f} = {price * quantity:.2f} USDT")
        else:
            logger.info(f"🔴 SELL: {symbol} - {quantity:.8f} at {price:.8f} = {price * quantity:.2f} USDT")
    
    def log_profit(self, buy_trade, sell_trade, reason=None):
        """
        Log profit/loss for a completed trade cycle.
        
        Args:
            buy_trade: Trade data for buy
            sell_trade: Trade data for sell
            reason: Reason for selling
        """
        profit = sell_trade['total'] - buy_trade['total']
        profit_percentage = (profit / buy_trade['total']) * 100 if buy_trade['total'] > 0 else 0
        
        profit_log = {
            'buy_trade_id': buy_trade['id'],
            'sell_trade_id': sell_trade['id'],
            'symbol': buy_trade['symbol'],
            'buy_price': buy_trade['price'],
            'sell_price': sell_trade['price'],
            'quantity': buy_trade['quantity'],
            'profit_usdt': profit,
            'profit_percentage': profit_percentage,
            'reason': reason
        }
        
        logger.info(f"Profit logged: {profit_log['symbol']} - {profit:.2f} USDT ({profit_percentage:.2f}%)")
        
        # Log to console with color
        if profit >= 0:
            logger.success(f"💰 PROFIT: {buy_trade['symbol']} - {profit:.2f} USDT ({profit_percentage:.2f}%)")
        else:
            logger.warning(f"📉 LOSS: {buy_trade['symbol']} - {profit:.2f} USDT ({profit_percentage:.2f}%)")
        
        return profit_log
    
    def get_trade_history(self, limit=None):
        """
        Get trade history.
        
        Args:
            limit: Optional limit on number of trades to return
            
        Returns:
            List of trades
        """
        if limit:
            return self.trades[-limit:]
        return self.trades
    
    def get_active_strategies(self):
        """
        Get active sell strategies.
        
        Returns:
            List of active strategies
        """
        return self.sell_strategy_manager.active_strategies
    
    def get_active_snipes(self):
        """
        Get active sniper targets.
        
        Returns:
            List of active snipe targets
        """
        return self.sniper_engine.target_pairs
    
    def display_status(self):
        """Display the current status of the bot."""
        active_snipes = len(self.sniper_engine.target_pairs)
        active_strategies = len(self.sell_strategy_manager.active_strategies)
        
        logger.info(f"Bot Status: {active_snipes} active snipes, {active_strategies} active sell strategies")
        
        # Display active snipes
        if active_snipes > 0:
            logger.info("Active Snipes:")
            for target in self.sniper_engine.target_pairs:
                logger.info(f"  - {target['pair']}: {target['usdt_amount']} USDT, {target['frequency_ms']}ms frequency")
        
        # Display active sell strategies
        if active_strategies > 0:
            logger.info("Active Sell Strategies:")
            for strategy_id, strategy in self.sell_strategy_manager.active_strategies.items():
                symbol = strategy['symbol']
                buy_price = strategy['buy_price']
                take_profit = strategy['take_profit_price']
                stop_loss = strategy['stop_loss_price']
                
                logger.info(f"  - {symbol}: Buy @ {buy_price:.8f}, TP @ {take_profit:.8f}, SL @ {stop_loss:.8f}")
