#!/bin/bash
# Setup script for downloading and configuring Ollama models
# Used by AICleaner v3 Docker setup

set -e

# Configuration
MODELS_CONFIG="/config/models.json"
OLLAMA_API="http://localhost:11434"
MAX_RETRIES=3
RETRY_DELAY=10

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

# Check if Ollama server is running
check_ollama_server() {
    log_info "Checking Ollama server status..."
    
    for i in $(seq 1 30); do
        if curl -s -f "$OLLAMA_API/api/tags" >/dev/null 2>&1; then
            log_success "Ollama server is running"
            return 0
        fi
        log_info "Waiting for Ollama server... ($i/30)"
        sleep 2
    done
    
    log_error "Ollama server is not responding"
    return 1
}

# Download a model with retry logic
download_model() {
    local model_name="$1"
    local model_type="$2"
    local retries=0
    
    log_info "Downloading model: $model_name ($model_type)"
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if ollama pull "$model_name"; then
            log_success "Successfully downloaded $model_name"
            return 0
        else
            retries=$((retries + 1))
            log_warning "Failed to download $model_name (attempt $retries/$MAX_RETRIES)"
            if [ $retries -lt $MAX_RETRIES ]; then
                log_info "Retrying in $RETRY_DELAY seconds..."
                sleep $RETRY_DELAY
            fi
        fi
    done
    
    log_error "Failed to download $model_name after $MAX_RETRIES attempts"
    return 1
}

# Verify model is working
verify_model() {
    local model_name="$1"
    local model_type="$2"
    
    log_info "Verifying model: $model_name"
    
    if [ "$model_type" = "vision" ]; then
        # For vision models, just check if they're loaded
        if ollama list | grep -q "$model_name"; then
            log_success "Vision model $model_name is available"
            return 0
        fi
    else
        # For text models, test with a simple prompt
        local test_response
        test_response=$(ollama run "$model_name" "Hello" 2>/dev/null | head -1)
        if [ -n "$test_response" ]; then
            log_success "Text model $model_name is working (response: ${test_response:0:50}...)"
            return 0
        fi
    fi
    
    log_error "Model $model_name verification failed"
    return 1
}

# Main setup function
setup_models() {
    log_info "Starting model setup for AICleaner v3..."
    
    # Check if Ollama server is running
    if ! check_ollama_server; then
        exit 1
    fi
    
    # Define recommended models
    declare -A models=(
        ["llava:13b"]="vision"
        ["mistral:7b"]="text"
        ["llama2:7b"]="text"
    )
    
    local success_count=0
    local total_count=${#models[@]}
    
    # Download each model
    for model in "${!models[@]}"; do
        model_type="${models[$model]}"
        
        # Check if model already exists
        if ollama list | grep -q "$model"; then
            log_info "Model $model already exists, skipping download"
            verify_model "$model" "$model_type"
            success_count=$((success_count + 1))
            continue
        fi
        
        # Download and verify model
        if download_model "$model" "$model_type"; then
            if verify_model "$model" "$model_type"; then
                success_count=$((success_count + 1))
            fi
        fi
    done
    
    # Summary
    log_info "Model setup complete: $success_count/$total_count models ready"
    
    if [ $success_count -eq $total_count ]; then
        log_success "All recommended models are ready for AICleaner v3!"
        return 0
    elif [ $success_count -gt 0 ]; then
        log_warning "Some models failed to download, but AICleaner v3 can still function"
        return 0
    else
        log_error "No models were successfully downloaded"
        return 1
    fi
}

# Show current model status
show_model_status() {
    log_info "Current Ollama models:"
    ollama list || log_error "Failed to list models"
}

# Main execution
main() {
    case "${1:-setup}" in
        "setup")
            setup_models
            ;;
        "status")
            show_model_status
            ;;
        "verify")
            if [ -n "$2" ]; then
                verify_model "$2" "${3:-text}"
            else
                log_error "Usage: $0 verify <model_name> [model_type]"
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 {setup|status|verify}"
            echo "  setup  - Download and configure recommended models"
            echo "  status - Show current model status"
            echo "  verify - Verify a specific model"
            exit 1
            ;;
    esac
}

main "$@"
