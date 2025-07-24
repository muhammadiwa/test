# VPN Configuration for MEXC API Access

Since MEXC API is not accessible from Indonesia, this Docker setup includes integrated VPN capability that connects to a free Singapore VPN server.

## How It Works

1. The Docker container includes OpenVPN and automatically connects to a freely available Singapore VPN server from [VPN Gate](https://www.vpngate.net/).
2. The connection is established before starting the bot, ensuring all API calls are routed through the VPN.
3. VPN connection details are logged to the container's output for troubleshooting.

## Configuration

You can control the VPN feature through environment variables in your `.env` file or by modifying the `docker-compose.yml` file:

```yaml
environment:
  - USE_VPN=true  # Set to 'false' to disable VPN
```

## Using Your Own VPN Configuration

If you have a premium VPN service or prefer to use your own configuration:

1. Place your `.ovpn` configuration file in the `./vpn` directory (create it if it doesn't exist)
2. Rename your config file to `custom.ovpn`
3. Update the entrypoint.sh script to use your custom config:

```bash
# Edit entrypoint.sh
if [ -f "/app/vpn/custom.ovpn" ]; then
  # Use custom VPN config
  openvpn --config /app/vpn/custom.ovpn --daemon
else
  # Use default VPN Gate config
  # [existing code]
fi
```

## Troubleshooting

If you experience connectivity issues:

1. Check if the VPN is connected:

   ```bash
   docker exec -it tradebot ip addr show | grep tun0
   ```
   
2. View VPN logs:

   ```bash
   docker exec -it tradebot cat /var/log/openvpn.log
   ```

3. Try a different VPN server:
   - Visit [VPN Gate](https://www.vpngate.net/) and download a different Singapore .ovpn file
   - Place it in the `./vpn` directory as `custom.ovpn`

4. If all else fails, you can disable the VPN and use a proxy server instead.

## Security Notes

- Free VPN services might have limitations in bandwidth, speed, and privacy
- For production use, consider using a paid VPN service with dedicated servers
- Always ensure your API keys are stored securely
