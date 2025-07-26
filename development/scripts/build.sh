#!/bin/bash
# Build Script for AICleaner v3 Home Assistant Add-on
# Builds multi-architecture Docker images with proper tagging

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REGISTRY="ghcr.io/drewcifer"
IMAGE_NAME="aicleaner_v3"

# Functions
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

show_help() {
    cat << EOF
AICleaner v3 Build Script

Usage: $0 [options]

Options:
  --arch <arch>           - Build for specific architecture (aarch64, amd64, armv7, armhf, i386)
  --all                   - Build for all architectures
  --push                  - Push images to registry
  --latest                - Tag as latest
  --no-cache              - Don't use build cache
  --dry-run               - Show what would be done without building
  -h, --help              - Show this help message
  
Examples:
  $0 --arch amd64                    # Build for amd64 only
  $0 --all --push                    # Build all architectures and push
  $0 --arch aarch64 --latest         # Build aarch64 and tag as latest
  $0 --all --push --latest           # Build all, push, and tag as latest
EOF
}

get_version() {
    # Get version from config.yaml
    if [[ -f "$PROJECT_ROOT/config.yaml" ]]; then
        python3 -c "import yaml; print(yaml.safe_load(open('$PROJECT_ROOT/config.yaml'))['version'])"
    else
        echo "unknown"
    fi
}

setup_buildx() {
    log_info "Setting up Docker Buildx..."
    
    # Create buildx builder if it doesn't exist
    if ! docker buildx ls | grep -q "aicleaner-builder"; then
        docker buildx create --name aicleaner-builder --driver docker-container --use
    else
        docker buildx use aicleaner-builder
    fi
    
    # Bootstrap the builder
    docker buildx inspect --bootstrap
    
    log_success "Docker Buildx ready"
}

build_architecture() {
    local arch="$1"
    local version="$2"
    local push="$3"
    local latest="$4"
    local no_cache="$5"
    local dry_run="$6"
    
    log_info "Building for $arch..."
    
    # Map architecture names for Docker
    local docker_platform=""
    case "$arch" in
        aarch64)
            docker_platform="linux/arm64"
            ;;
        amd64)
            docker_platform="linux/amd64"
            ;;
        armv7)
            docker_platform="linux/arm/v7"
            ;;
        armhf)
            docker_platform="linux/arm/v6"
            ;;
        i386)
            docker_platform="linux/386"
            ;;
        *)
            log_error "Unsupported architecture: $arch"
            return 1
            ;;
    esac
    
    # Build command
    local build_cmd="docker buildx build"
    build_cmd="$build_cmd --platform $docker_platform"
    build_cmd="$build_cmd --build-arg BUILD_ARCH=$arch"
    build_cmd="$build_cmd --build-arg BUILD_VERSION=$version"
    build_cmd="$build_cmd --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    build_cmd="$build_cmd --build-arg VCS_REF=$(git rev-parse HEAD)"
    build_cmd="$build_cmd -f Dockerfile"
    
    # Add cache options
    if [[ "$no_cache" == "true" ]]; then
        build_cmd="$build_cmd --no-cache"
    fi
    
    # Add tags
    local tags=""
    tags="$tags -t $REGISTRY/$IMAGE_NAME-$arch:$version"
    
    if [[ "$latest" == "true" ]]; then
        tags="$tags -t $REGISTRY/$IMAGE_NAME-$arch:latest"
    fi
    
    build_cmd="$build_cmd $tags"
    
    # Add push option
    if [[ "$push" == "true" ]]; then
        build_cmd="$build_cmd --push"
    else
        build_cmd="$build_cmd --load"
    fi
    
    # Add build context
    build_cmd="$build_cmd $PROJECT_ROOT"
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would execute: $build_cmd"
        return 0
    fi
    
    # Execute build
    if eval "$build_cmd"; then
        log_success "Built $arch successfully"
        return 0
    else
        log_error "Failed to build $arch"
        return 1
    fi
}

create_manifest() {
    local version="$1"
    local architectures=("$@")
    local push="$2"
    local latest="$3"
    local dry_run="$4"
    
    # Remove first 4 parameters to get architectures
    shift 4
    local archs=("$@")
    
    log_info "Creating manifest for version $version..."
    
    # Create manifest for version tag
    local manifest_cmd="docker manifest create $REGISTRY/$IMAGE_NAME:$version"
    for arch in "${archs[@]}"; do
        manifest_cmd="$manifest_cmd $REGISTRY/$IMAGE_NAME-$arch:$version"
    done
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would create manifest: $manifest_cmd"
        if [[ "$push" == "true" ]]; then
            log_info "DRY RUN: Would push manifest: docker manifest push $REGISTRY/$IMAGE_NAME:$version"
        fi
        return 0
    fi
    
    # Execute manifest creation
    if eval "$manifest_cmd"; then
        if [[ "$push" == "true" ]]; then
            docker manifest push "$REGISTRY/$IMAGE_NAME:$version"
        fi
        log_success "Created manifest for $version"
    else
        log_error "Failed to create manifest for $version"
        return 1
    fi
    
    # Create manifest for latest tag if requested
    if [[ "$latest" == "true" ]]; then
        local latest_manifest_cmd="docker manifest create $REGISTRY/$IMAGE_NAME:latest"
        for arch in "${archs[@]}"; do
            latest_manifest_cmd="$latest_manifest_cmd $REGISTRY/$IMAGE_NAME-$arch:latest"
        done
        
        if eval "$latest_manifest_cmd"; then
            if [[ "$push" == "true" ]]; then
                docker manifest push "$REGISTRY/$IMAGE_NAME:latest"
            fi
            log_success "Created latest manifest"
        else
            log_error "Failed to create latest manifest"
            return 1
        fi
    fi
}

validate_environment() {
    log_info "Validating build environment..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        exit 1
    fi
    
    # Check if buildx is available
    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx is required but not available"
        exit 1
    fi
    
    # Check if we're in the project root
    if [[ ! -f "$PROJECT_ROOT/config.yaml" ]]; then
        log_error "config.yaml not found. Please run from project root."
        exit 1
    fi
    
    # Check if Dockerfile exists
    if [[ ! -f "$PROJECT_ROOT/Dockerfile" ]]; then
        log_error "Dockerfile not found"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

# Main script logic
main() {
    cd "$PROJECT_ROOT"
    
    # Parse command line arguments
    architectures=()
    all_architectures=("aarch64" "amd64" "armv7" "armhf" "i386")
    push="false"
    latest="false"
    no_cache="false"
    dry_run="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --arch)
                architectures+=("$2")
                shift 2
                ;;
            --all)
                architectures=("${all_architectures[@]}")
                shift
                ;;
            --push)
                push="true"
                shift
                ;;
            --latest)
                latest="true"
                shift
                ;;
            --no-cache)
                no_cache="true"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Default to amd64 if no architecture specified
    if [[ ${#architectures[@]} -eq 0 ]]; then
        architectures=("amd64")
    fi
    
    # Validate environment
    validate_environment
    
    # Get version
    version=$(get_version)
    log_info "Building version: $version"
    
    # Setup buildx
    if [[ "$dry_run" != "true" ]]; then
        setup_buildx
    fi
    
    # Build each architecture
    build_failures=0
    for arch in "${architectures[@]}"; do
        if ! build_architecture "$arch" "$version" "$push" "$latest" "$no_cache" "$dry_run"; then
            ((build_failures++))
        fi
    done
    
    # Check if any builds failed
    if [[ $build_failures -gt 0 ]]; then
        log_error "$build_failures build(s) failed"
        exit 1
    fi
    
    # Create manifest if building multiple architectures and pushing
    if [[ ${#architectures[@]} -gt 1 && "$push" == "true" ]]; then
        create_manifest "$version" "$push" "$latest" "$dry_run" "${architectures[@]}"
    fi
    
    log_success "Build completed successfully"
    
    # Show summary
    log_info "Build Summary:"
    log_info "  Version: $version"
    log_info "  Architectures: ${architectures[*]}"
    log_info "  Push: $push"
    log_info "  Latest: $latest"
    log_info "  No Cache: $no_cache"
    
    if [[ "$push" == "true" ]]; then
        log_info "Images pushed to:"
        for arch in "${architectures[@]}"; do
            log_info "  $REGISTRY/$IMAGE_NAME-$arch:$version"
            if [[ "$latest" == "true" ]]; then
                log_info "  $REGISTRY/$IMAGE_NAME-$arch:latest"
            fi
        done
        
        if [[ ${#architectures[@]} -gt 1 ]]; then
            log_info "  $REGISTRY/$IMAGE_NAME:$version (manifest)"
            if [[ "$latest" == "true" ]]; then
                log_info "  $REGISTRY/$IMAGE_NAME:latest (manifest)"
            fi
        fi
    fi
}

# Run main function
main "$@"