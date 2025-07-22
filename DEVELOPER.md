# Sniper Bot - Developer Documentation

## 👨‍💻 **Installation & Setup**

### **Prerequisites**
- Python 3.8 or higher
- MEXC exchange account with API key and secret

### **Installation**
1. Clone the repository:
   ```
   git clone https://github.com/your-username/tradebot.git
   cd tradebot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment:
   ```
   cp .env.example .env
   ```
   
4. Edit `.env` file with your MEXC API credentials and settings.

## 🚀 **Running the Bot**

### **Testing API Connection**
```
python test_api.py
```

### **Running the Bot**
```
python main.py
```

## 📋 **Architecture Overview**

### **Core Modules**
- **API Module** (`api/mexc_api.py`): Handles all communication with MEXC API
- **Sniper Engine** (`core/sniper_engine.py`): Manages the detection and execution of buy orders for target pairs
- **Order Executor** (`core/order_executor.py`): Executes and monitors orders
- **Sell Strategy Manager** (`core/sell_strategy_manager.py`): Manages different sell strategies

### **Supporting Modules**
- **Telegram Bot** (`telegram/telegram_bot.py`): Provides Telegram integration for commands and notifications
- **Dashboard Manager** (`dashboard/dashboard_manager.py`): Logs and displays performance metrics
- **Config** (`utils/config.py`): Manages configuration settings

## 🔧 **Telegram Commands**

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Start the bot | `/start` |
| `/help` | Show help message | `/help` |
| `/status` | Show bot status | `/status` |
| `/balance` | Show wallet balance | `/balance` |
| `/snipe <pair> <amount>` | Add a token to snipe | `/snipe BTCUSDT 100` |
| `/buy <pair> <amount>` | Buy a token immediately | `/buy BTCUSDT 100` |
| `/sell <pair> <amount>` | Sell a token immediately | `/sell BTCUSDT 0.005` |
| `/cancel <pair>` | Cancel sniping for a token | `/cancel BTCUSDT` |

## 🛠️ **Configuration Options**

The bot can be configured via the `.env` file with the following settings:

| Setting | Description | Default |
|---------|-------------|---------|
| `MEXC_API_KEY` | Your MEXC API key | Required |
| `MEXC_API_SECRET` | Your MEXC API secret | Required |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Optional |
| `TELEGRAM_CHAT_ID` | Allowed Telegram chat ID(s) | Optional |
| `DEFAULT_USDT_AMOUNT` | Default amount in USDT for trades | 100 |
| `BUY_FREQUENCY_MS` | Default buy frequency in ms | 10 |
| `MAX_RETRY_ATTEMPTS` | Maximum retry attempts | 5 |
| `PROFIT_TARGET_PERCENTAGE` | Default take profit percentage | 20 |
| `STOP_LOSS_PERCENTAGE` | Default stop loss percentage | 10 |
| `TRAILING_STOP_PERCENTAGE` | Default trailing stop percentage | 5 |
| `TIME_BASED_SELL_MINUTES` | Default time to auto-sell in minutes | 30 |

## 📊 **Performance Considerations**

- The bot is designed to execute trades with ultra-low latency (target: 1-50ms)
- WebSocket connections provide real-time data and faster execution
- Retry logic ensures orders are filled even during high network congestion
- Asynchronous architecture allows for multiple simultaneous operations

## 🔒 **Security**

- API keys should have appropriate permissions (trading only, no withdrawals)
- Environment variables are used to store sensitive information
- The bot validates user commands to ensure only authorized users can control it

## 🔍 **Troubleshooting**

- Check `logs/` directory for detailed logs
- Use `test_api.py` to verify API connectivity
- Ensure time synchronization between your system and MEXC servers
