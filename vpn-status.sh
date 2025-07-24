#!/bin/bash
# vpn-status.sh - Script to check VPN status in the tradebot container

# Check if container is running
if ! docker ps | grep -q tradebot; then
    echo "Error: tradebot container is not running."
    echo "Start it with: docker-compose up -d"
    exit 1
fi

echo "=== Checking VPN Status ==="
echo "VPN Interface:"
docker exec -it tradebot ip addr show | grep tun0 || echo "VPN interface not found."

echo -e "\nCurrent IP Address:"
docker exec -it tradebot wget -q -O- https://ifconfig.me || echo "Could not determine external IP"

echo -e "\nVPN Logs (last 10 lines):"
docker exec -it tradebot cat /var/log/openvpn.log 2>/dev/null | tail -n 10 || echo "No VPN logs found."

echo -e "\nRouting Table:"
docker exec -it tradebot ip route

echo -e "\nConnection Test to MEXC:"
docker exec -it tradebot curl -I -s https://www.mexc.com | head -n 1 || echo "Could not connect to MEXC."

echo -e "\nTo restart the VPN connection:"
echo "docker-compose restart tradebot"
