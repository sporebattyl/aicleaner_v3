ARG BUILD_FROM=ghcr.io/hassio-addons/base:15.0.1
FROM $BUILD_FROM

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies and Python
RUN apk add --no-cache \
        python3 \
        python3-dev \
        py3-pip \
        py3-setuptools \
        py3-wheel \
        py3-pillow \
        py3-numpy \
        py3-aiohttp \
        py3-paho-mqtt \
        py3-yaml \
        py3-requests \
        build-base \
        jpeg-dev \
        zlib-dev \
        libffi-dev \
        openssl-dev \
        rust \
        cargo \
        git

# Create app directory
RUN mkdir -p /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
WORKDIR /app

# Install Python packages
RUN pip3 install --no-cache-dir --prefer-binary -r requirements.txt

# Create application structure
RUN mkdir -p /app/src \
    && mkdir -p /app/core \
    && mkdir -p /app/core/providers \
    && mkdir -p /app/core/analysis \
    && mkdir -p /app/core/ha_integration \
    && mkdir -p /app/core/pdca \
    && mkdir -p /app/core/utils \
    && mkdir -p /data \
    && mkdir -p /config

# Copy application files
COPY src/ /app/src/
COPY core/ /app/core/
COPY run.sh /

# Set permissions
RUN chmod +x /run.sh \
    && chown -R root:root /app

# Add labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="sporebattyl" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="Home Assistant Community Add-ons" \
    org.opencontainers.image.authors="sporebattyl" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.url="https://github.com/sporebattyl/ai-cleaner" \
    org.opencontainers.image.source="https://github.com/sporebattyl/ai-cleaner" \
    org.opencontainers.image.documentation="https://github.com/sporebattyl/ai-cleaner/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Set working directory
WORKDIR /app

# Run script
CMD ["/run.sh"]