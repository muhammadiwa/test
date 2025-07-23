FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make sure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Create volume for data persistence
VOLUME /app/data

# Run the bot
CMD ["./entrypoint.sh"]
