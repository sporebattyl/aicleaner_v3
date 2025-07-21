# Multi-stage optimized Dockerfile for AICleaner v3 Home Assistant Add-on
# Supports multi-architecture builds: amd64, arm64, armv7

# Build arguments for multi-architecture support
ARG BUILD_ARCH=amd64
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Build stage - Optimized for size and security
FROM python:3.12-alpine3.19 as builder

# Build arguments
ARG BUILD_ARCH

# Set working directory
WORKDIR /build

# Install build dependencies in a single layer
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    g++ \
    musl-dev \
    linux-headers \
    libffi-dev \
    openssl-dev \
    cargo \
    rust \
    && apk add --no-cache \
    curl \
    git

# Create virtual environment for better dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel for faster builds
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements first for better cache utilization
COPY addons/aicleaner_v3/requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --compile --optimize=2 \
    --disable-pip-version-check \
    -r requirements.txt

# Clean up build dependencies to reduce size
RUN apk del .build-deps && \
    rm -rf /var/cache/apk/* /root/.cache /root/.cargo

# Production stage - Use Home Assistant base for multi-arch support
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base-python:3.12-alpine3.19 as production

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_REF
ARG BUILD_VERSION=1.0.0

# Set shell for better error handling
SHELL ["/bin/ash", "-o", "pipefail", "-c"]

# Install minimal runtime dependencies
RUN apk add --no-cache \
    bash \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/cache/apk/*

# Create application user for security
RUN addgroup -g 1000 aicleaner && \
    adduser -D -u 1000 -G aicleaner -s /bin/bash aicleaner

# Create working directory
WORKDIR /usr/src/app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code with proper ownership
COPY --chown=aicleaner:aicleaner addons/aicleaner_v3/ .

# Set executable permissions
RUN chmod +x run.sh

# Create data directories with proper permissions
RUN mkdir -p /data/aicleaner /share/aicleaner /tmp/aicleaner && \
    chown -R aicleaner:aicleaner /data/aicleaner /share/aicleaner /tmp/aicleaner

# Switch to non-root user for security
USER aicleaner

# Expose port for web interface
EXPOSE 8000

# Optimized health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Enhanced labels for Home Assistant and OCI compliance
LABEL \
    io.hass.name="AICleaner v3" \
    io.hass.description="Advanced AI-powered Home Assistant automation with intelligent device management" \
    io.hass.arch="aarch64|amd64|armhf|armv7|i386" \
    io.hass.type="addon" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.machine="intel-nuc|odroid-c2|odroid-c4|odroid-n2|odroid-xu|qemuarm|qemuarm-64|qemux86|qemux86-64|raspberrypi|raspberrypi2|raspberrypi3|raspberrypi4|raspberrypi3-64|raspberrypi4-64|tinker|yellow" \
    maintainer="AICleaner Team <support@aicleaner.dev>" \
    org.opencontainers.image.title="AICleaner v3" \
    org.opencontainers.image.description="Advanced AI-powered Home Assistant automation with intelligent device management, multi-provider AI integration, and comprehensive privacy protection" \
    org.opencontainers.image.url="https://github.com/drewcifer/aicleaner_v3" \
    org.opencontainers.image.source="https://github.com/drewcifer/aicleaner_v3" \
    org.opencontainers.image.documentation="https://github.com/drewcifer/aicleaner_v3/blob/main/README.md" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.revision="${BUILD_REF}" \
    org.opencontainers.image.version="${BUILD_VERSION}" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.vendor="AICleaner Project" \
    org.opencontainers.image.authors="AICleaner Team" \
    org.label-schema.schema-version="1.0" \
    org.label-schema.build-date="${BUILD_DATE}" \
    org.label-schema.version="${BUILD_VERSION}" \
    org.label-schema.vcs-ref="${BUILD_REF}"

# Switch back to root for final setup (Home Assistant requirement)
USER root

# Final setup and permissions
RUN chown -R root:root /usr/src/app && \
    chmod 755 /usr/src/app

# Default command
CMD ["./run.sh"]
