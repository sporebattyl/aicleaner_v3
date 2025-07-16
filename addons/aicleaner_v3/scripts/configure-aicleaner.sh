#!/bin/bash
# Configuration script for AICleaner v3 with Ollama integration
# Automatically configures AICleaner to connect to Ollama

set -e

# Configuration
CONFIG_FILE="config.yaml"
ENV_FILE=".env"
OLLAMA_HOST="${OLLAMA_HOST:-localhost:11434}"
BACKUP_SUFFIX=".backup.$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Ollama is accessible
check_ollama_connectivity() {
    log_info "Checking Ollama connectivity at $OLLAMA_HOST..."
    
    local api_url="http://$OLLAMA_HOST"
    local retries=0
    local max_retries=10
    
    while [[ $retries -lt $max_retries ]]; do
        if curl -s -f "$api_url/api/tags" >/dev/null 2>&1; then
            log_success "Ollama is accessible at $OLLAMA_HOST"
            return 0
        fi
        
        retries=$((retries + 1))
        log_info "Waiting for Ollama... ($retries/$max_retries)"
        sleep 3
    done
    
    log_error "Cannot connect to Ollama at $OLLAMA_HOST"
    log_error "Please ensure Ollama is running: systemctl status ollama"
    return 1
}

# Get available models from Ollama
get_available_models() {
    log_info "Retrieving available models from Ollama..."
    
    local api_url="http://$OLLAMA_HOST"
    local models_json
    
    models_json=$(curl -s "$api_url/api/tags" 2>/dev/null || echo '{"models":[]}')
    
    if [[ -n "$models_json" ]]; then
        echo "$models_json" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sort
    else
        log_warning "No models found or unable to retrieve model list"
        return 1
    fi
}

# Create backup of existing configuration
backup_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        log_info "Creating backup of existing configuration..."
        cp "$CONFIG_FILE" "${CONFIG_FILE}${BACKUP_SUFFIX}"
        log_success "Backup created: ${CONFIG_FILE}${BACKUP_SUFFIX}"
    fi
}

# Generate AICleaner configuration
generate_config() {
    log_info "Generating AICleaner configuration..."
    
    local available_models
    available_models=$(get_available_models)
    
    # Determine preferred models
    local vision_model=""
    local text_model=""
    
    if echo "$available_models" | grep -q "llava"; then
        vision_model=$(echo "$available_models" | grep "llava" | head -1)
    fi
    
    if echo "$available_models" | grep -q "mistral"; then
        text_model=$(echo "$available_models" | grep "mistral" | head -1)
    elif echo "$available_models" | grep -q "llama"; then
        text_model=$(echo "$available_models" | grep "llama" | head -1)
    fi
    
    # Create configuration file
    cat > "$CONFIG_FILE" << EOF
# AICleaner v3 Configuration
# Generated automatically by configure-aicleaner.sh

# Display name for the addon
display_name: "AI Cleaner v3"

# Local LLM Configuration (Ollama)
local_llm:
  enabled: true
  host: "$OLLAMA_HOST"
  auto_download: true
  preferred_models:
    vision: "${vision_model:-llava:13b}"
    text: "${text_model:-mistral:7b}"
  performance_tuning:
    timeout_seconds: 120
    max_concurrent_requests: 2
    memory_limit_mb: 4096
    quantization_level: 4

# AI Enhancements
ai_enhancements:
  predictive_analytics:
    enabled: true
    privacy_preserving: true
    retention_days: 30
  
  gamification:
    enabled: true
    privacy_first: true
    home_assistant_integration: true
  
  scene_understanding:
    enabled: true
    confidence_threshold: 0.7

# Cloud AI Fallback (optional)
cloud_ai:
  enabled: false
  gemini_api_key: ""  # Set this if you want cloud fallback
  
# Privacy Settings
privacy:
  level: "standard"  # strict, standard, relaxed
  data_retention_days: 30
  analytics_enabled: true
  telemetry_enabled: false

# Performance Settings
performance:
  max_memory_usage: 4096
  max_cpu_usage: 80
  cache_ttl_seconds: 300
  batch_processing: true

# Home Assistant Integration
home_assistant:
  api_url: "\${HA_URL:-http://homeassistant:8123}"
  token: "\${HA_TOKEN}"
  
# MQTT Configuration (optional)
mqtt:
  enabled: false
  host: ""
  port: 1883
  username: ""
  password: ""

# Zone Configuration (example)
zones:
  - name: "Living Room"
    camera_entity: "camera.living_room"
    todo_list_entity: "todo.living_room_cleaning"
    purpose: "Living room for relaxation and entertainment"
    interval_minutes: 60
    ignore_rules:
      - "Ignore items on the coffee table"
      - "Don't worry about books on the bookshelf"

# Logging Configuration
logging:
  level: "INFO"
  file: "/logs/aicleaner.log"
  max_size_mb: 10
  backup_count: 5

# Development Settings
development:
  debug_mode: false
  test_mode: false
  mock_cameras: false
EOF
    
    log_success "Configuration file created: $CONFIG_FILE"
}

# Generate environment file
generate_env_file() {
    log_info "Generating environment file..."
    
    cat > "$ENV_FILE" << EOF
# AICleaner v3 Environment Variables
# Generated automatically by configure-aicleaner.sh

# Ollama Configuration
OLLAMA_HOST=$OLLAMA_HOST
OLLAMA_MODELS_PATH=/data/models
OLLAMA_AUTO_DOWNLOAD=true

# AICleaner Configuration
AICLEANER_DATA_PATH=/data/aicleaner
AICLEANER_LOG_LEVEL=INFO
AICLEANER_PRIVACY_LEVEL=standard

# Home Assistant Integration
# Set these values according to your Home Assistant setup
HA_TOKEN=your_home_assistant_token_here
HA_URL=http://homeassistant:8123

# Performance Settings
MAX_MEMORY_USAGE=4096
MAX_CPU_USAGE=80
QUANTIZATION_LEVEL=4

# Optional: Cloud AI API Keys (for fallback)
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
EOF
    
    log_success "Environment file created: $ENV_FILE"
    log_warning "Please edit $ENV_FILE to set your Home Assistant token and URL"
}

# Test configuration
test_configuration() {
    log_info "Testing AICleaner configuration..."
    
    # Test Ollama connectivity with configured host
    local config_host
    config_host=$(grep "host:" "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
    
    if [[ -n "$config_host" ]]; then
        OLLAMA_HOST="$config_host"
        if check_ollama_connectivity; then
            log_success "Configuration test passed"
            return 0
        else
            log_error "Configuration test failed"
            return 1
        fi
    else
        log_error "Could not find Ollama host in configuration"
        return 1
    fi
}

# Show configuration summary
show_summary() {
    log_info "Configuration Summary:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📁 Configuration file: $CONFIG_FILE"
    echo "🌍 Environment file: $ENV_FILE"
    echo "🤖 Ollama host: $OLLAMA_HOST"
    
    if [[ -f "$CONFIG_FILE" ]]; then
        local vision_model text_model
        vision_model=$(grep -A 2 "preferred_models:" "$CONFIG_FILE" | grep "vision:" | awk '{print $2}' | tr -d '"')
        text_model=$(grep -A 3 "preferred_models:" "$CONFIG_FILE" | grep "text:" | awk '{print $2}' | tr -d '"')
        
        echo "👁️  Vision model: ${vision_model:-Not configured}"
        echo "📝 Text model: ${text_model:-Not configured}"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Next steps:"
    echo "1. Edit $ENV_FILE to set your Home Assistant token and URL"
    echo "2. Review and customize $CONFIG_FILE as needed"
    echo "3. Start AICleaner: docker-compose up -d"
    echo "4. Check logs: docker-compose logs -f aicleaner"
}

# Main configuration function
main() {
    log_info "Starting AICleaner configuration for Ollama integration..."
    
    # Check if Ollama is accessible
    if ! check_ollama_connectivity; then
        log_error "Cannot proceed without Ollama connectivity"
        exit 1
    fi
    
    # Create backup of existing config
    backup_config
    
    # Generate new configuration
    generate_config
    generate_env_file
    
    # Test the configuration
    if test_configuration; then
        show_summary
        log_success "AICleaner configuration completed successfully!"
    else
        log_error "Configuration test failed. Please check the settings."
        exit 1
    fi
}

# Handle command line arguments
case "${1:-configure}" in
    "configure")
        main
        ;;
    "test")
        test_configuration
        ;;
    "backup")
        backup_config
        ;;
    "summary")
        show_summary
        ;;
    *)
        echo "Usage: $0 {configure|test|backup|summary}"
        echo "  configure - Configure AICleaner for Ollama (default)"
        echo "  test      - Test current configuration"
        echo "  backup    - Create backup of current configuration"
        echo "  summary   - Show configuration summary"
        exit 1
        ;;
esac
