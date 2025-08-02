#!/bin/bash
# Validation script to test AICleaner addon fixes

echo "🔍 AICleaner Addon Validation Script"
echo "====================================="

# Check if web UI is running
echo "1. Testing web UI accessibility..."
UI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null)
if [ "$UI_STATUS" = "200" ]; then
    echo "   ✅ Web UI is accessible (HTTP $UI_STATUS)"
else
    echo "   ❌ Web UI not accessible (HTTP $UI_STATUS)"
fi

# Test API endpoints
echo "2. Testing API endpoints..."

# Test status endpoint
echo "   Testing /api/status..."
STATUS_RESULT=$(curl -s http://localhost:8080/api/status 2>/dev/null)
if echo "$STATUS_RESULT" | jq . >/dev/null 2>&1; then
    echo "   ✅ /api/status returns valid JSON"
    echo "   Status: $(echo "$STATUS_RESULT" | jq -r '.status // "unknown"')"
    echo "   Token available: $(echo "$STATUS_RESULT" | jq -r '.supervisor_token_available // false')"
else
    echo "   ❌ /api/status returns invalid JSON or error"
fi

# Test entities endpoint (the main fix)
echo "   Testing /api/entities..."
ENTITIES_RESULT=$(curl -s http://localhost:8080/api/entities 2>/dev/null)
if echo "$ENTITIES_RESULT" | jq . >/dev/null 2>&1; then
    echo "   ✅ /api/entities returns valid JSON"
    CAMERA_COUNT=$(echo "$ENTITIES_RESULT" | jq '.cameras | length // 0')
    TODO_COUNT=$(echo "$ENTITIES_RESULT" | jq '.todo_lists | length // 0')
    SUCCESS=$(echo "$ENTITIES_RESULT" | jq -r '.success // false')
    echo "   Success: $SUCCESS"
    echo "   Cameras found: $CAMERA_COUNT"
    echo "   Todo lists found: $TODO_COUNT"
    
    if [ "$SUCCESS" = "true" ] && [ "$CAMERA_COUNT" -gt "0" ] && [ "$TODO_COUNT" -gt "0" ]; then
        echo "   🎉 API fix is working! Real entities loaded from Home Assistant"
    else
        echo "   ⚠️  API responding but may have issues"
        if [ "$SUCCESS" = "false" ]; then
            ERROR=$(echo "$ENTITIES_RESULT" | jq -r '.error // "unknown error"')
            echo "   Error: $ERROR"
        fi
    fi
else
    echo "   ❌ /api/entities returns invalid JSON or error"
fi

# Test config endpoint
echo "   Testing /api/config..."
CONFIG_RESULT=$(curl -s http://localhost:8080/api/config 2>/dev/null)
if echo "$CONFIG_RESULT" | jq . >/dev/null 2>&1; then
    echo "   ✅ /api/config returns valid JSON"
else
    echo "   ❌ /api/config returns invalid JSON or error"
fi

echo ""
echo "3. Home Assistant entity status..."
# Check if we can query HA entities through our MCP tools
python3 -c "
import sys
sys.path.insert(0, '/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/src')
print('AICleaner entities in Home Assistant:')
# This would require the MCP tools which aren't available in this script context
"

echo ""
echo "Validation complete!"
echo ""
echo "Next steps if addon is not running:"
echo "1. Open Home Assistant web interface"
echo "2. Go to Settings > Add-ons"
echo "3. Find 'AICleaner V3' and click 'Restart'"
echo "4. Re-run this script to validate the fixes"