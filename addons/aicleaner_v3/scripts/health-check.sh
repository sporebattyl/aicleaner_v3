#!/bin/bash
# Health check script for Ollama container
# Used by Docker health checks and monitoring

set -e

# Configuration
OLLAMA_API="http://localhost:11434"
TIMEOUT=10
REQUIRED_MODELS=("llava:13b" "mistral:7b")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "[INFO] $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if Ollama API is responding
check_api_health() {
    log_info "Checking Ollama API health..."
    
    if curl -s -f --max-time $TIMEOUT "$OLLAMA_API/api/tags" >/dev/null 2>&1; then
        log_success "Ollama API is responding"
        return 0
    else
        log_error "Ollama API is not responding"
        return 1
    fi
}

# Check if required models are available
check_models() {
    log_info "Checking required models..."
    
    local available_models
    available_models=$(curl -s --max-time $TIMEOUT "$OLLAMA_API/api/tags" 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    if [ -z "$available_models" ]; then
        log_error "Could not retrieve model list"
        return 1
    fi
    
    local missing_models=()
    for model in "${REQUIRED_MODELS[@]}"; do
        if echo "$available_models" | grep -q "$model"; then
            log_info "✓ Model $model is available"
        else
            missing_models+=("$model")
        fi
    done
    
    if [ ${#missing_models[@]} -eq 0 ]; then
        log_success "All required models are available"
        return 0
    else
        log_warning "Missing models: ${missing_models[*]}"
        # Don't fail health check for missing models, just warn
        return 0
    fi
}

# Check system resources
check_resources() {
    log_info "Checking system resources..."
    
    # Check memory usage
    local memory_usage
    memory_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    
    if (( $(echo "$memory_usage > 90" | bc -l) )); then
        log_warning "High memory usage: ${memory_usage}%"
    else
        log_info "Memory usage: ${memory_usage}%"
    fi
    
    # Check disk space for models
    local disk_usage
    disk_usage=$(df /data 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//' || echo "0")
    
    if [ "$disk_usage" -gt 90 ]; then
        log_warning "High disk usage: ${disk_usage}%"
    else
        log_info "Disk usage: ${disk_usage}%"
    fi
    
    return 0
}

# Test model inference
test_inference() {
    log_info "Testing model inference..."
    
    # Test with a simple text model if available
    local test_model=""
    for model in "mistral:7b" "llama2:7b"; do
        if curl -s --max-time $TIMEOUT "$OLLAMA_API/api/tags" | grep -q "$model"; then
            test_model="$model"
            break
        fi
    done
    
    if [ -z "$test_model" ]; then
        log_warning "No text models available for inference test"
        return 0
    fi
    
    log_info "Testing inference with $test_model..."
    
    local response
    response=$(curl -s --max-time 30 -X POST "$OLLAMA_API/api/generate" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$test_model\",\"prompt\":\"Hello\",\"stream\":false}" \
        2>/dev/null | grep -o '"response":"[^"]*"' | cut -d'"' -f4 || echo "")
    
    if [ -n "$response" ]; then
        log_success "Inference test successful (response length: ${#response} chars)"
        return 0
    else
        log_warning "Inference test failed or timed out"
        return 0  # Don't fail health check for inference issues
    fi
}

# Main health check function
main_health_check() {
    local exit_code=0
    
    log_info "Starting Ollama health check..."
    
    # Check API health (critical)
    if ! check_api_health; then
        exit_code=1
    fi
    
    # Check models (warning only)
    check_models
    
    # Check resources (warning only)
    check_resources
    
    # Test inference (warning only)
    test_inference
    
    if [ $exit_code -eq 0 ]; then
        log_success "Ollama health check passed"
        echo "healthy"
    else
        log_error "Ollama health check failed"
        echo "unhealthy"
    fi
    
    return $exit_code
}

# Quick health check for Docker
quick_health_check() {
    if curl -s -f --max-time 5 "$OLLAMA_API/api/tags" >/dev/null 2>&1; then
        echo "healthy"
        return 0
    else
        echo "unhealthy"
        return 1
    fi
}

# Main execution
case "${1:-full}" in
    "full")
        main_health_check
        ;;
    "quick")
        quick_health_check
        ;;
    "api")
        check_api_health
        ;;
    "models")
        check_models
        ;;
    "resources")
        check_resources
        ;;
    "inference")
        test_inference
        ;;
    *)
        echo "Usage: $0 {full|quick|api|models|resources|inference}"
        echo "  full      - Complete health check (default)"
        echo "  quick     - Quick API check for Docker health"
        echo "  api       - Check API health only"
        echo "  models    - Check model availability"
        echo "  resources - Check system resources"
        echo "  inference - Test model inference"
        exit 1
        ;;
esac
