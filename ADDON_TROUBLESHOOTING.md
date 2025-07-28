# Home Assistant Addon Repository Troubleshooting Guide

## Critical Fix Applied
✅ **Repository Structure Fixed**: Added explicit addon location specification to `repository.yaml`

This was the most likely cause of the addon not appearing in Home Assistant.

## Repository URL
Use this exact URL in Home Assistant Add-on Store:
```
https://github.com/sporebattyl/aicleaner_v3
```

## Diagnostic Steps

### 1. Clear Home Assistant Cache (CRITICAL)
Home Assistant aggressively caches repository information. Even after fixes, it may show old cached versions.

**Method A - Host Reboot (Most Effective)**:
1. Go to **Settings > System > Hardware**
2. Click the three-dot menu (top right)
3. Select **"Reboot Host"**
4. Wait for complete restart
5. Try adding repository again

**Method B - Supervisor Repair**:
1. Install "Terminal & SSH" addon if not already installed
2. Access terminal and run:
   ```bash
   ha su repair
   ```
3. Wait for completion
4. Go to Add-on Store and click **"Reload"**

### 2. Check Supervisor Logs
This will show exactly why the repository isn't working:

1. Go to **Settings > System > Logs**
2. Change dropdown from "Home Assistant Core" to **"Supervisor"**
3. Click **"Refresh"** immediately after trying to add the repository
4. Look for lines containing:
   - `sporebattyl/aicleaner_v3`
   - `aicleaner_v3`
   - Error messages related to repository validation

### 3. Verify System Architecture
1. Go to **Settings > System > Hardware**
2. Note your architecture (e.g., `aarch64`, `amd64`, `armhf`, `armv7`)
3. Confirm this matches one of the supported architectures:
   - ✅ aarch64 (Raspberry Pi 4, etc.)
   - ✅ amd64 (Intel/AMD 64-bit)
   - ✅ armhf (Older ARM devices)
   - ✅ armv7 (32-bit ARM)

### 4. Manual Repository Addition Steps
1. Go to **Supervisor > Add-on Store**
2. Click the three-dot menu (top right)
3. Select **"Repositories"**
4. Add: `https://github.com/sporebattyl/aicleaner_v3`
5. Click **"Add"**
6. Wait 30 seconds
7. Click **"Reload"** (three-dot menu)
8. Look for "AICleaner V3" in the store

## Alternative: Local Installation Method

If repository method still fails, try local installation:

### Prerequisites
- "Terminal & SSH" addon installed and configured
- SSH access to Home Assistant

### Steps
1. SSH into Home Assistant
2. Navigate to addons directory:
   ```bash
   cd /addons
   ```
3. Clone repository:
   ```bash
   git clone https://github.com/sporebattyl/aicleaner_v3.git aicleaner_v3_local
   ```
4. Go to Add-on Store
5. Click **"Reload"** (three-dot menu)
6. Look for "Local addons" section at top
7. "AICleaner V3" should appear there

## Expected Behavior After Fix

After clearing cache and adding repository:
- Repository should appear in **Supervisor > Add-on Store > Repositories**
- "AICleaner V3" should appear in the main add-on store
- Addon description should show version 1.1.0
- Install button should be available

## Common Issues & Solutions

### Issue: "Repository not found"
- **Solution**: Verify exact URL (no trailing slashes)
- **Solution**: Check internet connectivity from HA

### Issue: "No addons found in repository"
- **Solution**: This was the original problem - now fixed with explicit addon location

### Issue: Addon appears but won't install
- **Solution**: Check Docker images are available at `ghcr.io/sporebattyl/aicleaner_v3`
- **Solution**: Verify your architecture is supported

### Issue: Still not working after all steps
- **Solution**: Try local installation method above
- **Solution**: Check Supervisor logs for specific error messages
- **Solution**: Ensure Home Assistant version is 2023.1.0 or newer

## Files That Were Fixed
- `/repository.yaml` - Added explicit addon location specification
- This resolves the primary discovery issue

## Support
If issues persist after following this guide:
1. Check Supervisor logs and note exact error messages
2. Verify system architecture compatibility
3. Try local installation method as final test