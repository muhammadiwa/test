#!/bin/bash
set -e

# Initialize environment variables from .env file if present
if [ -f ".env" ]; then
    echo "Loading environment from .env file"
    # Export only valid environment variables, excluding comments and empty lines
    set -a
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env)
    set +a
fi

# Function to wait for VPN connection
wait_for_vpn() {
    if [ "$VPN_ENABLED" = "true" ]; then
        echo "Waiting for VPN connection to be ready..."
        for i in {1..60}; do
            if ip route | grep -q tun; then
                echo "VPN connection detected!"
                break
            fi
            echo "Waiting for VPN... ($i/60)"
            sleep 2
        done
        
        # Test MEXC API connectivity
        echo "Testing MEXC API connectivity..."
        if curl -s --max-time 10 https://api.mexc.com/api/v3/ping > /dev/null; then
            echo "✅ MEXC API is accessible through VPN!"
        else
            echo "⚠️  Warning: MEXC API still not accessible. Check VPN configuration."
        fi
    else
        echo "VPN is disabled. Testing direct MEXC API access..."
        if curl -s --max-time 10 https://api.mexc.com/api/v3/ping > /dev/null; then
            echo "✅ MEXC API is accessible directly!"
        else
            echo "❌ MEXC API is not accessible. Consider enabling VPN."
        fi
    fi
}

# Wait for VPN if enabled (only during initialization)
wait_for_vpn

# Keep container running without auto-starting the bot
echo "🚀 Container ready! Use 'docker compose exec tradebot bash -c \"cd /app && python main.py\"' to start the bot"
echo "📋 Container will stay alive for manual bot execution"

# Keep container alive
tail -f /dev/null
