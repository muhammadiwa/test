#!/bin/bash
set -e

# Initialize environment variables from .env file if present
if [ -f ".env" ]; then
    echo "Loading environment from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Set trap to handle Docker stop signals gracefully
trap "echo 'Received SIGTERM, shutting down...'; exit 0" SIGTERM
trap "echo 'Received SIGINT, shutting down...'; exit 0" SIGINT

# Start the bot
echo "Starting TradingBot..."
python main.py

# Keep container running for debugging if needed
# tail -f /dev/null
