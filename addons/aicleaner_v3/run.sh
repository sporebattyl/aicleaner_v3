#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant AICleaner v3 Add-on
# Starts the AICleaner v3 web interface and backend services
# ==============================================================================

# Set up configuration
CONFIG_PATH="/data/options.json"
AICLEANER_DATA_PATH="/data/aicleaner"
AICLEANER_CONFIG_PATH="/data/aicleaner/config.yaml"

# Create data directories if they don't exist
mkdir -p "$AICLEANER_DATA_PATH"
mkdir -p "$AICLEANER_DATA_PATH/logs"
mkdir -p "$AICLEANER_DATA_PATH/models"
mkdir -p "$AICLEANER_DATA_PATH/security"
mkdir -p /data/cache
mkdir -p /data/snapshots

# Log startup
bashio::log.info "Starting AICleaner v3 Home Assistant Add-on..."

# Check if configuration file exists
if bashio::config.exists 'log_level'; then
    LOG_LEVEL=$(bashio::config 'log_level')
else
    LOG_LEVEL="info"
fi

bashio::log.info "Setting log level to: $LOG_LEVEL"

# Export environment variables
export AICLEANER_DATA_PATH="$AICLEANER_DATA_PATH"
export AICLEANER_CONFIG_PATH="$AICLEANER_CONFIG_PATH"
export PYTHONPATH="/usr/src/app:$PYTHONPATH"

# Handle ingress if enabled
if bashio::config.exists 'ingress_port'; then
    INGRESS_PORT=$(bashio::config 'ingress_port')
    if [ "$INGRESS_PORT" != "null" ] && [ "$INGRESS_PORT" != "0" ]; then
        export INGRESS_PORT="$INGRESS_PORT"
        bashio::log.info "Ingress enabled on port: $INGRESS_PORT"
    else
        export INGRESS_PORT="8000"
        bashio::log.info "Using default ingress port: 8000"
    fi
else
    export INGRESS_PORT="8000"
fi

# Initialize configuration if not exists
if [ ! -f "$AICLEANER_CONFIG_PATH" ]; then
    bashio::log.info "Initializing default configuration..."
    
    # Create default configuration from Home Assistant options
    cat > "$AICLEANER_CONFIG_PATH" << EOF
# AICleaner v3 Configuration
# Auto-generated from Home Assistant Add-on options
version: "3.0.0"

# General settings
general:
  log_level: "$LOG_LEVEL"
  data_path: "$AICLEANER_DATA_PATH"
  enable_web_interface: true
  web_port: $INGRESS_PORT

# AI Provider configuration
ai_providers:
EOF

    # Add AI providers from configuration
    if bashio::config.exists 'ai_providers'; then
        for provider in $(bashio::config 'ai_providers | keys[]'); do
            PROVIDER_ENABLED=$(bashio::config "ai_providers[${provider}].enabled")
            PROVIDER_NAME=$(bashio::config "ai_providers[${provider}].provider")
            
            cat >> "$AICLEANER_CONFIG_PATH" << EOF
  - name: "$PROVIDER_NAME"
    enabled: $PROVIDER_ENABLED
    priority: 1
    rate_limit_rpm: 60
    rate_limit_tpm: 10000
    daily_budget: 10.0
EOF
        done
    fi

    # Add zones configuration
    cat >> "$AICLEANER_CONFIG_PATH" << EOF

# Zone configuration
zones:
EOF

    if bashio::config.exists 'zones'; then
        for zone in $(bashio::config 'zones | keys[]'); do
            ZONE_NAME=$(bashio::config "zones[${zone}].name")
            ZONE_ENABLED=$(bashio::config "zones[${zone}].enabled")
            
            cat >> "$AICLEANER_CONFIG_PATH" << EOF
  - name: "$ZONE_NAME"
    enabled: $ZONE_ENABLED
    devices: []
    automation_rules: []
EOF
        done
    fi

    # Add security configuration
    SECURITY_ENABLED=$(bashio::config 'security.enabled')
    ENCRYPTION_ENABLED=$(bashio::config 'security.encryption')
    AUDIT_LOGGING=$(bashio::config 'security.audit_logging')
    
    cat >> "$AICLEANER_CONFIG_PATH" << EOF

# Security configuration
security:
  enabled: $SECURITY_ENABLED
  encryption: $ENCRYPTION_ENABLED
  audit_logging: $AUDIT_LOGGING
  ssl_certificate: null
  ssl_key: null

# Performance configuration
performance:
  auto_optimization: true
  resource_monitoring: true
  caching: true
  max_memory_mb: 512
  max_cpu_percent: 80

# Privacy configuration
privacy:
  enabled: true
  level: "balanced"
  models:
    face_detection:
      speed: "models/yunet.onnx"
      balanced: "models/retinaface.onnx"
      paranoid: "models/scrfd.onnx"
    object_detection:
      general: "models/yolov8m.onnx"
      license_plates: "models/yolov8_license_plates.onnx"
    text_detection: "models/paddle_ocr.onnx"
  redaction:
    face_mode: "blur"
    license_plate_mode: "black_box"
    pii_text_mode: "black_box"
  performance:
    max_image_size: [1920, 1080]
    parallel_processing: true
    model_caching: true
    async_processing: true
EOF

    bashio::log.info "Default configuration created at: $AICLEANER_CONFIG_PATH"
fi

# Change to the application directory
cd /usr/src/app

# Start the application
bashio::log.info "Starting AICleaner v3 backend service..."
bashio::log.info "Web interface will be available at: http://localhost:$INGRESS_PORT"

# Start the FastAPI backend with proper configuration
exec python -m uvicorn api.backend:app \
    --host 0.0.0.0 \
    --port "$INGRESS_PORT" \
    --log-level "$LOG_LEVEL" \
    --no-server-header \
    --no-date-header \
    --forwarded-allow-ips "*" \
    --proxy-headers