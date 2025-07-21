#!/bin/bash
# AICleaner v3 Phase 2 - Home Assistant Integration Test Runner
# This script orchestrates a complete test run with real Home Assistant

set -e  # Exit on any error

echo "🧪 AICleaner v3 - Home Assistant Integration Tests"
echo "=================================================="

# Check if .env file exists with HA_ACCESS_TOKEN
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please run setup-ha-token.sh first."
    exit 1
fi

# Source environment variables
source .env

if [ -z "$HA_ACCESS_TOKEN" ]; then
    echo "❌ Error: HA_ACCESS_TOKEN not found in .env file. Please run setup-ha-token.sh first."
    exit 1
fi

echo "✅ HA_ACCESS_TOKEN found in .env file"

# Clean up any existing containers and volumes
echo "🧹 Cleaning up existing test environment..."
docker-compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true

# Build the AICleaner container if needed
echo "🔨 Building AICleaner container..."
docker-compose -f docker-compose.test.yml build --no-cache aicleaner-test

# Start the test environment
echo "🚀 Starting Home Assistant and supporting services..."
docker-compose -f docker-compose.test.yml up -d mosquitto-test homeassistant

echo "⏳ Waiting for Home Assistant to be ready (this may take 60-90 seconds)..."
timeout 120 bash -c 'until docker-compose -f docker-compose.test.yml ps | grep -q "homeassistant.*healthy"; do sleep 5; echo -n "."; done'

if ! docker-compose -f docker-compose.test.yml ps | grep -q "homeassistant.*healthy"; then
    echo ""
    echo "❌ Home Assistant failed to start properly. Checking logs:"
    docker-compose -f docker-compose.test.yml logs homeassistant --tail 20
    exit 1
fi

echo ""
echo "✅ Home Assistant is ready!"

# Start the AICleaner addon
echo "🔌 Starting AICleaner addon..."
docker-compose -f docker-compose.test.yml up -d aicleaner-test mqtt-monitor

echo "⏳ Waiting for AICleaner to be ready..."
timeout 60 bash -c 'until docker-compose -f docker-compose.test.yml ps | grep -q "aicleaner-test.*healthy"; do sleep 3; echo -n "."; done'

if ! docker-compose -f docker-compose.test.yml ps | grep -q "aicleaner-test.*healthy"; then
    echo ""
    echo "❌ AICleaner addon failed to start properly. Checking logs:"
    docker-compose -f docker-compose.test.yml logs aicleaner-test --tail 20
    exit 1
fi

echo ""
echo "✅ AICleaner addon is ready!"

# Run the integration tests
echo "🧪 Running integration tests..."
docker-compose -f docker-compose.test.yml run --rm test-runner

# Capture the exit code
TEST_EXIT_CODE=$?

# Show service status
echo ""
echo "📊 Final service status:"
docker-compose -f docker-compose.test.yml ps

# Show recent logs if tests failed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "❌ Tests failed. Recent logs:"
    echo "--- AICleaner Logs ---"
    docker-compose -f docker-compose.test.yml logs aicleaner-test --tail 15
    echo "--- Home Assistant Logs ---"
    docker-compose -f docker-compose.test.yml logs homeassistant --tail 15
fi

# Clean up
echo "🧹 Cleaning up test environment..."
docker-compose -f docker-compose.test.yml down -v

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "🎉 All tests passed successfully!"
else
    echo "❌ Tests failed with exit code $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE