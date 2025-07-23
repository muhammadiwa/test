# Docker Deployment Guide for Tradebot

This guide explains how to deploy the trading bot using Docker for consistent and isolated runtime environments.

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine

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

3. Build and start the container:

   ```bash
   docker-compose up -d
   ```

4. Check the logs:

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

## Troubleshooting

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Restart the container: `docker-compose restart`
3. Rebuild the container if needed: `docker-compose up -d --build`

## Security Notes

- Never push your `.env` file with real API keys to Git repositories
- Consider using Docker secrets for sensitive information in production environments
