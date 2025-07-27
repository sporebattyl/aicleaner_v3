ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set shell to bash with error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install Python and essential packages
RUN apk add --no-cache \
    bash \
    jq \
    python3 \
    py3-pip \
    curl

# Install bashio for Home Assistant integration
RUN pip3 install --no-cache-dir bashio

# Create working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY run.sh /
RUN chmod +x /run.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the addon
CMD [ "/run.sh" ]