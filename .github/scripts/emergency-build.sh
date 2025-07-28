#!/bin/bash

# Emergency Build Script for AICleaner V3
# Use this script when the automated GitHub Actions build system fails
# This script provides manual build capabilities with comprehensive error handling

set -e

# Configuration
REGISTRY="${REGISTRY:-ghcr.io}"
REPO_OWNER="${GITHUB_REPOSITORY_OWNER:-sporebattyl}"
ADDON_SLUG="aicleaner_v3"
BUILD_DATE=$(date +%Y%m%d-%H%M%S)
EMERGENCY_TAG="emergency-$BUILD_DATE"

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

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

show_help() {
    cat << EOF
Emergency Build Script for AICleaner V3

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -a, --arch ARCH         Build specific architecture (amd64, aarch64, armhf, armv7)
    -t, --tag TAG           Custom tag (default: emergency-YYYYMMDD-HHMMSS)
    -r, --registry URL      Container registry (default: ghcr.io)
    -p, --push              Push to registry after build
    -l, --load              Load image locally after build
    -c, --clean             Clean Docker environment before build
    -v, --validate          Validate configuration before build
    -h, --help              Show this help message

EXAMPLES:
    # Build single architecture locally
    $0 --arch amd64 --load

    # Build and push specific architecture
    $0 --arch amd64 --push --tag v1.1.0-hotfix

    # Build all architectures and push
    $0 --push

    # Emergency build with full validation
    $0 --validate --clean --push

ENVIRONMENT VARIABLES:
    REGISTRY                Container registry URL
    GITHUB_REPOSITORY_OWNER Repository owner
    DOCKER_BUILDKIT         Enable BuildKit (set to 1)
    EMERGENCY_BUILD_MODE    Enable emergency mode flags

EOF
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    if ! command -v yq &> /dev/null; then
        missing_deps+=("yq")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running or accessible"
        exit 1
    fi
    
    log_success "All dependencies available"
}

validate_configuration() {
    log_info "Validating configuration..."
    
    # Check if we're in the right directory
    if [ ! -f "aicleaner_v3/config.yaml" ]; then
        log_error "config.yaml not found. Please run this script from the repository root."
        exit 1
    fi
    
    cd aicleaner_v3
    
    # Validate YAML syntax
    if ! yq eval '.' config.yaml >/dev/null 2>&1; then
        log_error "config.yaml has invalid YAML syntax"
        exit 1
    fi
    
    # Check required fields
    local name=$(yq eval '.name' config.yaml)
    local version=$(yq eval '.version' config.yaml)
    local slug=$(yq eval '.slug' config.yaml)
    local arch_count=$(yq eval '.arch | length' config.yaml)
    
    if [ "$name" = "null" ] || [ -z "$name" ]; then
        log_error "Missing or invalid 'name' field in config.yaml"
        exit 1
    fi
    
    if [ "$version" = "null" ] || [ -z "$version" ]; then
        log_error "Missing or invalid 'version' field in config.yaml"
        exit 1
    fi
    
    if [ "$slug" = "null" ] || [ -z "$slug" ]; then
        log_error "Missing or invalid 'slug' field in config.yaml"
        exit 1
    fi
    
    if [ "$arch_count" -eq 0 ]; then
        log_error "No architectures defined in config.yaml"
        exit 1
    fi
    
    # Check Dockerfile
    if [ ! -f "Dockerfile" ]; then
        log_error "Dockerfile not found in aicleaner_v3 directory"
        exit 1
    fi
    
    # Basic Dockerfile validation
    if ! grep -q "^FROM " Dockerfile; then
        log_error "Dockerfile missing FROM instruction"
        exit 1
    fi
    
    log_success "Configuration validation passed"
    log_info "Addon: $name v$version"
    log_info "Slug: $slug"
    log_info "Architectures: $(yq eval '.arch[]' config.yaml | tr '\n' ' ')"
    
    cd ..
}

clean_docker_environment() {
    log_info "Cleaning Docker environment..."
    
    # Remove dangling images
    docker image prune -f >/dev/null 2>&1 || true
    
    # Remove stopped containers
    docker container prune -f >/dev/null 2>&1 || true
    
    # Remove build cache
    docker builder prune -f >/dev/null 2>&1 || true
    
    log_success "Docker environment cleaned"
}

get_supported_architectures() {
    cd aicleaner_v3
    yq eval '.arch[]' config.yaml | tr '\n' ' '
    cd ..
}

build_architecture() {
    local arch="$1"
    local tag="$2"
    local push="$3"
    local load="$4"
    
    log_info "Building for architecture: $arch"
    
    cd aicleaner_v3
    
    # Prepare build arguments
    local build_args=(
        "--platform" "linux/$arch"
        "--tag" "$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag-$arch"
        "--tag" "$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$EMERGENCY_TAG-$arch"
    )
    
    # Add push flag if requested
    if [ "$push" = "true" ]; then
        build_args+=("--push")
    fi
    
    # Add load flag if requested (mutually exclusive with push)
    if [ "$load" = "true" ] && [ "$push" != "true" ]; then
        build_args+=("--load")
    fi
    
    # Enable BuildKit
    export DOCKER_BUILDKIT=1
    
    # Build the image
    log_info "Running: docker buildx build ${build_args[*]} ."
    
    if docker buildx build "${build_args[@]}" .; then
        log_success "Build completed for $arch"
        
        # Show image information
        if [ "$load" = "true" ] || [ "$push" != "true" ]; then
            local image_id=$(docker images --format "{{.ID}}" "$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag-$arch" | head -1)
            if [ -n "$image_id" ]; then
                local image_size=$(docker images --format "{{.Size}}" "$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag-$arch" | head -1)
                log_info "Image: $REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag-$arch"
                log_info "Size: $image_size"
                log_info "ID: $image_id"
            fi
        fi
        
        return 0
    else
        log_error "Build failed for $arch"
        return 1
    fi
    
    cd ..
}

test_built_image() {
    local arch="$1"
    local tag="$2"
    
    log_info "Testing built image for $arch..."
    
    local image_name="$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag-$arch"
    
    # Basic container startup test
    if timeout 30 docker run --rm --name "test-$arch-$$" \
        -e LOG_LEVEL=debug \
        "$image_name" /bin/sh -c "echo 'Container test successful' && sleep 2"; then
        log_success "Container test passed for $arch"
        return 0
    else
        log_error "Container test failed for $arch"
        return 1
    fi
}

build_multiarch_manifest() {
    local tag="$1"
    local architectures=($2)
    local push="$3"
    
    log_info "Creating multi-architecture manifest..."
    
    local manifest_name="$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag"
    local arch_images=()
    
    # Build list of architecture-specific images
    for arch in "${architectures[@]}"; do
        arch_images+=("$REGISTRY/$REPO_OWNER/$ADDON_SLUG:$tag-$arch")
    done
    
    # Create manifest
    if docker manifest create "$manifest_name" "${arch_images[@]}"; then
        log_success "Manifest created: $manifest_name"
        
        # Push manifest if requested
        if [ "$push" = "true" ]; then
            if docker manifest push "$manifest_name"; then
                log_success "Manifest pushed: $manifest_name"
            else
                log_error "Failed to push manifest: $manifest_name"
                return 1
            fi
        fi
        
        return 0
    else
        log_error "Failed to create manifest: $manifest_name"
        return 1
    fi
}

generate_build_report() {
    local tag="$1"
    local architectures=($2)
    local successful_builds=($3)
    local failed_builds=($4)
    
    log_info "Generating build report..."
    
    local report_file="emergency-build-report-$BUILD_DATE.json"
    
    cat > "$report_file" << EOF
{
  "emergency_build": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "tag": "$tag",
    "emergency_tag": "$EMERGENCY_TAG",
    "registry": "$REGISTRY",
    "repository": "$REPO_OWNER/$ADDON_SLUG"
  },
  "build_results": {
    "total_architectures": ${#architectures[@]},
    "successful_builds": ${#successful_builds[@]},
    "failed_builds": ${#failed_builds[@]},
    "success_rate": $(echo "scale=2; ${#successful_builds[@]} * 100 / ${#architectures[@]}" | bc -l 2>/dev/null || echo "0")
  },
  "architectures": {
    "requested": [$(printf '"%s",' "${architectures[@]}" | sed 's/,$//')]
  },
  "successful_builds": [$(printf '"%s",' "${successful_builds[@]}" | sed 's/,$//')]
  $([ ${#failed_builds[@]} -gt 0 ] && echo ', "failed_builds": ['"$(printf '"%s",' "${failed_builds[@]}" | sed 's/,$//')"']')
}
EOF
    
    log_success "Build report generated: $report_file"
    
    # Display summary
    echo ""
    echo "=== BUILD SUMMARY ==="
    echo "Tag: $tag"
    echo "Emergency Tag: $EMERGENCY_TAG"
    echo "Total Architectures: ${#architectures[@]}"
    echo "Successful: ${#successful_builds[@]}"
    echo "Failed: ${#failed_builds[@]}"
    
    if [ ${#successful_builds[@]} -gt 0 ]; then
        echo "Successful Builds: ${successful_builds[*]}"
    fi
    
    if [ ${#failed_builds[@]} -gt 0 ]; then
        echo "Failed Builds: ${failed_builds[*]}"
    fi
    echo "=================="
}

main() {
    local architectures=()
    local custom_tag=""
    local push_images=false
    local load_images=false
    local clean_environment=false
    local validate_config=false
    local test_images=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -a|--arch)
                architectures+=("$2")
                shift 2
                ;;
            -t|--tag)
                custom_tag="$2"
                shift 2
                ;;
            -r|--registry)
                REGISTRY="$2"
                shift 2
                ;;
            -p|--push)
                push_images=true
                shift
                ;;
            -l|--load)
                load_images=true
                shift
                ;;
            -c|--clean)
                clean_environment=true
                shift
                ;;
            -v|--validate)
                validate_config=true
                shift
                ;;
            --test)
                test_images=true
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
    
    echo "=== Emergency Build Script for AICleaner V3 ==="
    echo "Registry: $REGISTRY"
    echo "Repository: $REPO_OWNER/$ADDON_SLUG"
    echo "Build Date: $BUILD_DATE"
    echo ""
    
    # Check dependencies
    check_dependencies
    
    # Validate configuration if requested
    if [ "$validate_config" = true ]; then
        validate_configuration
    fi
    
    # Get architectures if not specified
    if [ ${#architectures[@]} -eq 0 ]; then
        log_info "No architectures specified, using all supported architectures"
        IFS=' ' read -ra architectures <<< "$(get_supported_architectures)"
    fi
    
    # Set tag
    local build_tag="${custom_tag:-$EMERGENCY_TAG}"
    
    log_info "Building architectures: ${architectures[*]}"
    log_info "Using tag: $build_tag"
    
    # Clean environment if requested
    if [ "$clean_environment" = true ]; then
        clean_docker_environment
    fi
    
    # Setup Docker buildx
    if ! docker buildx inspect emergency-builder >/dev/null 2>&1; then
        log_info "Creating Docker buildx builder..."
        docker buildx create --name emergency-builder --use >/dev/null 2>&1 || true
    else
        docker buildx use emergency-builder >/dev/null 2>&1 || true
    fi
    
    # Build each architecture
    local successful_builds=()
    local failed_builds=()
    
    for arch in "${architectures[@]}"; do
        echo ""
        if build_architecture "$arch" "$build_tag" "$push_images" "$load_images"; then
            successful_builds+=("$arch")
            
            # Test image if requested
            if [ "$test_images" = true ] && [ "$load_images" = true ]; then
                test_built_image "$arch" "$build_tag" || log_warn "Image test failed for $arch (non-critical)"
            fi
        else
            failed_builds+=("$arch")
        fi
    done
    
    # Create multi-arch manifest if multiple architectures built successfully
    if [ ${#successful_builds[@]} -gt 1 ] && [ "$push_images" = true ]; then
        echo ""
        build_multiarch_manifest "$build_tag" "${successful_builds[*]}" "$push_images"
    fi
    
    # Generate report
    echo ""
    generate_build_report "$build_tag" "${architectures[*]}" "${successful_builds[*]}" "${failed_builds[*]}"
    
    # Exit with appropriate code
    if [ ${#failed_builds[@]} -eq 0 ]; then
        log_success "Emergency build completed successfully!"
        exit 0
    elif [ ${#successful_builds[@]} -gt 0 ]; then
        log_warn "Emergency build completed with some failures"
        exit 1
    else
        log_error "Emergency build failed completely"
        exit 2
    fi
}

# Run main function with all arguments
main "$@"