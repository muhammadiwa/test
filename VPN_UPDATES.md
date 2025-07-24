# VPN Integration for MEXC API Access

## Overview of Changes

We've enhanced the Docker deployment of the MEXC Sniper Bot to include VPN functionality, allowing users in regions with restricted access (like Indonesia) to connect to the MEXC API through Singapore VPN servers.

### 1. Docker Configuration Updates

- Modified `Dockerfile` to install OpenVPN and necessary networking tools
- Updated `docker-compose.yml` to add network capabilities (`NET_ADMIN`, `SYS_ADMIN`) required for VPN
- Added environment variable `USE_VPN` to control VPN functionality
- Added volume for VPN configuration files

### 2. VPN Connection Management

- Enhanced `entrypoint.sh` to automatically:
  - Download and connect to free Singapore VPN servers from VPN Gate
  - Support custom VPN configurations
  - Verify VPN connection status
  - Log connection details for troubleshooting

### 3. Documentation

- Created `VPN_GUIDE.md` with detailed instructions for VPN configuration
- Created `PANDUAN_INDONESIA.md` with instructions in Bahasa Indonesia
- Updated `README.md` to include VPN information
- Updated `DOCKER_DEPLOYMENT.md` to include VPN setup steps

### 4. Troubleshooting Tools

- Created `vpn-status.sh` script to check VPN connection status

## How to Use

1. Enable VPN in your `.env` file:
   ```
   USE_VPN=true
   ```

2. Launch the bot normally:
   ```
   docker-compose up -d
   ```

3. The bot will automatically connect to a Singapore VPN before starting.

## Advanced Configuration

For users who want more control:

1. Place a custom OpenVPN (.ovpn) file in the `./vpn` directory named `custom.ovpn`
2. Restart the container to use your custom VPN configuration

## Troubleshooting

If you experience connectivity issues:

1. Run the VPN status script:
   ```
   bash vpn-status.sh
   ```

2. Check container logs:
   ```
   docker-compose logs -f
   ```

3. Try restarting the container:
   ```
   docker-compose restart tradebot
   ```
