#!/bin/bash

# VPN startup script untuk Asia VPN gratis
set -e

echo "Starting VPN connection to Asia server..."

# Function to download free VPN config
download_free_vpn() {
    echo "Downloading free Asia VPN configuration..."
    
    # ProtonVPN Free servers (Asia)
    # Note: Anda perlu mendaftar gratis di ProtonVPN untuk mendapatkan credentials
    if [ ! -f "/app/vpn/config.ovpn" ]; then
        echo "VPN config file not found. Please provide a valid .ovpn file."
        echo "You can get free VPN from:"
        echo "1. ProtonVPN Free - https://protonvpn.com/free-vpn"
        echo "2. Windscribe Free - https://windscribe.com"
        echo "3. TunnelBear Free - https://tunnelbear.com"
        
        # Create sample config template
        cat > /app/vpn/config.ovpn << 'EOF'
# Sample OpenVPN configuration
# Replace this with your actual VPN provider configuration
# 
# For ProtonVPN Free:
# 1. Sign up at https://protonvpn.com/free-vpn
# 2. Download Singapore or Japan server config
# 3. Replace this file with the downloaded config
#
# For Windscribe Free:
# 1. Sign up at https://windscribe.com
# 2. Generate OpenVPN config for Hong Kong or Singapore
# 3. Replace this file with the generated config

client
dev tun
proto udp
remote your-vpn-server.com 1194
resolv-retry infinite
nobind
persist-key
persist-tun
ca ca.crt
cert client.crt
key client.key
remote-cert-tls server
auth SHA512
cipher AES-256-CBC
ignore-unknown-option block-outside-dns
block-outside-dns
verb 3
EOF
        echo "Please replace /app/vpn/config.ovpn with your actual VPN configuration"
        return 1
    fi
    
    return 0
}

# Function to test internet connectivity
test_connectivity() {
    echo "Testing internet connectivity..."
    if curl -s --max-time 10 https://httpbin.org/ip > /dev/null; then
        echo "Internet connection: OK"
        return 0
    else
        echo "Internet connection: FAILED"
        return 1
    fi
}

# Function to test MEXC API access
test_mexc_api() {
    echo "Testing MEXC API accessibility..."
    if curl -s --max-time 10 https://api.mexc.com/api/v3/ping > /dev/null; then
        echo "MEXC API access: OK"
        return 0
    else
        echo "MEXC API access: BLOCKED - VPN needed"
        return 1
    fi
}

# Function to start VPN
start_vpn() {
    echo "Starting OpenVPN connection..."
    
    # Check if config file exists and has credentials
    if [ ! -f "/app/vpn/config.ovpn" ]; then
        echo "Error: VPN configuration file not found!"
        return 1
    fi
    
    # Create auth file if username/password provided via environment
    if [ ! -z "$VPN_USERNAME" ] && [ ! -z "$VPN_PASSWORD" ]; then
        echo "Creating auth file from environment variables..."
        echo "$VPN_USERNAME" > /app/vpn/auth.txt
        echo "$VPN_PASSWORD" >> /app/vpn/auth.txt
        chmod 600 /app/vpn/auth.txt
        
        # Add auth-user-pass to config if not present
        if ! grep -q "auth-user-pass" /app/vpn/config.ovpn; then
            echo "auth-user-pass /app/vpn/auth.txt" >> /app/vpn/config.ovpn
        fi
    fi
    
    # Start OpenVPN
    openvpn --config /app/vpn/config.ovpn --daemon --log /var/log/openvpn.log
    
    # Wait for VPN to establish connection
    echo "Waiting for VPN connection to establish..."
    sleep 15
    
    # Check if VPN is connected
    for i in {1..30}; do
        if ip route | grep -q tun; then
            echo "VPN connection established!"
            break
        fi
        echo "Waiting for VPN... ($i/30)"
        sleep 2
    done
    
    if ! ip route | grep -q tun; then
        echo "Failed to establish VPN connection!"
        return 1
    fi
    
    return 0
}

# Main execution
main() {
    echo "=== VPN Setup for MEXC API Access ==="
    
    # Initial connectivity test
    test_connectivity || {
        echo "No internet connection available!"
        exit 1
    }
    
    # Test MEXC API without VPN
    if test_mexc_api; then
        echo "MEXC API is accessible without VPN. Skipping VPN setup."
        exit 0
    fi
    
    # Download/setup VPN config
    download_free_vpn || {
        echo "VPN configuration setup failed!"
        echo "Please manually configure your VPN by:"
        echo "1. Getting a free VPN account (ProtonVPN, Windscribe, etc.)"
        echo "2. Placing the .ovpn config file at /app/vpn/config.ovpn"
        echo "3. Setting VPN_USERNAME and VPN_PASSWORD environment variables"
        exit 1
    }
    
    # Start VPN
    start_vpn || {
        echo "Failed to start VPN connection!"
        exit 1
    }
    
    # Test connectivity after VPN
    sleep 5
    test_connectivity || {
        echo "Internet connectivity lost after VPN connection!"
        exit 1
    }
    
    # Test MEXC API after VPN
    if test_mexc_api; then
        echo "✅ VPN connected successfully! MEXC API is now accessible."
    else
        echo "⚠️  VPN connected but MEXC API still not accessible. Try different server."
    fi
    
    # Keep VPN running
    echo "VPN is running. Monitoring connection..."
    while true; do
        if ! ip route | grep -q tun; then
            echo "VPN connection lost! Attempting to reconnect..."
            start_vpn || {
                echo "Failed to reconnect VPN!"
                sleep 30
                continue
            }
        fi
        sleep 60
    done
}

# Run main function
main
