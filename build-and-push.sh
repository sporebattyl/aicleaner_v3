#!/bin/bash

# Build and Push AICleaner V3 Docker Image
# This script builds the addon Docker image and pushes it to GitHub Container Registry

set -e

echo "🏗️  Building AICleaner V3 Docker Image"
echo "==============================================="

# Configuration
ADDON_DIR="/home/drewcifer/aicleaner_v3/addons/aicleaner_v3"
IMAGE_NAME="ghcr.io/sporebattyl/aicleaner_v3"
VERSION="1.1.1"
ARCHITECTURES=("amd64" "aarch64" "armhf" "armv7")

# Check if directory exists
if [ ! -d "$ADDON_DIR" ]; then
    echo "❌ Error: Addon directory not found at $ADDON_DIR"
    exit 1
fi

# Check if required files exist
cd "$ADDON_DIR"
if [ ! -f "Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found"
    exit 1
fi

if [ ! -f "config.yaml" ]; then
    echo "❌ Error: config.yaml not found"
    exit 1
fi

if [ ! -f "build.yaml" ]; then
    echo "❌ Error: build.yaml not found"
    exit 1
fi

echo "✅ All required files found"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    exit 1
fi

echo "✅ Docker is running"

# Login to GitHub Container Registry
echo "🔐 Logging into GitHub Container Registry..."
echo "Please make sure you have set GITHUB_TOKEN environment variable"
echo "or run: export GITHUB_TOKEN=your_personal_access_token"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN environment variable is not set"
    echo "To create a token:"
    echo "1. Go to https://github.com/settings/tokens"
    echo "2. Create a token with 'write:packages' permission" 
    echo "3. Export it: export GITHUB_TOKEN=your_token_here"
    exit 1
fi

echo "$GITHUB_TOKEN" | docker login ghcr.io -u "${GITHUB_ACTOR:-$(whoami)}" --password-stdin

# Build for AMD64 architecture (most common)
echo "🏗️  Building Docker image for amd64..."
docker buildx build \
    --platform linux/amd64 \
    --build-arg BUILD_FROM="ghcr.io/home-assistant/amd64-base:3.19" \
    -t "${IMAGE_NAME}/amd64:${VERSION}" \
    --push \
    .

echo "✅ Successfully built and pushed ${IMAGE_NAME}/amd64:${VERSION}"

# Build for ARM64 architecture (Raspberry Pi 4, etc.)
echo "🏗️  Building Docker image for aarch64..."
docker buildx build \
    --platform linux/arm64 \
    --build-arg BUILD_FROM="ghcr.io/home-assistant/aarch64-base:3.19" \
    -t "${IMAGE_NAME}/aarch64:${VERSION}" \
    --push \
    .

echo "✅ Successfully built and pushed ${IMAGE_NAME}/aarch64:${VERSION}"

echo ""
echo "🎉 Build Complete!"
echo "==============================================="
echo "Images pushed to GitHub Container Registry:"
echo "- ${IMAGE_NAME}/amd64:${VERSION}"
echo "- ${IMAGE_NAME}/aarch64:${VERSION}"
echo ""
echo "Home Assistant should now be able to install the addon!"
echo "The addon will automatically pull the correct architecture."