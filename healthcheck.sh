#!/bin/bash

# Health check script untuk TradingBot
# Script ini akan dicek oleh Docker untuk memastikan container berjalan dengan baik

set -e

# Function to check if bot process is running
check_bot_process() {
    if pgrep -f "python main.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to check VPN connection (if enabled)
check_vpn_connection() {
    if [ "$VPN_ENABLED" = "true" ]; then
        if ip route | grep -q tun; then
            return 0
        else
            echo "VPN connection not found"
            return 1
        fi
    else
        return 0
    fi
}

# Function to check MEXC API connectivity
check_mexc_api() {
    if curl -s --max-time 5 https://api.mexc.com/api/v3/ping > /dev/null; then
        return 0
    else
        echo "MEXC API not accessible"
        return 1
    fi
}

# Function to check if log file is being updated (bot is active)
check_log_activity() {
    if [ -f "/app/logs/sniper_bot_$(date +%Y-%m-%d).log" ]; then
        # Check if log file was modified in the last 5 minutes
        if [ $(find "/app/logs/sniper_bot_$(date +%Y-%m-%d).log" -mmin -5 2>/dev/null | wc -l) -gt 0 ]; then
            return 0
        else
            echo "Log file not updated recently"
            return 1
        fi
    else
        # If no log file exists yet, just check if process is running
        return 0
    fi
}

# Main health check
main() {
    echo "Running health check..."
    
    # Check if bot process is running
    if ! check_bot_process; then
        echo "❌ Bot process not running"
        exit 1
    fi
    echo "✅ Bot process is running"
    
    # Check VPN connection if enabled
    if ! check_vpn_connection; then
        echo "❌ VPN check failed"
        exit 1
    fi
    echo "✅ VPN check passed"
    
    # Check MEXC API connectivity
    if ! check_mexc_api; then
        echo "❌ MEXC API not accessible"
        exit 1
    fi
    echo "✅ MEXC API accessible"
    
    # Check log activity
    if ! check_log_activity; then
        echo "⚠️  Log activity check failed (may be normal for new containers)"
        # Don't exit with error for log activity check as it might be normal
    else
        echo "✅ Log activity detected"
    fi
    
    echo "✅ Health check passed"
    exit 0
}

# Run main function
main
