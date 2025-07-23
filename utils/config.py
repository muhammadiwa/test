from dotenv import load_dotenv
import os
import json
from loguru import logger
import sys

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/sniper_bot_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# Create logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Load environment variables
load_dotenv()

# Path to custom config file
CUSTOM_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'custom_config.json')

# Load custom config if exists
custom_config = {}
if os.path.exists(CUSTOM_CONFIG_PATH):
    try:
        with open(CUSTOM_CONFIG_PATH, 'r') as f:
            custom_config = json.load(f)
        logger.debug(f"Loaded custom configuration from {CUSTOM_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Failed to load custom configuration: {e}")

class Config:
    """Configuration class for the sniper bot."""
    
    # MEXC API Credentials
    MEXC_API_KEY = os.getenv("MEXC_API_KEY")
    MEXC_API_SECRET = os.getenv("MEXC_API_SECRET")
    
    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Bot Settings - check custom config first, then environment variables
    DEFAULT_USDT_AMOUNT = custom_config.get("DEFAULT_USDT_AMOUNT", float(os.getenv("DEFAULT_USDT_AMOUNT", "100")))
    BUY_FREQUENCY_MS = custom_config.get("BUY_FREQUENCY_MS", int(os.getenv("BUY_FREQUENCY_MS", "10")))
    MAX_RETRY_ATTEMPTS = custom_config.get("MAX_RETRY_ATTEMPTS", int(os.getenv("MAX_RETRY_ATTEMPTS", "5")))
    RETRY_DELAY = custom_config.get("RETRY_DELAY", float(os.getenv("RETRY_DELAY", "0.5")))  # Delay in seconds between retries
    MIN_ORDER_USDT = custom_config.get("MIN_ORDER_USDT", float(os.getenv("MIN_ORDER_USDT", "1.0")))  # Minimum order size in USDT
    PROFIT_TARGET_PERCENTAGE = custom_config.get("PROFIT_TARGET_PERCENTAGE", float(os.getenv("PROFIT_TARGET_PERCENTAGE", "20")))
    TP_SELL_PERCENTAGE = custom_config.get("TP_SELL_PERCENTAGE", float(os.getenv("TP_SELL_PERCENTAGE", "100")))  # Sell 100% at TP by default
    STOP_LOSS_PERCENTAGE = custom_config.get("STOP_LOSS_PERCENTAGE", float(os.getenv("STOP_LOSS_PERCENTAGE", "10")))
    TRAILING_STOP_PERCENTAGE = custom_config.get("TRAILING_STOP_PERCENTAGE", float(os.getenv("TRAILING_STOP_PERCENTAGE", "5")))
    TSL_MIN_ACTIVATION_PERCENTAGE = custom_config.get("TSL_MIN_ACTIVATION_PERCENTAGE", float(os.getenv("TSL_MIN_ACTIVATION_PERCENTAGE", "20")))  # Min 20% price increase to activate TSL
    TIME_BASED_SELL_MINUTES = custom_config.get("TIME_BASED_SELL_MINUTES", int(os.getenv("TIME_BASED_SELL_MINUTES", "30")))
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        if not cls.MEXC_API_KEY or not cls.MEXC_API_SECRET:
            logger.error("MEXC API credentials are not configured. Please set MEXC_API_KEY and MEXC_API_SECRET in .env file.")
            return False
            
        if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID:
            logger.warning("Telegram notifications are not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env file for notifications.")
            
        return True
