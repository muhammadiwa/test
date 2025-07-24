# Docker Deployment Guide for Tradebot

This guide explains how to deploy the trading bot using Docker for consistent and isolated runtime environments.

## Prerequisites

- Docker installed on your machine ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose installed on your machine ([Get Docker Compose](https://docs.docker.com/compose/install/))

## System Requirements

- Minimum: 1 CPU core, 1GB RAM, 5GB disk space
- Recommended: 2 CPU cores, 2GB RAM, 10GB disk space
- Operating System: Any OS that can run Docker (Linux, Windows with WSL2, macOS)
- Network: Stable internet connection required

## Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/tradebot.git
   cd tradebot
   ```

2. Copy the example environment file and edit it with your settings:

   ```bash
   cp .env.example .env
   nano .env
   ```

3. Configure the VPN (for users in regions where MEXC API is restricted):
   
   In your `.env` file, ensure VPN is enabled:
   
   ```bash
   USE_VPN=true  # Enable VPN for regions with API access restrictions
   ```
   
   For more detailed VPN configuration, see [VPN_GUIDE.md](VPN_GUIDE.md).

4. Build and start the container:

   ```bash
   docker-compose up -d
   ```

5. Check the logs:

   ```bash
   docker-compose logs -f
   ```

## Configuration

All configuration is done through the `.env` file. Make sure to set:

- MEXC API credentials
- Telegram Bot token and chat ID
- Trading parameters (profit targets, stop loss, etc.)

## Data Persistence

The bot stores data in the `./data` directory which is mounted as a volume in the container.
This ensures your data persists even if the container is stopped or removed.

## Stopping the Bot

To stop the bot:

```bash
docker-compose down
```

## Updating

To update the bot with the latest code:

```bash
git pull
docker-compose down
docker-compose up -d --build
```

## Python Version

This bot is specifically configured to use Python 3.10 to minimize dependency conflicts and ensure compatibility with all required packages. The Docker setup handles this automatically by using the `python:3.10-slim` base image.

## Troubleshooting

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Restart the container: `docker-compose restart`
3. Rebuild the container if needed: `docker-compose up -d --build`
4. Check container health status: `docker inspect --format "{{.State.Health.Status}}" tradebot`
5. For dependency issues, verify that you're using the recommended Python 3.10 version

### Common Issues and Solutions

1. **Container exits immediately after starting**
   - Check the logs: `docker-compose logs`
   - Verify that your .env file is properly configured
   - Ensure API keys are valid

2. **Network connection errors**
   - Verify your internet connection
   - Check if MEXC API is accessible from your network
   - Consider using a VPN if your ISP blocks cryptocurrency exchanges

3. **Memory issues**
   - The container is configured with a 1GB memory limit
   - If you're running on a low-memory system, modify the `deploy.resources.limits.memory` value in docker-compose.yml

4. **Python version conflicts**
   - The Docker setup uses Python 3.10
   - If running locally without Docker, make sure to use Python 3.10 specifically

## Using the Bot

Once deployed, interact with the bot through Telegram. Available commands:

- `/start` - Start the bot
- `/help` - Show help message
- `/status` - Show bot status
- `/balance` - Show wallet balance
- `/price <pair1> [pair2] [pair3]...` - Check current prices (up to 5 pairs)
- `/price <pair1> [pair2] [pair3]... --ob` - Check prices with detailed orderbooks
- `/cek <pair1> [pair2] [pair3]...` - Check prices with detailed orderbooks (alias for price with --ob)
- `/cek <pair1> [pair2] [pair3]... --noob` - Check only prices without orderbooks
- `/snipe <pair> <amount>` - Add a token to snipe
- `/buy <pair> <amount>` - Buy a token immediately
- `/sell <pair> <amount>` - Sell a token immediately
- `/cancel <pair>` - Cancel sniping for a token
- `/config` - View and modify bot configuration

### Orderbook Feature

The bot now displays detailed orderbook data when checking prices:

- View buy and sell orders with volume
- See spread information between best ask and bid prices
- Quickly analyze market depth for better trading decisions

Example usage:

```bash
/cek BTCUSDT ETHUSDT      # Shows prices and orderbooks for BTC and ETH
/cek BTCUSDT --noob       # Shows only price without orderbook
/price ETHUSDT --ob       # Shows price with orderbook
```

## Security Notes

- Never push your `.env` file with real API keys to Git repositories
- Consider using Docker secrets for sensitive information in production environments
- The Docker setup runs as a non-root user for enhanced security
- Ensure your host system is secured with firewalls and regular updates
- Regularly update your Docker images to get security patches: `docker-compose pull && docker-compose up -d`

## Backup and Recovery

To back up your data:

1. Stop the bot: `docker-compose down`
2. Create a backup of the data folder:

   ```bash
   tar -czvf tradebot_backup_$(date +%Y%m%d).tar.gz ./data
   ```

3. Store the backup in a safe location
4. Restart the bot: `docker-compose up -d`

To restore from a backup:

1. Stop the bot: `docker-compose down`
2. Extract the backup:

   ```bash
   tar -xzvf tradebot_backup_YYYYMMDD.tar.gz -C /path/to/tradebot/
   ```

3. Restart the bot: `docker-compose up -d`

## Advanced Docker Configuration

For production deployments, consider these additional configurations:

1. **Auto-restart with system boot**:

   ```bash
   docker update --restart=always tradebot
   ```

2. **Network settings**: Create a dedicated network for better isolation:

   ```bash
   docker network create tradebot-network
   ```

   Then update your docker-compose.yml with:

   ```yaml
   networks:
     - tradebot-network
   ```

3. **Monitoring**: Use Docker's built-in tools:

   ```bash
   docker stats tradebot
   ```
   
   Or integrate with Prometheus and Grafana for advanced monitoring.
