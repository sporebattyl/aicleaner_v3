ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

# Install bash first (needed for shell setting)
RUN apk add --no-cache bash

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies including build tools for Python packages
RUN apk add --no-cache \
    jq \
    python3 \
    py3-pip \
    curl \
    gcc \
    musl-dev \
    linux-headers \
    python3-dev

# Note: bashio is pre-installed in Home Assistant base images

# Create app user early
RUN addgroup -S app && adduser -S -G app app

# Set working directory and create directories with proper ownership
WORKDIR /app
RUN mkdir -p /data /config && chown -R app:app /data /config /app

# Copy requirements and install as root, then switch user
COPY requirements.txt .

# Handle architecture-specific installation, especially for ARM builds
ARG BUILD_FROM
RUN echo "Building from base image: $BUILD_FROM" && \
    case "$BUILD_FROM" in \
        *armv7*|*armhf*) \
            echo "Installing for ARM architecture with optimizations..." && \
            apk add --no-cache py3-cryptography py3-psutil && \
            pip install --no-cache-dir --prefer-binary --no-build-isolation \
                --only-binary=cryptography,psutil -r requirements.txt ;; \
        *) \
            echo "Installing for standard architecture..." && \
            pip install --no-cache-dir -r requirements.txt ;; \
    esac

# Copy source code with proper ownership
COPY --chown=app:app src/ ./src/
COPY --chown=app:app run.sh /
RUN chmod +x /run.sh

# Switch to non-root user
USER app

# Health check - verify main process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ps aux | grep -v grep | grep "python.*src/main.py" || exit 1

# Set the entrypoint
CMD [ "/run.sh" ]