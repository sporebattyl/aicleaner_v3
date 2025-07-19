#!/bin/bash
# Docker configuration validation script for AICleaner v3

set -euo pipefail

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

# Function to validate Dockerfile syntax
validate_dockerfile() {
    local dockerfile_path="$1"
    
    log_info "Validating Dockerfile syntax: $dockerfile_path"
    
    # Check if file exists
    if [[ ! -f "$dockerfile_path" ]]; then
        log_error "Dockerfile not found: $dockerfile_path"
        return 1
    fi
    
    # Basic syntax validation
    local errors=0
    
    # Check for required FROM statements
    if ! grep -q "^FROM.*as builder" "$dockerfile_path"; then
        log_error "Missing builder stage FROM statement"
        ((errors++))
    fi
    
    if ! grep -q "^FROM.*as production" "$dockerfile_path"; then
        log_error "Missing production stage FROM statement"
        ((errors++))
    fi
    
    # Check for WORKDIR
    if ! grep -q "^WORKDIR" "$dockerfile_path"; then
        log_warning "No WORKDIR specified"
    fi
    
    # Check for EXPOSE
    if ! grep -q "^EXPOSE 8000" "$dockerfile_path"; then
        log_error "Missing EXPOSE 8000 statement"
        ((errors++))
    fi
    
    # Check for CMD
    if ! grep -q "^CMD" "$dockerfile_path"; then
        log_error "Missing CMD statement"
        ((errors++))
    fi
    
    # Check for HEALTHCHECK
    if ! grep -q "^HEALTHCHECK" "$dockerfile_path"; then
        log_warning "No HEALTHCHECK specified"
    fi
    
    # Check for security best practices
    if grep -q "^USER root" "$dockerfile_path"; then
        log_warning "Found explicit USER root - consider non-root user"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Dockerfile syntax validation passed"
        return 0
    else
        log_error "Dockerfile validation failed with $errors errors"
        return 1
    fi
}

# Function to validate docker-compose files
validate_compose() {
    local compose_file="$1"
    
    log_info "Validating docker-compose file: $compose_file"
    
    if [[ ! -f "$compose_file" ]]; then
        log_error "Docker Compose file not found: $compose_file"
        return 1
    fi
    
    # Check for required services
    local required_services=("aicleaner" "redis" "prometheus" "grafana")
    local errors=0
    
    for service in "${required_services[@]}"; do
        if ! grep -q "^  $service:" "$compose_file"; then
            log_error "Missing required service: $service"
            ((errors++))
        fi
    done
    
    # Check for networks
    if ! grep -q "^networks:" "$compose_file"; then
        log_warning "No networks defined"
    fi
    
    # Check for volumes
    if ! grep -q "^volumes:" "$compose_file"; then
        log_warning "No volumes defined"
    fi
    
    # Check for health checks
    if ! grep -q "healthcheck:" "$compose_file"; then
        log_warning "No health checks defined"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Docker Compose validation passed"
        return 0
    else
        log_error "Docker Compose validation failed with $errors errors"
        return 1
    fi
}

# Function to validate .dockerignore
validate_dockerignore() {
    local dockerignore_path="$1"
    
    log_info "Validating .dockerignore: $dockerignore_path"
    
    if [[ ! -f "$dockerignore_path" ]]; then
        log_warning ".dockerignore not found - build context may be large"
        return 0
    fi
    
    # Check for common patterns
    local important_patterns=(".git/" "*.md" "__pycache__/" "*.pyc" ".pytest_cache/")
    local warnings=0
    
    for pattern in "${important_patterns[@]}"; do
        if ! grep -q "$pattern" "$dockerignore_path"; then
            log_warning "Consider adding pattern to .dockerignore: $pattern"
            ((warnings++))
        fi
    done
    
    log_success ".dockerignore validation completed with $warnings suggestions"
    return 0
}

# Function to validate build configuration
validate_build_config() {
    local build_yaml="$1"
    
    log_info "Validating build configuration: $build_yaml"
    
    if [[ ! -f "$build_yaml" ]]; then
        log_warning "build.yaml not found - multi-arch builds may not work"
        return 0
    fi
    
    # Check for required architectures
    local required_archs=("amd64" "aarch64" "armv7")
    local errors=0
    
    for arch in "${required_archs[@]}"; do
        if ! grep -q "$arch:" "$build_yaml"; then
            log_error "Missing architecture in build.yaml: $arch"
            ((errors++))
        fi
    done
    
    if [[ $errors -eq 0 ]]; then
        log_success "Build configuration validation passed"
        return 0
    else
        log_error "Build configuration validation failed with $errors errors"
        return 1
    fi
}

# Function to check file sizes
check_file_sizes() {
    log_info "Checking configuration file sizes..."
    
    local large_files=()
    
    # Check for large files that shouldn't be in build context
    while IFS= read -r -d '' file; do
        local size
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        if [[ $size -gt 10485760 ]]; then  # 10MB
            large_files+=("$file ($(( size / 1048576 ))MB)")
        fi
    done < <(find . -type f -not -path "./.git/*" -not -path "./data/*" -not -path "./logs/*" -print0 2>/dev/null)
    
    if [[ ${#large_files[@]} -gt 0 ]]; then
        log_warning "Large files found in build context:"
        printf '  %s\n' "${large_files[@]}"
        log_warning "Consider adding these to .dockerignore"
    else
        log_success "No large files found in build context"
    fi
}

# Function to validate requirements.txt
validate_requirements() {
    local req_file="addons/aicleaner_v3/requirements.txt"
    
    log_info "Validating requirements.txt"
    
    if [[ ! -f "$req_file" ]]; then
        log_error "requirements.txt not found: $req_file"
        return 1
    fi
    
    # Check for version pinning
    local unpinned=0
    while IFS= read -r line; do
        if [[ $line =~ ^[a-zA-Z] ]] && [[ ! $line =~ "[=><]" ]]; then
            log_warning "Unpinned dependency: $line"
            ((unpinned++))
        fi
    done < "$req_file"
    
    if [[ $unpinned -eq 0 ]]; then
        log_success "All dependencies are properly pinned"
    else
        log_warning "$unpinned dependencies are not pinned"
    fi
    
    return 0
}

# Main validation function
main() {
    local validation_errors=0
    
    log_info "Starting Docker configuration validation for AICleaner v3"
    echo ""
    
    # Validate Dockerfile
    if ! validate_dockerfile "Dockerfile"; then
        ((validation_errors++))
    fi
    echo ""
    
    # Validate docker-compose files
    local compose_files=("docker-compose.yml" "docker-compose.prod.yml" "docker-compose.dev.yml")
    for compose_file in "${compose_files[@]}"; do
        if [[ -f "$compose_file" ]]; then
            if ! validate_compose "$compose_file"; then
                ((validation_errors++))
            fi
        else
            log_warning "Docker Compose file not found: $compose_file"
        fi
        echo ""
    done
    
    # Validate .dockerignore
    validate_dockerignore ".dockerignore"
    echo ""
    
    # Validate build configuration
    validate_build_config "build.yaml"
    echo ""
    
    # Validate requirements
    validate_requirements
    echo ""
    
    # Check file sizes
    check_file_sizes
    echo ""
    
    # Summary
    if [[ $validation_errors -eq 0 ]]; then
        log_success "All Docker configuration validations passed!"
        echo ""
        log_info "Ready for Docker build and deployment"
        return 0
    else
        log_error "Docker configuration validation failed with $validation_errors errors"
        echo ""
        log_info "Please fix the errors before building"
        return 1
    fi
}

# Run main function
main "$@"