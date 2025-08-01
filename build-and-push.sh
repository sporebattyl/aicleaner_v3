#!/bin/bash
set -e

# AICleaner V3 - Local Build and Push Script
# This script tests the addon build process locally before GitHub Actions

REGISTRY="ghcr.io"
REPO_OWNER="sporebattyl"
VERSION="1.1.1"
ADDON_PATH="./addons/aicleaner_v3"

echo "🏗️  Building AICleaner V3 addon locally..."
echo "Registry: ${REGISTRY}"
echo "Owner: ${REPO_OWNER}"
echo "Version: ${VERSION}"
echo "Addon Path: ${ADDON_PATH}"
echo "----------------------------------------"

# Verify addon directory exists
if [ ! -d "${ADDON_PATH}" ]; then
    echo "❌ Error: Addon directory not found at ${ADDON_PATH}"
    exit 1
fi

# Verify required files exist
echo "📋 Checking required files..."
if [ ! -f "${ADDON_PATH}/config.yaml" ]; then
    echo "❌ Error: config.yaml not found"
    exit 1
fi

if [ ! -f "${ADDON_PATH}/Dockerfile" ]; then
    echo "❌ Error: Dockerfile not found"
    exit 1
fi

if [ ! -f "${ADDON_PATH}/build.yaml" ]; then
    echo "❌ Error: build.yaml not found"
    exit 1
fi

echo "✅ All required files found"

# Check if logged into registry
echo "🔐 Checking Docker registry authentication..."
if ! docker login ${REGISTRY} --username ${REPO_OWNER} --password-stdin < /dev/null 2>/dev/null; then
    echo "⚠️  Not logged into ${REGISTRY}. Please run:"
    echo "echo 'YOUR_GITHUB_TOKEN' | docker login ${REGISTRY} --username ${REPO_OWNER} --password-stdin"
    echo ""
fi

# Build using Home Assistant builder (test mode first)
echo "🔨 Building addon with Home Assistant builder (test mode)..."
docker run \
    --rm \
    --privileged \
    -v "$(pwd)/${ADDON_PATH}:/data" \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    ghcr.io/home-assistant/amd64-builder \
    --target /data \
    --test \
    --amd64 \
    --docker-hub "${REGISTRY}/${REPO_OWNER}" \
    || {
        echo "❌ Test build failed!"
        exit 1
    }

echo "✅ Test build successful!"

# Ask user if they want to proceed with full build and push
read -p "🚀 Proceed with full build and push to registry? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Building and pushing to registry..."
    
    docker run \
        --rm \
        --privileged \
        -v ~/.docker:/root/.docker \
        -v "$(pwd)/${ADDON_PATH}:/data" \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        ghcr.io/home-assistant/amd64-builder \
        --target /data \
        --all \
        --docker-hub "${REGISTRY}/${REPO_OWNER}" \
        || {
            echo "❌ Build and push failed!"
            exit 1
        }
    
    echo "✅ Build and push completed successfully!"
    echo "📦 Image should now be available at:"
    echo "   ${REGISTRY}/${REPO_OWNER}/aicleaner_v3/amd64:${VERSION}"
    echo "   ${REGISTRY}/${REPO_OWNER}/aicleaner_v3/aarch64:${VERSION}"
    echo "   ${REGISTRY}/${REPO_OWNER}/aicleaner_v3/armv7:${VERSION}"
    echo "   ${REGISTRY}/${REPO_OWNER}/aicleaner_v3/armhf:${VERSION}"
else
    echo "🛑 Build cancelled by user"
fi

echo "✅ Script completed"