FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install necessary system dependencies including VPN tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    dos2unix \
    iproute2 \
    iptables \
    net-tools \
    openvpn \
    supervisor \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for VPN and supervisor
RUN mkdir -p /etc/openvpn /var/log/supervisor /app/vpn

# Copy VPN and supervisor configuration files
COPY vpn/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Make sure entrypoint and health check scripts are executable and fix line endings
RUN chmod +x /app/entrypoint.sh /app/vpn/start_vpn.sh /app/healthcheck.sh /app/start_bot.sh && \
    dos2unix /app/entrypoint.sh /app/vpn/start_vpn.sh /app/healthcheck.sh /app/start_bot.sh

# Create volume for data persistence
VOLUME /app/data

# Expose port for dashboard if needed
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/app/healthcheck.sh"]

# Use entrypoint script to setup environment and start supervisor
CMD ["/app/entrypoint.sh"]
