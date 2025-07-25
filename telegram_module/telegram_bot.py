import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from loguru import logger
from utils.config import Config
from utils.config_manager import ConfigManager
from api.mexc_api import MexcAPI
from core.sniper_engine import SniperEngine
from core.order_executor import OrderExecutor
from core.sell_strategy_manager import SellStrategyManager

# Constants for common messages
UNAUTHORIZED_MESSAGE = "⚠️ You are not authorized to use this bot."
INVALID_NUMBER_MESSAGE = "⚠️ Amount must be a number."

class TelegramBot:
    """
    Telegram Bot integration for controlling the trading bot and receiving notifications.
    
    This module provides:
    - Command handlers for controlling the bot
    - Real-time notifications for trade events
    - Status reporting
    """
    
    def __init__(self, mexc_api: MexcAPI, sniper_engine: SniperEngine, 
                 order_executor: OrderExecutor, sell_strategy_manager: SellStrategyManager):
        """Initialize the Telegram Bot with bot components."""
        # Get configuration from Config
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        
        # Check if token is configured
        if not self.token:
            logger.warning("Telegram bot token not configured. Bot will be disabled.")
            
        # Store component references
        self.mexc_api = mexc_api
        self.sniper_engine = sniper_engine
        self.order_executor = order_executor
        self.sell_strategy_manager = sell_strategy_manager
        
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Register callback with sell strategy manager for profit notifications
        if sell_strategy_manager:
            sell_strategy_manager.register_sell_callback(self.send_profit_notification)
        
        # Initialize bot properties
        self.application = None
        self.bot = None
        self._polling_task = None
        
        # Parse authorized users
        self.authorized_users = self.chat_id.split(',') if self.chat_id else []
        if not self.authorized_users:
            logger.warning("No authorized Telegram users configured. Nobody will be able to control the bot.")
        else:
            logger.info(f"Authorized Telegram users: {self.authorized_users}")
    
    async def setup(self):
        """Set up the Telegram bot and handlers."""
        if not self.token:
            logger.error("Telegram bot token not configured. Notifications will not work.")
            return False
            
        try:
            # Initialize the application using the builder pattern in v20
            # In v20, builder() returns a builder object that can be chained
            builder = Application.builder()
            builder = builder.token(self.token)
            self.application = builder.build()
            
            # Verify that application was created successfully
            if self.application is None:
                logger.error("Failed to build Telegram application")
                return False
                
            # Set the bot instance for convenience
            self.bot = self.application.bot
            
            if self.bot is None:
                logger.error("Failed to get bot instance from application")
                return False
                
            # Register command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("snipe", self.cmd_snipe))
            self.application.add_handler(CommandHandler("buy", self.cmd_buy))
            self.application.add_handler(CommandHandler("sell", self.cmd_sell))
            self.application.add_handler(CommandHandler("cancel", self.cmd_cancel))
            self.application.add_handler(CommandHandler("balance", self.cmd_balance))
            self.application.add_handler(CommandHandler("price", self.cmd_price))
            self.application.add_handler(CommandHandler("cek", self.cmd_price)) # Alias for price
            self.application.add_handler(CommandHandler("config", self.cmd_config))
            self.application.add_handler(CommandHandler("strategies", self.cmd_strategies))  # New command to view strategies
            
            # Handle unknown commands
            self.application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))
            
            logger.info("Telegram bot has been set up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up Telegram bot: {e}")
            self.application = None
            self.bot = None
            return False
    
    async def start(self):
        """Start the Telegram bot."""
        # If token is not configured, don't even try to start
        if not self.token:
            logger.warning("Not starting Telegram bot - token not configured")
            return False
            
        # If application isn't set up yet, try to set it up
        if not self.application:
            setup_success = await self.setup()
            if not setup_success:
                logger.error("Failed to set up Telegram bot. Cannot start.")
                return False
        
        # Double check that application is not None after setup
        if self.application is None:
            logger.error("Application is None after setup. Cannot start Telegram bot.")
            return False
            
        try:
            logger.info("Starting Telegram bot...")
            
            # For python-telegram-bot v20+, we have two options:
            # 1. Use run_polling (preferred) if we can run blocking
            # 2. Or create a background task that manages polling
            
            # We'll use option 2 since we need non-blocking behavior
            self._polling_task = asyncio.create_task(self._run_application())
            
            logger.info("Telegram bot started successfully")
            
            # Send startup notification
            await self.send_message("🤖 Sniper Bot has been started and is ready!")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
            return False
    
    async def _run_application(self):
        """Runs the application in a non-blocking way."""
        try:
            # Check if the application is initialized before trying to start it
            if self.application is None:
                logger.error("Cannot start application - application is None")
                return
                
            # We simply call the application to start running here
            # This is non-blocking and will keep running in background
            logger.debug("Starting Telegram application")
            
            # In v20+, we use run_polling but need to handle missing updater
            try:
                await self.application.initialize()
                await self.application.start()
            except AttributeError as ae:
                logger.error(f"Error in application initialization: {ae}")
                logger.error("Make sure you're using python-telegram-bot v20+")
                return
                
            # Check if updater exists before trying to access it
            if hasattr(self.application, 'updater') and self.application.updater is not None:
                logger.debug("Starting Telegram polling with updater")
                try:
                    await self.application.updater.start_polling()
                except Exception as e:
                    logger.error(f"Error starting polling: {e}")
            else:
                logger.warning("Application has no updater, using alternative method")
                # Alternative way to start polling in newer versions
                try:
                    # Try to use the update queue if available
                    if hasattr(self.application, 'update_queue'):
                        # Import locally to avoid problems at module level
                        from telegram import Update
                        await self.application.update_queue.put(Update(update_id=0))
                    else:
                        logger.warning("No update queue available in application")
                except Exception as e:
                    logger.error(f"Error using alternative polling method: {e}")
                    logger.error("Bot may not receive updates")
            
            logger.debug("Telegram application started successfully")
            
        except AttributeError as ae:
            logger.error(f"AttributeError in application polling: {ae}")
            logger.error("This could be due to incorrect python-telegram-bot version")
        except Exception as e:
            logger.error(f"Error running application: {e}")
    
    async def stop(self):
        """Stop the Telegram bot."""
        # If application was never initialized, nothing to stop
        if not self.application:
            logger.debug("Telegram bot was never initialized, nothing to stop")
            return
        
        try:
            # Attempt to send shutdown notification if bot is working
            if self.bot:
                try:
                    await self.send_message("🤖 Sniper Bot is shutting down...")
                except Exception as msg_error:
                    logger.debug(f"Could not send shutdown notification: {msg_error}")
            
            # Stop the polling task first
            if self._polling_task and not self._polling_task.done():
                logger.debug("Canceling Telegram polling task")
                self._polling_task.cancel()
                try:
                    await asyncio.wait_for(self._polling_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    # This is expected
                    pass
                except Exception as task_error:
                    logger.error(f"Error canceling polling task: {task_error}")
            
            # Stop the application
            if self.application:
                try:
                    logger.debug("Stopping Telegram application")
                    
                    # First try to stop the updater properly if it exists
                    if hasattr(self.application, 'updater') and self.application.updater is not None:
                        try:
                            logger.debug("Stopping updater first")
                            await self.application.updater.stop()
                        except Exception as updater_error:
                            logger.warning(f"Error stopping updater: {updater_error}")
                    
                    # Then stop the application
                    await self.application.stop()
                    
                    # Finally shutdown
                    try:
                        await self.application.shutdown()
                    except Exception as shutdown_error:
                        logger.warning(f"Error during application shutdown: {shutdown_error}")
                        
                except Exception as app_error:
                    logger.error(f"Error stopping application: {app_error}")
            
            # Clean up references
            self.bot = None
            self._polling_task = None
            
            logger.info("Telegram bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
    
    async def send_message(self, message, parse_mode="Markdown"):
        """
        Send a message to the configured chat ID.
        
        Args:
            message: Message text to send
            parse_mode: The parsing mode, defaults to "Markdown". Set to None for plain text.
        
        Args:
            message: Message text to send
        """
        # Check if bot is initialized and chat IDs are configured
        if not self.bot:
            logger.debug(f"Message not sent (bot not initialized): {message}")
            return
            
        if not self.authorized_users:
            logger.debug(f"Message not sent (no chat IDs configured): {message}")
            return
        
        try:
            # Send to all configured chat IDs
            for chat_id in self.authorized_users:
                try:
                    # Use a longer timeout for the message sending operation
                    # Create a task with a timeout
                    async def send_with_timeout():
                        try:
                            # First make sure bot is not None
                            if self.bot is None:
                                logger.error("Cannot send message - bot is None")
                                return None
                                
                            # Add a longer timeout for messages in case of network issues
                            return await asyncio.wait_for(
                                self.bot.send_message(
                                    chat_id=chat_id, 
                                    text=message, 
                                    parse_mode=parse_mode
                                ),
                                timeout=10.0  # 10 second timeout
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"Telegram message send operation timed out for chat ID {chat_id}")
                            return None

                    # Execute the send operation with timeout
                    result = await send_with_timeout()
                    if result:
                        logger.debug(f"Successfully sent message to chat ID {chat_id}")
                        
                except Exception as chat_error:
                    logger.error(f"Error sending message to chat ID {chat_id}: {chat_error}")
            
            logger.debug(f"Sent message to Telegram: {message}")
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
    
    async def send_trade_notification(self, trade_type, symbol, quantity, price):
        """
        Send a notification about a trade.
        
        Args:
            trade_type: Type of trade (BUY/SELL)
            symbol: Trading pair symbol
            quantity: Quantity traded
            price: Price at which the trade was executed
        """
        emoji = "🟢" if trade_type == "BUY" else "🔴"
        
        # Format numbers first to avoid issues with formatting special characters
        qty_formatted = f"{quantity:.8f}"
        price_formatted = f"{price:.8f}"
        total_formatted = f"{price * quantity:.2f}"
        
        # Escape any special characters in symbol to avoid Markdown parsing issues
        clean_symbol = symbol.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        
        message = (
            f"{emoji} *{trade_type}*: {clean_symbol}\n"
            f"Quantity: `{qty_formatted}`\n"
            f"Price: `{price_formatted}`\n"
            f"Total: `{total_formatted} USDT`"
        )
        
        try:
            await self.send_message(message)
            logger.info(f"Trade notification sent for {symbol}")
        except Exception as e:
            # Fallback to plain text if markdown formatting fails
            logger.error(f"Failed to send formatted notification: {e}")
            plain_message = (
                f"{emoji} {trade_type}: {symbol}\n"
                f"Quantity: {qty_formatted}\n"
                f"Price: {price_formatted}\n"
                f"Total: {total_formatted} USDT"
            )
            await self.send_message(plain_message, parse_mode="")
    
    async def send_profit_notification(self, symbol, buy_price, sell_price, quantity, reason):
        """
        Send a notification about profit/loss.
        
        Args:
            symbol: Trading pair symbol
            buy_price: Price at which the asset was bought
            sell_price: Price at which the asset was sold
            quantity: Quantity traded
            reason: Reason for selling
        """
        # Check if this is a failed order notification
        is_failed = "_FAILED" in reason
        
        # Calculate profit only for successful orders
        if is_failed:
            profit = 0
            profit_percentage = 0
            emoji = "⚠️"
            title = "*ORDER FAILED*"
        else:
            profit = (sell_price - buy_price) * quantity
            profit_percentage = ((sell_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
            emoji = "💰" if profit >= 0 else "📉"
            title = "*PROFIT REPORT*"
        
        # Format numbers to avoid issues with markdown
        buy_price_fmt = f"{buy_price:.8f}"
        sell_price_fmt = f"{sell_price:.8f}"
        quantity_fmt = f"{quantity:.8f}"
        profit_fmt = f"{profit:.2f}"
        profit_pct_fmt = f"{profit_percentage:.2f}"
        
        # Clean symbol and reason to avoid markdown parsing issues
        clean_symbol = symbol.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        clean_reason = str(reason).replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        
        # Create appropriate message based on success or failure
        if is_failed:
            message = (
                f"{emoji} {title}: {clean_symbol}\n"
                f"Buy Price: `{buy_price_fmt}`\n"
                f"Order Type: `{clean_reason.replace('_FAILED', '')}`\n"
                f"Quantity: `{quantity_fmt}`\n"
                f"Status: `Failed to execute`\n"
                f"Reason: Order execution failed - please check account balance and try again manually"
            )
        else:
            message = (
                f"{emoji} {title}: {clean_symbol}\n"
                f"Buy Price: `{buy_price_fmt}`\n"
                f"Sell Price: `{sell_price_fmt}`\n"
                f"Quantity: `{quantity_fmt}`\n"
                f"P/L: `{profit_fmt} USDT ({profit_pct_fmt}%)`\n"
                f"Reason: {clean_reason}"
            )
        
        try:
            await self.send_message(message)
            logger.info(f"{'Failed order' if is_failed else 'Profit'} notification sent for {symbol}")
        except Exception as e:
            # Fallback to plain text if markdown formatting fails
            logger.error(f"Failed to send formatted notification: {e}")
            
            if is_failed:
                plain_message = (
                    f"{emoji} ORDER FAILED: {symbol}\n"
                    f"Buy Price: {buy_price_fmt}\n"
                    f"Order Type: {reason.replace('_FAILED', '')}\n"
                    f"Quantity: {quantity_fmt}\n"
                    f"Status: Failed to execute\n"
                    f"Reason: Order execution failed - please check account balance"
                )
            else:
                plain_message = (
                    f"{emoji} PROFIT REPORT: {symbol}\n"
                    f"Buy Price: {buy_price_fmt}\n"
                    f"Sell Price: {sell_price_fmt}\n"
                    f"Quantity: {quantity_fmt}\n"
                    f"P/L: {profit_fmt} USDT ({profit_pct_fmt}%)\n"
                    f"Reason: {reason}"
                )
                
            await self.send_message(plain_message, parse_mode="")
    
    # Command Handlers
    
    async def cmd_start(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name
        
        logger.info(f"Received /start command from user {user_name} (ID: {user_id})")
        logger.info(f"Authorized users list: {self.authorized_users}")
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            logger.warning(f"Unauthorized access attempt from user {user_name} (ID: {user_id})")
            return
        
        await update.message.reply_text(
            "🤖 *Welcome to the Sniper Bot!*\n\n"
            "I'm here to help you snipe newly listed tokens on MEXC.\n"
            "Use /help to see available commands.",
            parse_mode="Markdown"
        )
    
    async def cmd_help(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /help command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        help_text = (
            "🤖 *Sniper Bot Commands*\n\n"
            "🔹 */start* - Start the bot\n"
            "🔹 */help* - Show this help message\n"
            "🔹 */status* - Show bot status\n"
            "🔹 */balance* - Show wallet balance\n"
            "🔹 */price <pair1> [pair2] [pair3]...* - Check current prices with 24h change (up to 5 pairs)\n"
            "🔹 */cek <pair1> [pair2] [pair3]...* - Show detailed orderbook with 24h change (up to 3 pairs)\n"
            "🔹 */snipe <pair> <amount>* - Add a token to snipe\n"
            "🔹 */buy <pair> <amount> [price]* - Buy a token (market or limit)\n"
            "🔹 */sell <pair> <amount>* - Sell a token immediately\n"
            "🔹 */cancel <pair>* - Cancel sniping for a token\n"
            "🔹 */config* - View and modify bot configuration\n"
            "🔹 */strategies* - View all active sell strategies\n\n"
            "📊 *Price Commands*\n"
            "- *Simple prices:* `/price BTC ETH SOL` - Shows price list with 24h change %\n"
            "- *Detailed orderbook:* `/cek PUMP AIX MBG` - Shows detailed orderbook with current price and 24h change\n\n"
            "💰 *Buy Commands*\n"
            "- *Market buy:* `/buy BTCUSDT 100` - Buy immediately at current market price\n"
            "- *Short format:* `/buy BTC 100` - Same as above (auto-adds USDT)\n"
            "- *Limit buy:* `/buy BTCUSDT 100 50000` - Place limit order at specified price\n"
            "- *Short limit:* `/buy PULSE 10 0.09` - Limit buy PULSE at 0.09 USDT\n\n"
            "� *Strategy Management*\n"
            "- */strategies* - View all active sell strategies with details\n"
            "- Shows individual strategies for multiple buy orders of same symbol\n\n"
            "�📈 *Price Change Indicators*\n"
            "- 🟢 Green with + = Price increased in 24h\n"
            "- 🔴 Red with - = Price decreased in 24h\n"
            "- ⚪ White = No change (0.00%) or data unavailable\n\n"
            "📊 *Advanced Sell Strategy*\n"
            "- *Take Profit (TP):* Set percentage gain target with `/config set PROFIT_TARGET_PERCENTAGE 50`\n"
            "- *Partial TP:* Set percentage of position to sell at TP with `/config set TP_SELL_PERCENTAGE 50`\n"
            "- *Trailing Stop (TSL):* Set percentage from highest price with `/config set TRAILING_STOP_PERCENTAGE 10`\n"
            "- *TSL Activation:* Set minimum price increase to activate TSL with `/config set TSL_MIN_ACTIVATION_PERCENTAGE 20`\n\n"
            "Examples:\n"
            "- `/snipe BTCUSDT 100`\n"
            "- `/buy BTCUSDT 100` (market buy)\n"
            "- `/buy BTC 100` (market buy - short format)\n"
            "- `/buy BTCUSDT 100 50000` (limit buy at 50000 USDT per BTC)\n"
            "- `/buy PULSE 10 0.09` (limit buy PULSE at 0.09 USDT)\n"
            "- `/price BTC ETH SOL` (simple price list with 24h change)\n"
            "- `/cek PUMP AIX MBG` (detailed orderbook with current price and 24h change)\n"
            "- `/strategies` (view all active sell strategies)\n"
            "- `/config list` - List all current configuration values\n"
            "- `/config set PROFIT_TARGET_PERCENTAGE 50` - Set take profit to 50%\n"
            "- `/config set TP_SELL_PERCENTAGE 50` - Sell 50% of position at take profit\n"
        )
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def cmd_status(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /status command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        # Get active snipes
        active_snipes = len(self.sniper_engine.target_pairs)
        active_strategies = len(self.sell_strategy_manager.active_strategies)
        
        status_text = (
            "🤖 *Bot Status*\n\n"
            f"🔹 Active Snipes: {active_snipes}\n"
            f"🔹 Active Sell Strategies: {active_strategies}\n"
            f"🔹 Bot Running: {'Yes' if self.sniper_engine.running else 'No'}"
        )
        
        await update.message.reply_text(status_text, parse_mode="Markdown")
    
    async def cmd_snipe(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /snipe command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("⚠️ Usage: /snipe <pair> <amount>\nExample: `/snipe PULSE 100` or `/snipe PULSEUSDT 100`")
            return
        
        pair = context.args[0].upper()
        
        # Auto-append USDT if not already present (support /snipe pulse 100 format)
        if not pair.endswith('USDT'):
            pair = pair + 'USDT'
            
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Amount must be a number.")
            return
        
        await update.message.reply_text(f"🔍 Setting up sniper for {pair} with {amount} USDT...")
        
        # Add pair to sniper targets
        self.sniper_engine.add_target_pair(pair, amount)
        
        if not self.sniper_engine.running:
            # Start the sniper engine if not running
            await self.sniper_engine.start()
            await update.message.reply_text(f"🚀 Sniper started for {pair}!")
        else:
            await update.message.reply_text(f"✅ Added {pair} to active sniper targets.")
    
    async def cmd_buy(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /buy command with support for both market and limit orders."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "⚠️ Usage:\n"
                "• `/buy <pair> <amount>` - Market buy\n"
                "• `/buy <pair> <amount> <price>` - Limit buy\n\n"
                "Examples:\n"
                "• `/buy BTCUSDT 100` - Market buy 100 USDT worth\n"
                "• `/buy BTC 100` - Same as above (auto-adds USDT)\n"
                "• `/buy PULSE 10` - Market buy 10 USDT worth of PULSE\n"
                "• `/buy PULSEUSDT 100 50000` - Limit buy 100 USDT worth at 50000 USDT per BTC\n"
                "• `/buy PULSE 10 0.09` - Limit buy 10 USDT worth of PULSE at 0.09 USDT per token"
            )
            return
        
        pair = context.args[0].upper()
        
        # Auto-append USDT if not already present (support /buy pulse 1 format)
        if not pair.endswith('USDT'):
            pair = pair + 'USDT'
            
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Amount must be a number.")
            return
        
        # Check if this is a limit order (3rd argument provided)
        if len(context.args) >= 3:
            try:
                price = float(context.args[2])
                await self._execute_limit_buy(update, pair, amount, price)
            except ValueError:
                await update.message.reply_text("⚠️ Price must be a number.")
                return
        else:
            await self._execute_market_buy(update, pair, amount)
    
    async def _execute_market_buy(self, update, pair, amount):
        """Execute a market buy order."""
        await update.message.reply_text(f"🔄 Executing market buy for {pair} with {amount} USDT...")
        
        # Execute market buy
        order = await self.order_executor.execute_market_buy(pair, amount)
        
        if order and order.get('orderId'):
            order_id = str(order.get('orderId'))
            
            # Send initial notification
            await update.message.reply_text("✅ Market buy order placed successfully. Waiting for execution details...")
            
            # Register callback for when we get accurate execution details
            async def order_callback(symbol, executed_qty, avg_price, total_value):
                logger.info(f"Received order callback for {symbol}: {executed_qty} @ {avg_price}, total: {total_value}")
                try:
                    # Format numbers to prevent Markdown parsing issues
                    qty_formatted = f"{executed_qty:.8f}"
                    price_formatted = f"{avg_price:.8f}"
                    total_formatted = f"{total_value:.2f}"
                    
                    # Escape symbol for markdown
                    clean_symbol = symbol.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
                    
                    # Send message using our own send_message method
                    await self.send_message(
                        f"✅ Successfully bought {qty_formatted} {clean_symbol} at {price_formatted} USDT, total: {total_formatted} USDT."
                    )
                    logger.info("Order execution message sent to Telegram successfully")
                    
                    # Send detailed trade notification with accurate price
                    await self.send_trade_notification("BUY", symbol, executed_qty, avg_price)
                    logger.info("Trade notification sent successfully")
                except Exception as e:
                    logger.error(f"Error in Telegram notification callback: {str(e)}", exc_info=True)
            
            # Register our callback to be called when order is filled with accurate price info
            try:
                logger.info(f"Before registration - Current callbacks: {list(self.order_executor.order_callbacks.keys() if hasattr(self.order_executor, 'order_callbacks') else [])}")
                self.order_executor.register_order_callback(order_id, order_callback)
                logger.info(f"Callback registered for order {order_id}")
                logger.info(f"After registration - Current callbacks: {list(self.order_executor.order_callbacks.keys() if hasattr(self.order_executor, 'order_callbacks') else [])}")
            except Exception as e:
                logger.error(f"Error registering callback for order {order_id}: {str(e)}", exc_info=True)
        else:
            await update.message.reply_text(f"❌ Failed to place market buy order for {pair}. Check logs for details.")
    
    async def _execute_limit_buy(self, update, pair, amount, price):
        """Execute a limit buy order."""
        try:
            await update.message.reply_text(
                f"🔄 Placing limit buy order for {pair}:\n"
                f"• Amount: {amount} USDT\n"
                f"• Price: {price} USDT per unit\n"
                f"• Estimated quantity: {amount/price:.8f} {pair.replace('USDT', '')}"
            )
        except Exception as e:
            logger.error(f"Error sending initial limit buy message: {e}")
            # Continue with order execution even if message fails
        
        # Execute limit buy
        order = await self.order_executor.execute_limit_buy(pair, amount, price)
        
        if order and order.get('orderId'):
            order_id = str(order.get('orderId'))
            status = order.get('status', 'UNKNOWN')
            orig_qty = order.get('origQty', '0')
            
            # Send confirmation notification
            clean_symbol = pair.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
            try:
                await update.message.reply_text(
                    f"✅ Limit buy order placed successfully!\n"
                    f"• Pair: {clean_symbol}\n"
                    f"• Order ID: `{order_id}`\n"
                    f"• Quantity: `{orig_qty}`\n"
                    f"• Price: `{price} USDT`\n"
                    f"• Status: `{status}`\n\n"
                    f"💡 The order will be executed when the market price reaches your limit price.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error sending limit buy confirmation: {e}")
                # Log the order details even if message fails
                logger.info(f"Limit buy order placed: {pair} - Order ID: {order_id} - Quantity: {orig_qty} - Price: {price}")
            
            # Register callback for order updates
            async def limit_order_callback(symbol, executed_qty, avg_price, total_value):
                logger.info(f"Limit order callback for {symbol}: {executed_qty} @ {avg_price}, total: {total_value}")
                try:
                    # Format numbers
                    qty_formatted = f"{executed_qty:.8f}"
                    price_formatted = f"{avg_price:.8f}"
                    total_formatted = f"{total_value:.2f}"
                    
                    # Escape symbol for markdown
                    clean_symbol = symbol.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
                    
                    # Send execution notification
                    await self.send_message(
                        f"🎯 Limit buy order executed!\n"
                        f"• {clean_symbol}: {qty_formatted} units\n"
                        f"• Execution price: {price_formatted} USDT\n"
                        f"• Total: {total_formatted} USDT"
                    )
                    
                    # Send detailed trade notification
                    await self.send_trade_notification("BUY", symbol, executed_qty, avg_price)
                except Exception as e:
                    logger.error(f"Error in limit order callback: {str(e)}", exc_info=True)
            
            # Register callback
            try:
                self.order_executor.register_order_callback(order_id, limit_order_callback)
            except Exception as e:
                logger.error(f"Error registering callback for order {order_id}: {str(e)}", exc_info=True)
        else:
            # Log the failure details
            logger.error(f"Failed to place limit buy order for {pair}: {amount} USDT at {price}")
            try:
                await update.message.reply_text(f"❌ Failed to place limit buy order for {pair}. Check logs for details.")
            except Exception as e:
                logger.error(f"Error sending failure message: {e}")
                logger.error(f"Original order failure: {pair} - {amount} USDT at {price}")
    
    async def cmd_sell(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /sell command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("⚠️ Usage: /sell <pair> <amount>\nExample: `/sell PULSE 100` or `/sell PULSEUSDT 100`")
            return
        
        pair = context.args[0].upper()
        
        # Auto-append USDT if not already present (support /sell pulse 100 format)
        if not pair.endswith('USDT'):
            pair = pair + 'USDT'
            
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Amount must be a number.")
            return
        
        await update.message.reply_text(f"🔄 Executing market sell for {pair} with {amount} units...")
        
        # Execute market sell
        order = await self.order_executor.execute_market_sell(pair, amount)
        
        if order and order.get('orderId'):
            order_id = order.get('orderId')
            
            # Send initial notification
            await update.message.reply_text("✅ Sell order placed successfully. Waiting for execution details...")
            
            # Register callback for when we get accurate execution details
            async def order_callback(symbol, executed_qty, avg_price, total_value):
                logger.info(f"Received order callback for {symbol}: {executed_qty} @ {avg_price}, total: {total_value}")
                await update.message.reply_text(
                    f"✅ Successfully sold {executed_qty} {symbol} at {avg_price:.8f} USDT, total: {total_value:.2f} USDT."
                )
                # Send detailed trade notification with accurate price
                await self.send_trade_notification("SELL", symbol, executed_qty, avg_price)
            
            # Register our callback to be called when order is filled with accurate price info
            self.order_executor.register_order_callback(order_id, order_callback)
        else:
            await update.message.reply_text(f"❌ Failed to sell {pair}. Check logs for details.")
    
    async def cmd_cancel(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /cancel command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args:
            await update.message.reply_text("⚠️ Usage: /cancel <pair>\nExample: `/cancel PULSE` or `/cancel PULSEUSDT`")
            return
        
        pair = context.args[0].upper()
        
        # Auto-append USDT if not already present (support /cancel pulse format)
        if not pair.endswith('USDT'):
            pair = pair + 'USDT'
        
        # Remove from sniper targets
        if self.sniper_engine.remove_target_pair(pair):
            await update.message.reply_text(f"✅ Canceled sniping for {pair}.")
        else:
            await update.message.reply_text(f"❌ {pair} is not an active sniper target.")
    
    async def cmd_balance(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /balance command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        await update.message.reply_text("🔄 Fetching account balance...")
        
        try:
            # Get account information
            account_info = await self.mexc_api.get_account_info()
            
            if not account_info or 'balances' not in account_info:
                await update.message.reply_text("❌ Failed to fetch account balance.")
                return
            
            # Filter non-zero balances
            balances = [b for b in account_info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
            
            if not balances:
                await update.message.reply_text("💰 No assets found in your account.")
                return
            
            # Format message
            balance_text = "💰 *Account Balance*\n\n"
            for balance in balances:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                balance_text += f"🔹 {asset}: {free} (Free) + {locked} (Locked)\n"
            
            await update.message.reply_text(balance_text, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            await update.message.reply_text(f"❌ Error fetching balance: {str(e)}")
    
    def _format_price(self, price):
        """Helper function to format price based on magnitude."""
        if price < 0.00001:
            return f"{price:.8f}"
        elif price < 0.001:
            return f"{price:.6f}"
        elif price < 1:
            return f"{price:.5f}" 
        elif price < 1000:
            return f"{price:.2f}"
        else:
            return f"{price:,.2f}"
    
    def _normalize_trading_pair(self, pair):
        """Helper function to normalize trading pair symbol."""
        pair = pair.upper()
        if not pair.endswith("USDT"):
            pair_with_usdt = f"{pair}USDT"
            pair_note = f"\nNOTE: Using {pair_with_usdt} (assuming USDT trading pair)"
            return pair_with_usdt, pair_note
        return pair, ""
    
    async def _get_orderbook_display(self, pair):
        """Get formatted orderbook display for a trading pair."""
        try:
            # Get 24hr ticker data which includes current price and change percentage
            ticker_24hr = await self.mexc_api.get_24hr_ticker(pair)
            current_price = None
            price_change_percent = None
            
            if ticker_24hr:
                if isinstance(ticker_24hr, list) and ticker_24hr:
                    for item in ticker_24hr:
                        if item.get('symbol') == pair:
                            current_price = float(item['lastPrice'])
                            raw_percent = float(item.get('priceChangePercent', 0))
                            if abs(raw_percent) > 100:
                                price_change_percent = raw_percent
                            else:
                                price_change_percent = raw_percent * 100
                            break
                    if current_price is None and ticker_24hr[0].get('lastPrice'):
                        current_price = float(ticker_24hr[0]['lastPrice'])
                        raw_percent = float(ticker_24hr[0].get('priceChangePercent', 0))
                        if abs(raw_percent) > 100:
                            price_change_percent = raw_percent
                        else:
                            price_change_percent = raw_percent * 100
                elif isinstance(ticker_24hr, dict) and 'lastPrice' in ticker_24hr:
                    current_price = float(ticker_24hr['lastPrice'])
                    raw_percent = float(ticker_24hr.get('priceChangePercent', 0))
                    if abs(raw_percent) > 100:
                        price_change_percent = raw_percent
                    else:
                        price_change_percent = raw_percent * 100
            
            # Get orderbook data from MEXC API
            orderbook = await self.mexc_api.get_order_book(pair, limit=10)
            
            if not orderbook or 'bids' not in orderbook or 'asks' not in orderbook:
                return None, f"❌ No orderbook data for {pair}"
            
            bids = orderbook['bids'][:5]  # Top 5 buy orders
            asks = orderbook['asks'][:5]  # Top 5 sell orders
            
            if not bids or not asks:
                return None, f"❌ Insufficient orderbook data for {pair}"
            
            # Calculate spread
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread = best_ask - best_bid
            spread_percent = (spread / best_ask) * 100
            
            # Format the orderbook display
            symbol_clean = pair.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
            
            message = f"📊 *Order Book: {symbol_clean}*\n"
            
            # Add current price with change percentage if available
            if current_price:
                price_formatted = self._format_price(current_price)
                if price_change_percent is not None:
                    if price_change_percent > 0:
                        change_emoji = "🟢"
                        change_text = f"+{price_change_percent:.2f}%"
                    elif price_change_percent < 0:
                        change_emoji = "🔴"
                        change_text = f"{price_change_percent:.2f}%"
                    else:
                        change_emoji = "⚪"
                        change_text = "0.00%"
                    message += f"💰 *Current Price*: `{price_formatted} USDT` {change_emoji} `{change_text}`\n"
                else:
                    message += f"💰 *Current Price*: `{price_formatted} USDT`\n"
                
                # Add 24hr high/low data if available from ticker_24hr
                if ticker_24hr:
                    high_24h = None
                    low_24h = None
                    
                    if isinstance(ticker_24hr, list) and ticker_24hr:
                        for item in ticker_24hr:
                            if item.get('symbol') == pair:
                                high_24h = float(item.get('highPrice', 0)) if item.get('highPrice') else None
                                low_24h = float(item.get('lowPrice', 0)) if item.get('lowPrice') else None
                                break
                        if high_24h is None and ticker_24hr[0].get('highPrice'):
                            high_24h = float(ticker_24hr[0].get('highPrice', 0))
                            low_24h = float(ticker_24hr[0].get('lowPrice', 0))
                    elif isinstance(ticker_24hr, dict):
                        high_24h = float(ticker_24hr.get('highPrice', 0)) if ticker_24hr.get('highPrice') else None
                        low_24h = float(ticker_24hr.get('lowPrice', 0)) if ticker_24hr.get('lowPrice') else None
                    
                    if high_24h is not None and low_24h is not None:
                        high_formatted = self._format_price(high_24h)
                        low_formatted = self._format_price(low_24h)
                        message += f"📈 *24h High*: `{high_formatted}` | 📉 *24h Low*: `{low_formatted}`\n"
                
                message += "\n"
            else:
                message += "\n"
                
            message += f"💹 *Best Ask*: `{self._format_price(best_ask)}`  |  💰 *Best Bid*: `{self._format_price(best_bid)}`\n"
            message += f"📏 *Spread*: `{self._format_price(spread)}` ({spread_percent:.2f}%)\n\n"
            
            # Sell orders (asks) - display in reverse order for better visualization
            message += "🔴 *SELL ORDERS*\n"
            for i, ask in enumerate(reversed(asks)):
                price = float(ask[0])
                volume = float(ask[1])
                value = price * volume
                
                if i == len(asks) - 1:  # Best ask
                    message += f"➡️ `{self._format_price(price)}` | Vol: `{volume:,.4f}` | `${value:,.2f}`\n"
                else:
                    message += f"   `{self._format_price(price)}` | Vol: `{volume:,.4f}` | `${value:,.2f}`\n"
            
            # Separator
            message += "\n▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️\n\n"
            
            # Buy orders (bids)
            message += "🟢 *BUY ORDERS*\n"
            for i, bid in enumerate(bids):
                price = float(bid[0])
                volume = float(bid[1])
                value = price * volume
                
                if i == 0:  # Best bid
                    message += f"➡️ `{self._format_price(price)}` | Vol: `{volume:,.4f}` | `${value:,.2f}`\n"
                else:
                    message += f"   `{self._format_price(price)}` | Vol: `{volume:,.4f}` | `${value:,.2f}`\n"
            
            return message, None
            
        except Exception as e:
            logger.error(f"Error fetching orderbook for {pair}: {str(e)}")
            return None, f"❌ Error getting orderbook for {pair}: {str(e)[:50]}..."

    async def _get_formatted_price_for_pair(self, pair):
        """Helper function to get and format price for a single trading pair.
        
        Returns:
            Tuple of (formatted_result, error_message)
            If successful, error_message will be None
            If failed, formatted_result will be None
        """
        try:
            # Get 24hr ticker data which includes price change percentage
            ticker_24hr = await self.mexc_api.get_24hr_ticker(pair)
            
            if not ticker_24hr:
                return None, f"❌ No data for {pair} - please check if this is a valid trading pair"
                
            # Extract data from 24hr ticker response
            price = None
            price_change_percent = None
            
            if isinstance(ticker_24hr, list) and ticker_24hr:
                # Find the matching pair in the list
                for item in ticker_24hr:
                    if item.get('symbol') == pair:
                        price = float(item['lastPrice'])
                        # Convert price change percent to proper percentage format
                        raw_percent = float(item.get('priceChangePercent', 0))
                        # MEXC returns percentage in decimal format (e.g., 0.0142 for 1.42%)
                        # We need to check if it's already in percentage format or decimal format
                        if abs(raw_percent) > 100:  # Likely already in percentage format
                            price_change_percent = raw_percent
                        else:  # Likely in decimal format, need to multiply by 100
                            price_change_percent = raw_percent * 100
                        break
                # If we couldn't find our pair in the list, use the first one as fallback
                if price is None and ticker_24hr[0].get('lastPrice'):
                    price = float(ticker_24hr[0]['lastPrice'])
                    raw_percent = float(ticker_24hr[0].get('priceChangePercent', 0))
                    if abs(raw_percent) > 100:
                        price_change_percent = raw_percent
                    else:
                        price_change_percent = raw_percent * 100
            elif isinstance(ticker_24hr, dict) and 'lastPrice' in ticker_24hr:
                price = float(ticker_24hr['lastPrice'])
                raw_percent = float(ticker_24hr.get('priceChangePercent', 0))
                if abs(raw_percent) > 100:
                    price_change_percent = raw_percent
                else:
                    price_change_percent = raw_percent * 100
                
            if price is None:
                return None, f"❌ Invalid data format received for {pair}"
            
            # Format price
            price_formatted = self._format_price(price)
            
            # Format percentage change with appropriate emoji
            if price_change_percent is not None:
                if price_change_percent > 0:
                    change_emoji = "🟢"
                    change_text = f"+{price_change_percent:.2f}%"
                elif price_change_percent < 0:
                    change_emoji = "🔴"
                    change_text = f"{price_change_percent:.2f}%"
                else:
                    change_emoji = "⚪"
                    change_text = "0.00%"
            else:
                change_emoji = "⚪"
                change_text = "N/A"
            
            # Escape special Markdown characters
            symbol_clean = pair.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
            
            # Get 24hr high/low data if available
            high_low_text = ""
            if isinstance(ticker_24hr, list) and ticker_24hr:
                for item in ticker_24hr:
                    if item.get('symbol') == pair:
                        high_24h = float(item.get('highPrice', 0)) if item.get('highPrice') else None
                        low_24h = float(item.get('lowPrice', 0)) if item.get('lowPrice') else None
                        if high_24h is not None and low_24h is not None:
                            high_formatted = self._format_price(high_24h)
                            low_formatted = self._format_price(low_24h)
                            high_low_text = f"\n   📈 `{high_formatted}` | 📉 `{low_formatted}`"
                        break
                if not high_low_text and ticker_24hr[0].get('highPrice'):
                    high_24h = float(ticker_24hr[0].get('highPrice', 0))
                    low_24h = float(ticker_24hr[0].get('lowPrice', 0))
                    high_formatted = self._format_price(high_24h)
                    low_formatted = self._format_price(low_24h)
                    high_low_text = f"\n   📈 `{high_formatted}` | 📉 `{low_formatted}`"
            elif isinstance(ticker_24hr, dict) and ticker_24hr.get('highPrice'):
                high_24h = float(ticker_24hr.get('highPrice', 0))
                low_24h = float(ticker_24hr.get('lowPrice', 0))
                high_formatted = self._format_price(high_24h)
                low_formatted = self._format_price(low_24h)
                high_low_text = f"\n   📈 `{high_formatted}` | 📉 `{low_formatted}`"
            
            # Return formatted result with price change and high/low
            return f"💹 *{symbol_clean}*: `{price_formatted} USDT` {change_emoji} `{change_text}`{high_low_text}", None
                
        except Exception as e:
            logger.error(f"Error fetching price for {pair}: {str(e)}")
            return None, f"❌ Error with {pair}: {str(e)[:50]}... Please try again later."
    
    async def cmd_price(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /price or /cek command to check current price and orderbook of a trading pair."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("⚠️ Usage: /price <pair1> [pair2] [pair3] ... or /cek <pair>\nExamples:\n- /price BTCUSDT\n- /price BTC ETH SOL")
            return
        
        # Normalize all pairs
        pairs = [self._normalize_trading_pair(arg)[0] for arg in context.args]
        
        # Get the command that was used
        command = update.message.text.split()[0].lower()
        is_cek_command = command == "/cek"
        
        # For /cek command, show detailed orderbook for each pair
        if is_cek_command:
            if len(pairs) > 5:
                await update.message.reply_text("⚠️ Too many pairs requested for detailed view. Please limit to 3 or fewer pairs at once.")
                return
            
            # Show detailed orderbook for each pair
            for pair in pairs:
                await update.message.reply_text(f"🔍 Fetching detailed orderbook for {pair}...")
                
                # Get orderbook display
                orderbook_result, error = await self._get_orderbook_display(pair)
                
                if orderbook_result:
                    await update.message.reply_text(orderbook_result, parse_mode="Markdown")
                else:
                    # Fallback to simple price if orderbook fails
                    price_result, price_error = await self._get_formatted_price_for_pair(pair)
                    if price_result:
                        fallback_msg = f"*Current Price* (orderbook unavailable)\n\n{price_result}"
                        if error:
                            fallback_msg += f"\n\n*Note:* {error}"
                        await update.message.reply_text(fallback_msg, parse_mode="Markdown")
                    else:
                        error_msg = error or price_error or "Unknown error occurred"
                        await update.message.reply_text(f"❌ {error_msg}", parse_mode="Markdown")
        
        # For /price command, show simple price list (multiple pairs)
        else:
            if len(pairs) > 5:
                await update.message.reply_text("⚠️ Too many pairs requested. Please limit to 5 or fewer pairs at once.")
                return
                
            await update.message.reply_text(f"🔍 Fetching current prices for {', '.join(pairs)}...")
            
            # Get prices for all pairs
            results = []
            errors = []
            
            for pair in pairs:
                result, error = await self._get_formatted_price_for_pair(pair)
                if result:
                    results.append(result)
                if error:
                    errors.append(error)
            
            # Prepare response message
            if results:
                message = "*Current Prices*\n\n" + "\n".join(results)
                
                # Add errors at the end if any
                if errors:
                    message += "\n\n*Errors:*\n" + "\n".join(errors)
                    
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Could not fetch prices for any of the requested pairs.", parse_mode="Markdown")
    
    async def unknown_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands."""
        await update.message.reply_text(
            "⚠️ Unknown command. Use /help to see available commands."
        )
        
    async def cmd_config(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /config command to view and modify bot configuration."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        # If no arguments provided, show available parameters
        if not context.args or len(context.args) == 0:
            params_info = self.config_manager.get_configurable_params_info()
            message = "⚙️ *Bot Configuration*\n\n"
            message += "Available commands:\n"
            message += "- `/config list` - List all configurable parameters\n"
            message += "- `/config get <param>` - Get the value of a parameter\n"
            message += "- `/config set <param> <value>` - Set a new value for a parameter\n"
            message += "- `/config reset <param>` - Reset a parameter to default value\n"
            message += "- `/config resetall` - Reset all parameters to default values\n\n"
            message += "Configurable parameters:\n"
            
            for param_name, param_info in params_info.items():
                message += f"- `{param_name}` - {param_info['description']}\n"
                
            await update.message.reply_text(message, parse_mode="Markdown")
            return
        
        # Parse command
        command = context.args[0].lower()
        
        # List all parameters and their values
        if command == "list":
            params = self.config_manager.get_all_parameters()
            params_info = self.config_manager.get_configurable_params_info()
            
            message = "⚙️ *Current Configuration*\n\n"
            
            for param_name, value in params.items():
                param_info = params_info.get(param_name, {})
                description = param_info.get('description', 'No description')
                
                message += f"*{param_name}*\n"
                message += f"Value: `{value}`\n"
                message += f"Description: {description}\n"
                if 'min' in param_info and 'max' in param_info:
                    message += f"Range: `{param_info['min']}` to `{param_info['max']}`\n"
                message += "\n"
                
            await update.message.reply_text(message, parse_mode="Markdown")
            return
            
        # Get a specific parameter value
        elif command == "get":
            if len(context.args) < 2:
                await update.message.reply_text("⚠️ Usage: /config get <parameter_name>")
                return
                
            param_name = context.args[1].upper()
            value = self.config_manager.get_parameter(param_name)
            
            if value is not None:
                param_info = self.config_manager.get_configurable_params_info().get(param_name, {})
                description = param_info.get('description', 'No description')
                
                message = f"⚙️ *{param_name}*\n"
                message += f"Current value: `{value}`\n"
                message += f"Description: {description}\n"
                
                if 'min' in param_info and 'max' in param_info:
                    message += f"Allowed range: `{param_info['min']}` to `{param_info['max']}`"
                
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text(f"⚠️ Parameter '{param_name}' not found or not configurable.")
            
        # Set a parameter value
        elif command == "set":
            if len(context.args) < 3:
                await update.message.reply_text("⚠️ Usage: /config set <parameter_name> <value>")
                return
                
            param_name = context.args[1].upper()
            value = context.args[2]
            
            success, message = self.config_manager.set_parameter(param_name, value)
            
            if success:
                await update.message.reply_text(f"✅ {message}")
            else:
                await update.message.reply_text(f"⚠️ {message}")
                
        # Reset a parameter to default value
        elif command == "reset":
            if len(context.args) < 2:
                await update.message.reply_text("⚠️ Usage: /config reset <parameter_name>")
                return
                
            param_name = context.args[1].upper()
            success, message = self.config_manager.reset_parameter(param_name)
            
            if success:
                await update.message.reply_text(f"✅ {message}")
            else:
                await update.message.reply_text(f"⚠️ {message}")
                
        # Reset all parameters to default values
        elif command == "resetall":
            success, message = self.config_manager.reset_all_parameters()
            
            if success:
                await update.message.reply_text(f"✅ {message}")
            else:
                await update.message.reply_text(f"⚠️ {message}")
                
        else:
            await update.message.reply_text(
                "⚠️ Unknown config command. Use /config without arguments to see usage."
            )
    
    async def cmd_strategies(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /strategies command to show active sell strategies."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not hasattr(self, 'sell_strategy_manager') or not self.sell_strategy_manager:
            await update.message.reply_text("⚠️ Sell strategy manager not available.")
            return
        
        try:
            # Get all active strategies
            active_strategies = {}
            for strategy_id, strategy in self.sell_strategy_manager.active_strategies.items():
                if strategy['status'] == 'ACTIVE' and not strategy['executed']:
                    symbol = strategy['symbol']
                    if symbol not in active_strategies:
                        active_strategies[symbol] = []
                    active_strategies[symbol].append(strategy)
            
            if not active_strategies:
                await update.message.reply_text("📊 No active sell strategies found.")
                return
            
            # Build response message
            response = "📊 **Active Sell Strategies**\n\n"
            
            for symbol, strategies in active_strategies.items():
                response += f"🪙 **{symbol}**\n"
                total_qty = sum(s['quantity'] for s in strategies)
                avg_buy_price = sum(s['buy_price'] * s['quantity'] for s in strategies) / total_qty if total_qty > 0 else 0
                
                response += f"   📈 Total Position: `{total_qty:.8f}` {symbol.replace('USDT', '')}\n"
                response += f"   💰 Avg Buy Price: `{avg_buy_price:.8f}` USDT\n"
                response += f"   📋 Strategies: `{len(strategies)}` active\n\n"
                
                for i, strategy in enumerate(strategies, 1):
                    buy_price = strategy['buy_price']
                    quantity = strategy['quantity']
                    tp_price = strategy['take_profit_price']
                    sl_price = strategy['stop_loss_price']
                    tp_pct = strategy['tp_sell_percentage']
                    tsl_activated = strategy['tsl_activated']
                    tsl_price = strategy.get('trailing_stop_price', 'Not set')
                    
                    response += f"   🔸 **Strategy #{i}**\n"
                    response += f"      • Quantity: `{quantity:.8f}`\n"
                    response += f"      • Buy Price: `{buy_price:.8f}` USDT\n"
                    response += f"      • Take Profit: `{tp_price:.8f}` USDT ({tp_pct}%)\n"
                    response += f"      • Stop Loss: `{sl_price:.8f}` USDT\n"
                    if tsl_activated:
                        response += f"      • TSL Active: `{tsl_price}` USDT ✅\n"
                    else:
                        response += f"      • TSL: Not activated ⏳\n"
                    response += "\n"
                
                response += "─" * 30 + "\n\n"
            
            # Split message if too long
            if len(response) > 4000:
                # Send in chunks
                parts = response.split("─" * 30)
                for part in parts:
                    if part.strip():
                        await update.message.reply_text(part.strip(), parse_mode="Markdown")
            else:
                await update.message.reply_text(response, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Error in strategies command: {e}")
            await update.message.reply_text("❌ Error retrieving strategy information. Check logs for details.")
