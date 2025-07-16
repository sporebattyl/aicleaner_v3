# Multi-stage build for optimized AICleaner v3 container
# Stage 1: Build dependencies
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    git \
    curl

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime image
ARG BUILD_FROM
FROM $BUILD_FROM

# Install runtime dependencies only
RUN apk add --no-cache \
    python3 \
    py3-pip \
    jpeg \
    zlib \
    freetype \
    lcms2 \
    openjpeg \
    tiff \
    curl \
    bash

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set the working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/www \
    /data/cache \
    /data/snapshots \
    /data/aicleaner \
    /config \
    /logs

# Copy application files with proper structure
COPY *.py ./
COPY ai/ ./ai/
COPY core/ ./core/
COPY integrations/ ./integrations/
COPY gamification/ ./gamification/
COPY notifications/ ./notifications/
COPY rules/ ./rules/
COPY utils/ ./utils/
COPY mobile/ ./mobile/
COPY mqtt/ ./mqtt/
COPY tests/ ./tests/
COPY www/ ./www/
COPY config.yaml ./
COPY config.json ./
COPY run.sh ./
COPY utils/services.yaml ./

# Make scripts executable
RUN chmod +x run.sh

# Set environment variables for Docker deployment
ENV PYTHONPATH="/app:$PYTHONPATH" \
    PYTHONUNBUFFERED=1 \
    AICLEANER_DATA_PATH="/data/aicleaner" \
    AICLEANER_LOG_LEVEL="INFO" \
    AICLEANER_PRIVACY_LEVEL="standard"

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8099', timeout=5)" || exit 1

# Expose ports
EXPOSE 8099

# Set proper ownership and permissions
RUN chown -R root:root /app && \
    chmod -R 755 /app

# Start the application
CMD ["./run.sh"]