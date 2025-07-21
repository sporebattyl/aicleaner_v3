#!/bin/bash
# AICleaner v3 Phase 2 - Home Assistant Access Token Setup
# This script helps generate and store the HA_ACCESS_TOKEN for testing

set -e

echo "🔐 AICleaner v3 - Home Assistant Access Token Setup"
echo "=================================================="
echo ""
echo "This script will help you generate a long-lived access token for Home Assistant testing."
echo ""

# Check if .env already exists
if [ -f .env ] && grep -q "HA_ACCESS_TOKEN=" .env; then
    echo "⚠️  An HA_ACCESS_TOKEN already exists in .env file:"
    grep "HA_ACCESS_TOKEN=" .env
    echo ""
    read -p "Do you want to replace it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ Keeping existing token. Exiting."
        exit 0
    fi
fi

echo "🚀 Starting temporary Home Assistant instance for token generation..."

# Clean up any existing containers
docker-compose -f docker-compose.test.yml down -v --remove-orphans 2>/dev/null || true

# Start just Home Assistant and MQTT for setup
docker-compose -f docker-compose.test.yml up -d mosquitto-test homeassistant

echo "⏳ Waiting for Home Assistant to start (this may take 60-90 seconds)..."
timeout 120 bash -c 'until curl -s http://localhost:8123/ >/dev/null 2>&1; do sleep 5; echo -n "."; done'

echo ""
echo "✅ Home Assistant is running!"
echo ""
echo "📋 To generate an access token, follow these steps:"
echo ""
echo "1. Open your web browser and go to: http://localhost:8123"
echo "2. Complete the Home Assistant onboarding:"
echo "   - Create a user account (any name/password)"
echo "   - Set your location (optional)"
echo "   - Skip any integrations for now"
echo "3. Once logged in, click on your user profile (bottom left)"
echo "4. Scroll down to 'Long-lived access tokens'"
echo "5. Click 'CREATE TOKEN'"
echo "6. Give it a name like 'AICleaner Testing'"
echo "7. Copy the generated token (it starts with 'eyJ...')"
echo ""
echo "⏳ Waiting for you to generate the token..."
echo "Press Enter when you have copied the token..."
read -r

echo ""
read -p "🔑 Paste your Home Assistant access token here: " HA_TOKEN

# Validate token format (basic check)
if [[ ! $HA_TOKEN =~ ^eyJ ]]; then
    echo "⚠️  Warning: Token doesn't look like a typical HA token (should start with 'eyJ')"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted. Please try again."
        docker-compose -f docker-compose.test.yml down -v
        exit 1
    fi
fi

# Test the token
echo "🧪 Testing the token..."
TEST_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $HA_TOKEN" \
    http://localhost:8123/api/)

if [ "$TEST_RESPONSE" = "200" ]; then
    echo "✅ Token is valid!"
else
    echo "❌ Token test failed (HTTP $TEST_RESPONSE). Please check the token and try again."
    docker-compose -f docker-compose.test.yml down -v
    exit 1
fi

# Save to .env file
if [ -f .env ]; then
    # Remove any existing HA_ACCESS_TOKEN line
    grep -v "HA_ACCESS_TOKEN=" .env > .env.tmp && mv .env.tmp .env || true
fi

echo "HA_ACCESS_TOKEN=$HA_TOKEN" >> .env

echo "✅ Token saved to .env file!"

# Clean up
echo "🧹 Stopping temporary Home Assistant instance..."
docker-compose -f docker-compose.test.yml down -v

echo ""
echo "🎉 Setup complete! You can now run the integration tests with:"
echo "   ./scripts/run-ha-tests.sh"
echo ""
echo "📝 Note: The token is saved in .env file. Keep this file secure and don't commit it to git."