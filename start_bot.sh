#!/bin/bash

# Bot startup script
set -e

echo "=== TradingBot Starting ==="

# Load environment variables
if [ -f "/app/.env" ]; then
    echo "Loading environment variables..."
    set -a
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' /app/.env)
    set +a
fi

# Wait a bit for VPN to be ready if enabled
if [ "$VPN_ENABLED" = "true" ]; then
    echo "Waiting for VPN to be ready..."
    sleep 10
    
    # Check if VPN is working
    if ip route | grep -q tun; then
        echo "✅ VPN is active"
    else
        echo "⚠️  VPN not detected, but continuing..."
    fi
fi

# Change to app directory
cd /app

# Start the bot
echo "Starting Python TradingBot..."
exec python main.py
