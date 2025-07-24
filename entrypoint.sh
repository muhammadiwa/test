#!/bin/bash
set -e

# Initialize environment variables from .env file if present
if [ -f ".env" ]; then
    echo "Loading environment from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Set trap to handle Docker stop signals gracefully
trap "echo 'Received SIGTERM, shutting down...'; rm -f /app/data/bot_running; exit 0" SIGTERM
trap "echo 'Received SIGINT, shutting down...'; rm -f /app/data/bot_running; exit 0" SIGINT

# Create a file to indicate the bot is running (for healthcheck)
mkdir -p /app/data
touch /app/data/bot_running

# Display Python version
echo "Using Python version:"
python --version

# Setup VPN if enabled
if [ "$USE_VPN" = "true" ]; then
    echo "VPN enabled, checking for VPN configuration..."
    mkdir -p /app/vpn
    
    # Check if custom VPN configuration exists
    if [ -f "/app/vpn/custom.ovpn" ]; then
        echo "Using custom VPN configuration..."
        VPN_CONFIG="/app/vpn/custom.ovpn"
    else
        echo "No custom VPN config found. Connecting to free Singapore VPN server..."
        
        # Download free VPN configuration (VPN Gate - Singapore)
        wget -q https://www.vpngate.net/en/ -O /app/vpn/vpngate.html
        
        # Extract Singapore VPN server from VPN Gate
        SG_OVPN_URL=$(grep -o 'https://www.vpngate.net/common/openvpn_download.aspx[^"]*SG[^"]*' /app/vpn/vpngate.html | head -1)
        
        if [ -z "$SG_OVPN_URL" ]; then
            echo "Error: Could not find Singapore VPN server. Running without VPN."
            VPN_CONFIG=""
        else
            wget -q "$SG_OVPN_URL" -O /app/vpn/singapore.ovpn
            
            # Adjust OpenVPN config for container environment
            sed -i 's/auth-user-pass/auth-user-pass \/app\/vpn\/auth.txt/g' /app/vpn/singapore.ovpn
            VPN_CONFIG="/app/vpn/singapore.ovpn"
        fi
    fi
    
    # If we have a VPN config, connect to it
    if [ -n "$VPN_CONFIG" ]; then
        # Create auth file if needed (VPN Gate servers typically don't require authentication)
        if [ ! -f "/app/vpn/auth.txt" ]; then
            echo "vpn" > /app/vpn/auth.txt
            echo "vpn" >> /app/vpn/auth.txt
            chmod 600 /app/vpn/auth.txt
        fi
        
        # Start OpenVPN in the background
        echo "Starting OpenVPN connection with $VPN_CONFIG..."
        # Log VPN output to a file for troubleshooting
        openvpn --config "$VPN_CONFIG" --log /var/log/openvpn.log --daemon
        
        # Wait for VPN connection to establish
        echo "Waiting for VPN connection to establish..."
        sleep 10
        
        # Verify VPN connection
        echo "VPN connection status:"
        ip addr show | grep "tun0"
        if [ $? -ne 0 ]; then
            echo "Warning: VPN interface not found. Check VPN connection."
            echo "Displaying VPN logs for troubleshooting:"
            tail -n 20 /var/log/openvpn.log
        else
            echo "VPN connection established successfully."
            echo "Current IP address:"
            wget -q -O- https://ifconfig.me || echo "Could not determine external IP"
        fi
    fi
fi

# Start the bot
echo "Starting TradingBot..."
python main.py

# In case the bot exits, remove the running file
rm -f /app/data/bot_running

# Keep container running for debugging if needed
# tail -f /dev/null
