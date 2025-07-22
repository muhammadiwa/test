import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from loguru import logger
from utils.config import Config
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
        profit = (sell_price - buy_price) * quantity
        profit_percentage = ((sell_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
        
        # Format numbers to avoid issues with markdown
        buy_price_fmt = f"{buy_price:.8f}"
        sell_price_fmt = f"{sell_price:.8f}"
        quantity_fmt = f"{quantity:.8f}"
        profit_fmt = f"{profit:.2f}"
        profit_pct_fmt = f"{profit_percentage:.2f}"
        
        # Clean symbol to avoid markdown parsing issues
        clean_symbol = symbol.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
        
        emoji = "💰" if profit >= 0 else "📉"
        message = (
            f"{emoji} *PROFIT REPORT*: {clean_symbol}\n"
            f"Buy Price: `{buy_price_fmt}`\n"
            f"Sell Price: `{sell_price_fmt}`\n"
            f"Quantity: `{quantity_fmt}`\n"
            f"P/L: `{profit_fmt} USDT ({profit_pct_fmt}%)`\n"
            f"Reason: {reason}"
        )
        
        try:
            await self.send_message(message)
            logger.info(f"Profit notification sent for {symbol}")
        except Exception as e:
            # Fallback to plain text if markdown formatting fails
            logger.error(f"Failed to send formatted profit notification: {e}")
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
            "🔹 */price <pair>* - Check current price of a trading pair\n"
            "🔹 */cek <pair>* - Alias for /price command\n"
            "🔹 */snipe <pair> <amount>* - Add a token to snipe\n"
            "🔹 */buy <pair> <amount>* - Buy a token immediately\n"
            "🔹 */sell <pair> <amount>* - Sell a token immediately\n"
            "🔹 */cancel <pair>* - Cancel sniping for a token\n\n"
            "Examples:\n"
            "- `/snipe BTCUSDT 100`\n"
            "- `/price ETHUSDT`\n"
            "- `/cek BTC` (automatically adds USDT suffix)"
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
            await update.message.reply_text("⚠️ Usage: /snipe <pair> <amount>")
            return
        
        pair = context.args[0].upper()
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
        """Handle the /buy command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("⚠️ Usage: /buy <pair> <amount>")
            return
        
        pair = context.args[0].upper()
        try:
            amount = float(context.args[1])
        except ValueError:
            await update.message.reply_text("⚠️ Amount must be a number.")
            return
        
        await update.message.reply_text(f"🔄 Executing market buy for {pair} with {amount} USDT...")
        
        # Execute market buy
        order = await self.order_executor.execute_market_buy(pair, amount)
        
        if order and order.get('orderId'):
            order_id = order.get('orderId')
            # Ensure we have a string ID to avoid type mismatch
            order_id = str(order_id)
            
            # Send initial notification
            await update.message.reply_text("✅ Buy order placed successfully. Waiting for execution details...")
            
            # Register callback for when we get accurate execution details
            async def order_callback(symbol, executed_qty, avg_price, total_value):
                logger.info(f"Received order callback for {symbol}: {executed_qty} @ {avg_price}, total: {total_value}")
                try:
                    # No need to extract chat_id since we're using our send_message method
                    
                    # Format numbers to prevent Markdown parsing issues
                    qty_formatted = f"{executed_qty:.8f}"
                    price_formatted = f"{avg_price:.8f}"
                    total_formatted = f"{total_value:.2f}"
                    
                    # Escape symbol for markdown
                    clean_symbol = symbol.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
                    
                    # Send message using our own send_message method instead of directly using bot
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
                # Log the current order_callbacks state before registration
                logger.info(f"Before registration - Current callbacks: {list(self.order_executor.order_callbacks.keys() if hasattr(self.order_executor, 'order_callbacks') else [])}")
                self.order_executor.register_order_callback(order_id, order_callback)
                logger.info(f"Callback registered for order {order_id}")
                # Log after registration to confirm
                logger.info(f"After registration - Current callbacks: {list(self.order_executor.order_callbacks.keys() if hasattr(self.order_executor, 'order_callbacks') else [])}")
            except Exception as e:
                logger.error(f"Error registering callback for order {order_id}: {str(e)}", exc_info=True)
        else:
            await update.message.reply_text(f"❌ Failed to buy {pair}. Check logs for details.")
    
    async def cmd_sell(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /sell command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text("⚠️ Usage: /sell <pair> <amount>")
            return
        
        pair = context.args[0].upper()
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
            await update.message.reply_text("⚠️ Usage: /cancel <pair>")
            return
        
        pair = context.args[0].upper()
        
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
    
    async def _get_formatted_price_for_pair(self, pair):
        """Helper function to get and format price for a single trading pair.
        
        Returns:
            Tuple of (formatted_result, error_message)
            If successful, error_message will be None
            If failed, formatted_result will be None
        """
        try:
            # Get ticker price from MEXC API
            ticker = await self.mexc_api.get_ticker_price(pair)
            
            if not ticker:
                return None, f"❌ No data for {pair}"
                
            # Extract price from response
            price = None
            if isinstance(ticker, list) and ticker:
                price = float(ticker[0]['price'])
            elif isinstance(ticker, dict) and 'price' in ticker:
                price = float(ticker['price'])
                
            if price is None:
                return None, f"❌ Invalid data for {pair}"
            
            # Format price
            price_formatted = self._format_price(price)
            symbol_clean = pair.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
            
            # Return formatted result
            return f"💹 *{symbol_clean}*: `{price_formatted} USDT`", None
                
        except Exception as e:
            logger.error(f"Error fetching price for {pair}: {str(e)}")
            return None, f"❌ Error with {pair}: {str(e)[:50]}..."
    
    async def cmd_price(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /price or /cek command to check current price of a trading pair."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text("⚠️ Usage: /price <pair1> [pair2] [pair3] ... or /cek <pair>\nExamples:\n- /price BTCUSDT\n- /price BTC ETH SOL")
            return
        
        # Normalize all pairs
        pairs = [self._normalize_trading_pair(arg)[0] for arg in context.args]
        
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
