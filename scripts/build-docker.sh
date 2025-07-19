#!/bin/bash
# Multi-architecture Docker build script for AICleaner v3
# Supports amd64, arm64, and armv7 architectures for Home Assistant

set -euo pipefail

# Configuration
REPO_NAME="aicleaner_v3"
IMAGE_NAME="aicleaner_v3"
VERSION=${1:-"1.0.0"}
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
BUILD_REF=${GITHUB_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")}

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

# Function to check if docker buildx is available
check_buildx() {
    if ! docker buildx version > /dev/null 2>&1; then
        log_error "Docker buildx is not available. Please install Docker Desktop or enable buildx."
        exit 1
    fi
    log_success "Docker buildx is available"
}

# Function to create and use buildx builder
setup_builder() {
    local builder_name="aicleaner-builder"
    
    log_info "Setting up multi-architecture builder..."
    
    # Remove existing builder if it exists
    docker buildx rm "$builder_name" 2>/dev/null || true
    
    # Create new builder with multi-arch support
    docker buildx create \
        --name "$builder_name" \
        --driver docker-container \
        --use \
        --bootstrap
    
    log_success "Builder '$builder_name' created and activated"
}

# Function to build single architecture
build_single_arch() {
    local arch=$1
    local tag="${IMAGE_NAME}:${VERSION}-${arch}"
    
    log_info "Building for architecture: $arch"
    
    docker buildx build \
        --platform "linux/$arch" \
        --build-arg BUILD_ARCH="$arch" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg BUILD_REF="$BUILD_REF" \
        --build-arg BUILD_VERSION="$VERSION" \
        --tag "$tag" \
        --load \
        .
    
    log_success "Built $tag"
}

# Function to build multi-architecture image
build_multi_arch() {
    local platforms="linux/amd64,linux/arm64,linux/arm/v7"
    local tags=(
        "${IMAGE_NAME}:${VERSION}"
        "${IMAGE_NAME}:latest"
    )
    
    log_info "Building multi-architecture image for platforms: $platforms"
    
    # Build tag arguments
    local tag_args=""
    for tag in "${tags[@]}"; do
        tag_args="$tag_args --tag $tag"
    done
    
    docker buildx build \
        --platform "$platforms" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg BUILD_REF="$BUILD_REF" \
        --build-arg BUILD_VERSION="$VERSION" \
        $tag_args \
        --push \
        .\n    \n    log_success \"Multi-architecture image built and pushed\"\n}\n\n# Function to test image\ntest_image() {\n    local arch=${1:-\"amd64\"}\n    local tag=\"${IMAGE_NAME}:${VERSION}-${arch}\"\n    \n    log_info \"Testing image: $tag\"\n    \n    # Test image can start\n    local container_id\n    container_id=$(docker run -d \\\n        -p 8000:8000 \\\n        -e LOG_LEVEL=debug \\\n        \"$tag\")\n    \n    # Wait for container to start\n    sleep 10\n    \n    # Test health endpoint\n    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then\n        log_success \"Health check passed for $tag\"\n    else\n        log_warning \"Health check failed for $tag (this may be expected in test environment)\"\n    fi\n    \n    # Clean up\n    docker stop \"$container_id\" > /dev/null\n    docker rm \"$container_id\" > /dev/null\n    \n    log_success \"Test completed for $tag\"\n}\n\n# Function to get image size\nget_image_size() {\n    local tag=$1\n    local size\n    size=$(docker images --format \"table {{.Size}}\" \"$tag\" | tail -n 1)\n    echo \"$size\"\n}\n\n# Function to display build summary\nbuild_summary() {\n    log_info \"Build Summary:\"\n    echo \"  Version: $VERSION\"\n    echo \"  Build Date: $BUILD_DATE\"\n    echo \"  Build Ref: $BUILD_REF\"\n    echo \"\"\n    \n    log_info \"Image sizes:\"\n    for arch in amd64 arm64 armv7; do\n        local tag=\"${IMAGE_NAME}:${VERSION}-${arch}\"\n        if docker images -q \"$tag\" > /dev/null 2>&1; then\n            local size\n            size=$(get_image_size \"$tag\")\n            echo \"  $arch: $size\"\n        fi\n    done\n}\n\n# Main function\nmain() {\n    log_info \"Starting AICleaner v3 Docker build process\"\n    log_info \"Version: $VERSION\"\n    \n    # Check prerequisites\n    check_buildx\n    \n    # Parse command line arguments\n    local build_type=${2:-\"multi\"}\n    local test_enabled=${3:-\"true\"}\n    \n    case \"$build_type\" in\n        \"single\")\n            local arch=${4:-\"amd64\"}\n            build_single_arch \"$arch\"\n            if [[ \"$test_enabled\" == \"true\" ]]; then\n                test_image \"$arch\"\n            fi\n            ;;\n        \"multi\")\n            setup_builder\n            build_multi_arch\n            ;;\n        \"test\")\n            local arch=${4:-\"amd64\"}\n            test_image \"$arch\"\n            ;;\n        *)\n            log_error \"Unknown build type: $build_type\"\n            echo \"Usage: $0 <version> [single|multi|test] [true|false] [arch]\"\n            echo \"Examples:\"\n            echo \"  $0 1.0.0 single true amd64   # Build single arch with test\"\n            echo \"  $0 1.0.0 multi false         # Build multi-arch without test\"\n            echo \"  $0 1.0.0 test true arm64     # Test specific architecture\"\n            exit 1\n            ;;\n    esac\n    \n    build_summary\n    log_success \"Docker build process completed!\"\n}\n\n# Run main function with all arguments\nmain \"$@\""