#!/bin/bash
set -e

echo "🚀 Starting TradingBot Container..."

# Initialize environment variables from .env file if present
if [ -f ".env" ]; then
    echo "📁 Loading environment from .env file"
    # Export only valid environment variables, excluding comments and empty lines
    set -a
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' .env | grep -v '^#')
    set +a
fi

# Function to wait for VPN connection
wait_for_vpn() {
    if [ "$VPN_ENABLED" = "true" ]; then
        echo "🔐 VPN enabled. Waiting for connection to be ready..."
        for i in {1..60}; do
            if ip route | grep -q tun; then
                echo "✅ VPN connection detected!"
                break
            fi
            echo "⏳ Waiting for VPN... ($i/60)"
            sleep 2
        done
        
        # Test MEXC API connectivity
        echo "🌐 Testing MEXC API connectivity..."
        if curl -s --max-time 10 https://api.mexc.com/api/v3/ping > /dev/null; then
            echo "✅ MEXC API is accessible through VPN!"
        else
            echo "⚠️  Warning: MEXC API still not accessible. Check VPN configuration."
        fi
    else
        echo "🌐 VPN is disabled. Testing direct MEXC API access..."
        if curl -s --max-time 10 https://api.mexc.com/api/v3/ping > /dev/null; then
            echo "✅ MEXC API is accessible directly!"
        else
            echo "❌ MEXC API is not accessible. Consider enabling VPN."
        fi
    fi
}

# Wait for VPN if enabled
wait_for_vpn

echo "📋 Starting Supervisor for process management..."
echo "🤖 Bot will auto-start and auto-restart if crashes"
echo "📊 Logs available via 'docker-compose logs -f'"

# Start supervisor in foreground to keep container alive
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf