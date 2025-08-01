#!/bin/bash
# Docker configuration validation script for AICleaner v3
# Validates Home Assistant addon Docker setup and related configurations

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

# Function to validate Home Assistant addon Dockerfile
validate_dockerfile() {
    local dockerfile_path="$1"
    
    log_info "Validating Home Assistant addon Dockerfile: $dockerfile_path"
    
    # Check if file exists
    if [[ ! -f "$dockerfile_path" ]]; then
        log_error "Dockerfile not found: $dockerfile_path"
        return 1
    fi
    
    local errors=0
    
    # Check for required HA addon elements
    if ! grep -q "ARG BUILD_FROM" "$dockerfile_path"; then
        log_error "Missing ARG BUILD_FROM statement (required for HA addons)"
        ((errors++))
    fi
    
    if ! grep -q "FROM.*BUILD_FROM" "$dockerfile_path"; then
        log_error "Missing FROM \${BUILD_FROM} statement"
        ((errors++))
    fi
    
    # Check for WORKDIR
    if ! grep -q "^WORKDIR" "$dockerfile_path"; then
        log_warning "No WORKDIR specified"
    fi
    
    # Check for CMD or ENTRYPOINT
    if ! grep -q "^CMD\|^ENTRYPOINT" "$dockerfile_path"; then
        log_error "Missing CMD or ENTRYPOINT statement"
        ((errors++))
    fi
    
    # Check for HEALTHCHECK (recommended for HA addons)
    if ! grep -q "^HEALTHCHECK" "$dockerfile_path"; then
        log_info "HEALTHCHECK found - good for monitoring"
    else
        log_warning "No HEALTHCHECK specified (recommended for HA addons)"
    fi
    
    # Check for security best practices
    if grep -q "^USER root" "$dockerfile_path"; then
        log_warning "Found explicit USER root - consider non-root user if possible"
    fi
    
    # Check for Python dependencies installation
    if ! grep -q "pip.*install" "$dockerfile_path"; then
        log_warning "No pip install found - ensure dependencies are installed"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log_success "Dockerfile validation passed"
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
    
    local errors=0
    
    # Check for services section
    if ! grep -q "^services:" "$compose_file"; then
        log_error "Missing services section"
        ((errors++))
    fi
    
    # Check for aicleaner service
    if ! grep -q "aicleaner:" "$compose_file"; then
        log_warning "No aicleaner service found (checking for main app service)"
    fi
    
    # Check for networks (good practice)
    if grep -q "^networks:" "$compose_file"; then
        log_success "Networks section found"
    else
        log_info "No custom networks defined (using default)"
    fi
    
    # Check for volumes (good practice)
    if grep -q "^volumes:" "$compose_file"; then
        log_success "Volumes section found"
    else
        log_info "No named volumes defined"
    fi
    
    # Check for health checks in compose
    if grep -q "healthcheck:" "$compose_file"; then
        log_success "Health checks found in compose file"
    else
        log_warning "No health checks defined in compose"
    fi
    
    # Check for restart policies
    if grep -q "restart:" "$compose_file"; then
        log_success "Restart policies found"
    else
        log_warning "No restart policies defined"
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
        log_error ".dockerignore not found - build context may be large"
        return 1
    fi
    
    # Check for common patterns that should be ignored
    local important_patterns=(".git/" "*.md" "__pycache__/" "*.pyc" ".pytest_cache/" "tests/" ".github/")
    local missing=0
    
    for pattern in "${important_patterns[@]}"; do
        if ! grep -q "$pattern" "$dockerignore_path"; then
            log_warning "Consider adding pattern to .dockerignore: $pattern"
            ((missing++))
        fi
    done
    
    if [[ $missing -eq 0 ]]; then
        log_success ".dockerignore validation passed - all recommended patterns found"
    else
        log_info ".dockerignore validation completed with $missing suggestions"
    fi
    
    return 0
}

# Function to validate build configuration for HA addon
validate_build_config() {
    local build_yaml="$1"
    
    log_info "Validating Home Assistant addon build configuration: $build_yaml"
    
    if [[ ! -f "$build_yaml" ]]; then
        log_warning "build.yaml not found - multi-arch builds may not work for HA addon"
        return 0
    fi
    
    # Check for HA addon specific architectures
    local ha_archs=("amd64" "aarch64" "armv7")
    local missing_archs=0
    
    for arch in "${ha_archs[@]}"; do
        if ! grep -q "$arch" "$build_yaml"; then
            log_warning "Architecture not found in build.yaml: $arch"
            ((missing_archs++))
        fi
    done
    
    # Check for build_from section (HA addon specific)
    if grep -q "build_from:" "$build_yaml"; then
        log_success "build_from section found (HA addon compatible)"
    else
        log_warning "No build_from section found (may be needed for HA addon)"
    fi
    
    if [[ $missing_archs -eq 0 ]]; then
        log_success "Build configuration validation passed"
        return 0
    else
        log_info "Build configuration validation completed with $missing_archs missing architectures"
        return 0
    fi
}

# Function to check file sizes in build context
check_file_sizes() {
    log_info "Checking build context file sizes..."
    
    local large_files=()
    local total_size=0
    
    # Check for large files that shouldn't be in build context
    while IFS= read -r -d '' file; do
        local size
        size=$(stat -c%s "$file" 2>/dev/null || echo 0)
        total_size=$((total_size + size))
        if [[ $size -gt 10485760 ]]; then  # 10MB
            large_files+=("$file ($(( size / 1048576 ))MB)")
        fi
    done < <(find . -type f -not -path "./.git/*" -not -path "./data/*" -not -path "./logs/*" -print0 2>/dev/null)
    
    # Convert total size to MB for display
    local total_mb=$((total_size / 1048576))
    
    log_info "Total build context size: ${total_mb}MB"
    
    if [[ ${#large_files[@]} -gt 0 ]]; then
        log_warning "Large files found in build context:"
        printf '  %s\n' "${large_files[@]}"
        log_warning "Consider adding these to .dockerignore to reduce build time"
    else
        log_success "No excessively large files found in build context"
    fi
    
    # Warn if build context is very large
    if [[ $total_mb -gt 100 ]]; then
        log_warning "Build context is quite large (${total_mb}MB) - consider optimizing .dockerignore"
    fi
}

# Function to validate requirements.txt
validate_requirements() {
    local req_file="requirements.txt"
    
    log_info "Validating requirements.txt"
    
    if [[ ! -f "$req_file" ]]; then
        log_error "requirements.txt not found in current directory"
        return 1
    fi
    
    # Check for version pinning
    local unpinned=0
    local total_deps=0
    
    while IFS= read -r line; do
        # Skip comments and empty lines
        if [[ $line =~ ^[[:space:]]*# ]] || [[ -z "${line// }" ]]; then
            continue
        fi
        
        # Check if it's a dependency line
        if [[ $line =~ ^[a-zA-Z0-9_-]+ ]]; then
            ((total_deps++))
            if [[ ! $line =~ [=\>\<] ]]; then
                log_warning "Unpinned dependency: $line"
                ((unpinned++))
            fi
        fi
    done < "$req_file"
    
    log_info "Found $total_deps dependencies"
    
    if [[ $unpinned -eq 0 ]]; then
        log_success "All dependencies are properly pinned"
    else
        log_warning "$unpinned out of $total_deps dependencies are not pinned"
    fi
    
    return 0
}

# Function to validate overall Docker setup
validate_docker_setup() {
    log_info "Performing basic Docker setup validation..."
    
    # Check if we can parse Dockerfile without Docker
    if command -v docker &> /dev/null; then
        log_info "Docker is available - could perform advanced validation"
    else
        log_warning "Docker not available - performing syntax-only validation"
    fi
    
    # Check for config.yaml (HA addon requirement)
    if [[ -f "config.yaml" ]]; then
        log_success "config.yaml found (required for HA addon)"
    else
        log_warning "config.yaml not found (required for HA addon publication)"
    fi
    
    # Check for run.sh script (common HA addon pattern)
    if [[ -f "run.sh" ]]; then
        log_success "run.sh script found"
        if [[ -x "run.sh" ]]; then
            log_success "run.sh is executable"
        else
            log_warning "run.sh is not executable"
        fi
    else
        log_info "No run.sh script found (not required but common for HA addons)"
    fi
}

# Main validation function
main() {
    local validation_errors=0
    
    log_info "Starting Docker configuration validation for AICleaner v3 (Home Assistant Addon)"
    echo ""
    
    # Validate overall Docker setup
    validate_docker_setup
    echo ""
    
    # Validate Dockerfile
    if ! validate_dockerfile "Dockerfile"; then
        ((validation_errors++))
    fi
    echo ""
    
    # Validate docker-compose files (if any exist)
    local compose_files_found=false
    for compose_file in docker-compose*.yml; do
        if [[ -f "$compose_file" ]]; then
            compose_files_found=true
            if ! validate_compose "$compose_file"; then
                ((validation_errors++))
            fi
            echo ""
        fi
    done
    
    if [[ "$compose_files_found" == false ]]; then
        log_info "No docker-compose files found (not required for HA addon)"
        echo ""
    fi
    
    # Validate .dockerignore
    if ! validate_dockerignore ".dockerignore"; then
        ((validation_errors++))
    fi
    echo ""
    
    # Validate build configuration
    validate_build_config "build.yaml"
    echo ""
    
    # Validate requirements
    if ! validate_requirements; then
        ((validation_errors++))
    fi
    echo ""
    
    # Check file sizes
    check_file_sizes
    echo ""
    
    # Summary
    if [[ $validation_errors -eq 0 ]]; then
        log_success "All critical Docker configuration validations passed!"
        echo ""
        log_info "Docker configuration is ready for Home Assistant addon deployment"
        return 0
    else
        log_error "Docker configuration validation failed with $validation_errors critical errors"
        echo ""
        log_info "Please fix the critical errors before proceeding with deployment"
        return 1
    fi
}

# Run main function
main "$@"