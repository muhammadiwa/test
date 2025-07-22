import asyncio
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram import Update
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
        
        # Initialize bot properties
        self.application = None
        self.bot = None
        self._polling_task = None
        
        # Parse authorized users
        self.authorized_users = self.chat_id.split(',') if self.chat_id else []
        if not self.authorized_users:
            logger.warning("No authorized Telegram users configured. Nobody will be able to control the bot.")
    
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
            await self.application.initialize()
            await self.application.start()
            
            # Check if updater exists before trying to access it
            if hasattr(self.application, 'updater') and self.application.updater is not None:
                logger.debug("Starting Telegram polling with updater")
                await self.application.updater.start_polling()
            else:
                logger.warning("Application has no updater, using alternative method")
                # Alternative way to start polling in newer versions
                await self.application.update_queue.put(Update(update_id=0))
            
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
                    await self.application.stop()
                    await self.application.shutdown()
                except Exception as app_error:
                    logger.error(f"Error stopping application: {app_error}")
            
            # Clean up references
            self.bot = None
            self._polling_task = None
            
            logger.info("Telegram bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")
    
    async def send_message(self, message):
        """
        Send a message to the configured chat ID.
        
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
                    await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
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
        message = (
            f"{emoji} *{trade_type}*: {symbol}\n"
            f"Quantity: `{quantity:.8f}`\n"
            f"Price: `{price:.8f}`\n"
            f"Total: `{price * quantity:.2f} USDT`"
        )
        await self.send_message(message)
    
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
        
        emoji = "💰" if profit >= 0 else "📉"
        message = (
            f"{emoji} *PROFIT REPORT*: {symbol}\n"
            f"Buy Price: `{buy_price:.8f}`\n"
            f"Sell Price: `{sell_price:.8f}`\n"
            f"Quantity: `{quantity:.8f}`\n"
            f"P/L: `{profit:.2f} USDT ({profit_percentage:.2f}%)`\n"
            f"Reason: {reason}"
        )
        await self.send_message(message)
    
    # Command Handlers
    
    async def cmd_start(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        user_id = str(update.effective_user.id)
        
        if user_id not in self.authorized_users:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            logger.warning(f"Unauthorized access attempt from user ID: {user_id}")
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
            "🔹 */snipe <pair> <amount>* - Add a token to snipe\n"
            "🔹 */buy <pair> <amount>* - Buy a token immediately\n"
            "🔹 */sell <pair> <amount>* - Sell a token immediately\n"
            "🔹 */cancel <pair>* - Cancel sniping for a token\n\n"
            "Example: `/snipe BTCUSDT 100`"
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
            price = float(order.get('price', 0))
            quantity = float(order.get('executedQty', 0))
            
            # Add sell strategy for the bought token
            self.sell_strategy_manager.add_strategy(pair, price, quantity)
            
            await update.message.reply_text(f"✅ Successfully bought {quantity} {pair} at {price} USDT.")
            
            # Send trade notification
            await self.send_trade_notification("BUY", pair, quantity, price)
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
            price = float(order.get('price', 0))
            quantity = float(order.get('executedQty', 0))
            await update.message.reply_text(f"✅ Successfully sold {quantity} {pair} at {price} USDT.")
            
            # Send trade notification
            await self.send_trade_notification("SELL", pair, quantity, price)
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
    
    async def unknown_command(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands."""
        await update.message.reply_text(
            "⚠️ Unknown command. Use /help to see available commands."
        )
