ARG BUILD_FROM=python:3.11-alpine
FROM ${BUILD_FROM}

# Install bash first (needed for shell setting)
RUN apk add --no-cache bash

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install remaining system dependencies
RUN apk add --no-cache \
    jq \
    python3 \
    py3-pip \
    curl

# Set up a non-root user for security
RUN addgroup -S app && adduser -S -G app app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY src/ ./src/

# Copy and set permissions for run script
COPY run.sh /
RUN chmod +x /run.sh

# Create data directories with proper permissions
RUN mkdir -p /data /config && chown -R app:app /data /config /app

# Switch to non-root user
USER app

# Health check - verify main process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ps aux | grep -v grep | grep "python.*src/main.py" || exit 1

# Set the entrypoint
CMD [ "/run.sh" ]