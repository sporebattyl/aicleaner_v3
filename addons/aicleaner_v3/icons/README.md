# AICleaner V3 Icon Assets

This directory contains all icon variants for the AICleaner V3 Home Assistant addon.

## Current Status
- ✅ Directory structure created
- ✅ Primary logo copied (logo-128.png)
- ⏳ Additional variants need generation
- ⏳ Web UI integration pending
- ⏳ Config updates pending

## Quick Start

### 1. Generate Icon Variants
Use the ImageMagick commands in `ICON_SPECIFICATIONS.md` to generate all required variants from the primary logo.

### 2. Update Addon Configuration
Apply the changes suggested in `config-updates.yaml` to your main `config.yaml` file.

### 3. Web UI Integration
Implement the favicon and manifest integration using the templates provided in `web-ui-integration.html` and `manifest.json`.

## Files in This Directory

### Documentation
- `ICON_SPECIFICATIONS.md` - Complete specifications for all icon variants
- `config-updates.yaml` - Recommended configuration changes
- `README.md` - This file

### Templates
- `web-ui-integration.html` - HTML template for web UI favicon integration
- `manifest.json` - Progressive Web App manifest

### Icons (To Be Generated)
- `logo-128.png` - ✅ Primary 128x128 icon (copied from original)
- `logo-64.png` - ⏳ 64x64 variant for mobile/compact displays
- `logo-256.png` - ⏳ 256x256 variant for high-DPI displays
- `logo-512.png` - ⏳ 512x512 variant for ultra high-DPI
- `logo-dark.png` - ⏳ Dark theme variant
- `logo-light.png` - ⏳ Light theme variant
- `logo-transparent.png` - ⏳ Transparent background variant
- `logo-high-contrast.png` - ⏳ High contrast accessibility variant
- `logo-circle.png` - ⏳ Circular crop variant
- `logo-square-padded.png` - ⏳ Square with padding
- `logo-panel.png` - ⏳ Panel-optimized 64x64
- `favicon.ico` - ⏳ Multi-size ICO for web UI
- `logo-web-192.png` - ⏳ 192x192 PWA icon
- `logo-web-512.png` - ⏳ 512x512 PWA icon

## Next Steps

1. **Generate Missing Icons**: Use image editing software or ImageMagick to create all variants
2. **Update Config**: Apply `panel_icon` change to main config.yaml
3. **Implement Web UI**: Add favicon and manifest to your web interface
4. **Test Integration**: Verify icons display correctly across HA contexts
5. **Update Documentation**: Add icon usage to main addon README

## Support

Refer to the comprehensive specifications in `ICON_SPECIFICATIONS.md` for detailed implementation guidance, color values, and technical requirements.