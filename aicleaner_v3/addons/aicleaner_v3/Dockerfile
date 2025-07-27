ARG BUILD_FROM
FROM ${BUILD_FROM}

# Set shell to bash with error handling
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install runtime packages optimized for cross-architecture builds
RUN apk add --no-cache \
    bash \
    jq \
    python3 \
    py3-pip \
    curl \
    py3-cryptography \
    py3-psutil \
    py3-aiohttp \
    py3-yaml \
    py3-requests \
    && apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    python3-dev

# bashio is pre-installed in Home Assistant base images

# Create working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir --break-system-packages -r requirements.txt && \
    apk del .build-deps

# Copy source code
COPY src/ ./src/
COPY config/ ./config/ 2>/dev/null || true
COPY run.sh /
RUN chmod +x /run.sh

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/temp

# Health check with proper endpoint (uses internal port 8000)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the addon
CMD [ "/run.sh" ]