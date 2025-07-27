# GitHub Release Instructions for AICleaner V3 v1.0.2

## Option 1: Using GitHub CLI (Recommended)

### Step 1: Authenticate GitHub CLI
```bash
export PATH="$PWD/gh_2.40.1_linux_amd64/bin:$PATH"
gh auth login
```
Follow the prompts to authenticate with your GitHub account.

### Step 2: Create Release
```bash
gh release create v1.0.2 \
  --title "AICleaner V3 v1.0.2 - Build System Fix" \
  --notes "## Fixed Home Assistant Addon Installation

### Changes
- ✅ Fixed Docker image naming mismatch causing 403 Forbidden errors
- ✅ Implemented standard Home Assistant addon build workflow  
- ✅ Added proper multi-architecture support
- ✅ Configured GitHub Container Registry authentication

### Installation
Images are now properly built as \`ghcr.io/sporebattyl/aicleaner_v3/{arch}:1.0.2\`

This release resolves the addon installation failures in Home Assistant."
```

## Option 2: Using GitHub Web Interface

1. **Navigate to**: https://github.com/sporebattyl/aicleaner_v3/releases/new
2. **Tag**: Select or type `v1.0.2` (tag already exists)
3. **Title**: `AICleaner V3 v1.0.2 - Build System Fix`
4. **Description**: Copy the markdown content from Step 2 above
5. **Click**: "Publish release"

## Option 3: Using API with Personal Access Token

### Step 1: Set your GitHub token
```bash
export GITHUB_TOKEN="your_personal_access_token_here"
```

### Step 2: Run the release script
```bash
./create_release.sh
```

## What Happens After Release Creation

1. **Workflow Triggers**: The GitHub Actions workflow will trigger the `publish` job
2. **Multi-Architecture Builds**: Images will be built for all supported architectures
3. **Container Registry**: Images will be published to `ghcr.io/sporebattyl/aicleaner_v3/{arch}:1.0.2`
4. **Addon Installation**: Home Assistant will now be able to pull the correctly named images

## Verification Steps

1. **Check Workflow**: https://github.com/sporebattyl/aicleaner_v3/actions
2. **Verify Packages**: https://github.com/sporebattyl?tab=packages
3. **Test Installation**: Try installing the addon in Home Assistant

## Expected Results

- ✅ No more 403 Forbidden errors during addon installation
- ✅ Proper multi-architecture support (amd64, aarch64, armv7, armhf, i386)
- ✅ Correctly named Docker images in GitHub Container Registry
- ✅ Successful addon installation and operation in Home Assistant

The fix addresses the root cause of the installation failure by aligning the Docker image naming convention between the Home Assistant addon configuration and the GitHub Actions build process.