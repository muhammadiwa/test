FROM python:3.10-slim as builder

# Set working directory
WORKDIR /app

# Install necessary system dependencies for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies into a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Second stage: create the runtime image
FROM python:3.10-slim

# Install OpenVPN and necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openvpn \
    unzip \
    wget \
    ca-certificates \
    iptables \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment path to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appuser . .

# Make sure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Create volume for data persistence and set permissions
RUN mkdir -p /app/data && \
    chown -R appuser:appuser /app/data
VOLUME /app/data

# Switch to non-root user
USER appuser

# Run the bot
CMD ["./entrypoint.sh"]
