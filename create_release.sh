#!/bin/bash

# GitHub Release Creation Script for AICleaner V3 v1.0.2
# Run this script with a valid GITHUB_TOKEN environment variable

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is required"
    echo "Create a token at: https://github.com/settings/tokens"
    echo "Token needs 'public_repo' scope"
    exit 1
fi

echo "Creating GitHub release v1.0.2..."

curl -L \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/sporebattyl/aicleaner_v3/releases \
  -d '{
    "tag_name": "v1.0.2",
    "name": "AICleaner V3 v1.0.2 - Build System Fix",
    "body": "## Fixed Home Assistant Addon Installation\n\n### Changes\n- ✅ Fixed Docker image naming mismatch causing 403 Forbidden errors\n- ✅ Implemented standard Home Assistant addon build workflow  \n- ✅ Added proper multi-architecture support\n- ✅ Configured GitHub Container Registry authentication\n\n### Installation\nImages are now properly built as `ghcr.io/sporebattyl/aicleaner_v3/{arch}:1.0.2`\n\nThis release resolves the addon installation failures in Home Assistant.",
    "draft": false,
    "prerelease": false
  }'

echo -e "\n\nRelease created! Check: https://github.com/sporebattyl/aicleaner_v3/releases/tag/v1.0.2"
echo "Monitor build progress: https://github.com/sporebattyl/aicleaner_v3/actions"