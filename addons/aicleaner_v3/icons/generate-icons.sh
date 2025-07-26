#!/bin/bash

# AICleaner V3 Icon Generation Script
# Generates all required icon variants from the primary logo

set -e

# Configuration
ICONS_DIR="/home/drewcifer/aicleaner_v3/addons/aicleaner_v3/icons"
SOURCE_LOGO="/home/drewcifer/aicleaner_v3/logo.png"
PRIMARY_LOGO="$ICONS_DIR/logo-128.png"

# Colors
BG_GRAY="#E8E8E8"
BG_DARK="#2C2C2C"
BG_WHITE="#FFFFFF"

echo "🎨 AICleaner V3 Icon Generation Starting..."
echo "Source: $SOURCE_LOGO"
echo "Output: $ICONS_DIR"

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo "❌ ImageMagick not found. Please install it:"
    echo "   Ubuntu/Debian: sudo apt install imagemagick"
    echo "   macOS: brew install imagemagick"
    echo "   RHEL/CentOS: sudo yum install ImageMagick"
    exit 1
fi

# Ensure source exists
if [ ! -f "$SOURCE_LOGO" ]; then
    echo "❌ Source logo not found: $SOURCE_LOGO"
    exit 1
fi

# Create icons directory if it doesn't exist
mkdir -p "$ICONS_DIR"

echo "📋 Generating size variants..."

# Size variants
echo "  - 64x64 (mobile/compact)"
convert "$PRIMARY_LOGO" -resize 64x64 "$ICONS_DIR/logo-64.png"

echo "  - 256x256 (high-DPI)"
convert "$PRIMARY_LOGO" -resize 256x256 "$ICONS_DIR/logo-256.png"

echo "  - 512x512 (ultra high-DPI)"
convert "$PRIMARY_LOGO" -resize 512x512 "$ICONS_DIR/logo-512.png"

echo "🌙 Generating theme variants..."

# Dark theme variant
echo "  - Dark theme"
convert "$PRIMARY_LOGO" \
    -fill "$BG_DARK" -colorize 100% \
    \( "$PRIMARY_LOGO" -alpha extract -negate \) \
    -compose multiply -composite \
    \( "$PRIMARY_LOGO" -modulate 120,150,100 \) \
    -compose screen -composite \
    "$ICONS_DIR/logo-dark.png"

# Light theme variant  
echo "  - Light theme"
convert "$PRIMARY_LOGO" -background "$BG_WHITE" -flatten "$ICONS_DIR/logo-light.png"

# Transparent background
echo "  - Transparent background"
convert "$PRIMARY_LOGO" -transparent "$BG_GRAY" "$ICONS_DIR/logo-transparent.png"

# High contrast variant
echo "  - High contrast"
convert "$PRIMARY_LOGO" \
    -modulate 100,0,100 \
    -brightness-contrast 50x50 \
    -background "$BG_WHITE" -flatten \
    "$ICONS_DIR/logo-high-contrast.png"

echo "🔄 Generating shape variants..."

# Circular variant
echo "  - Circular crop"
convert "$PRIMARY_LOGO" -resize 128x128 \
    \( +clone -threshold -1 -negate -fill white -draw "circle 64,64 64,0" \) \
    -alpha off -compose copy_opacity -composite \
    "$ICONS_DIR/logo-circle.png"

# Square with padding
echo "  - Square with padding"
convert "$PRIMARY_LOGO" -background "$BG_GRAY" -gravity center -extent 144x144 -resize 128x128 "$ICONS_DIR/logo-square-padded.png"

# Panel optimized (simplified 64x64)
echo "  - Panel optimized"
convert "$PRIMARY_LOGO" -resize 64x64 -unsharp 0x1 "$ICONS_DIR/logo-panel.png"

echo "🌐 Generating web variants..."

# PWA icons
echo "  - PWA 192x192"
convert "$PRIMARY_LOGO" -resize 192x192 "$ICONS_DIR/logo-web-192.png"

echo "  - PWA 512x512"
convert "$PRIMARY_LOGO" -resize 512x512 "$ICONS_DIR/logo-web-512.png"

# Favicon (multi-size ICO)
echo "  - Favicon.ico"
convert "$PRIMARY_LOGO" \
    \( -clone 0 -resize 16x16 \) \
    \( -clone 0 -resize 32x32 \) \
    \( -clone 0 -resize 48x48 \) \
    -delete 0 \
    "$ICONS_DIR/favicon.ico"

echo "📊 Generating summary report..."

# Create summary file
cat > "$ICONS_DIR/generation-report.txt" << EOF
AICleaner V3 Icon Generation Report
Generated: $(date)
Source: $SOURCE_LOGO

Files Generated:
$(ls -la "$ICONS_DIR"/*.png "$ICONS_DIR"/*.ico 2>/dev/null | wc -l) icon files

Size Variants:
- logo-64.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-64.png"))
- logo-128.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-128.png"))  
- logo-256.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-256.png"))
- logo-512.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-512.png"))

Theme Variants:
- logo-dark.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-dark.png"))
- logo-light.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-light.png"))
- logo-transparent.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-transparent.png"))
- logo-high-contrast.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-high-contrast.png"))

Shape Variants:
- logo-circle.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-circle.png"))
- logo-square-padded.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-square-padded.png"))
- logo-panel.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-panel.png"))

Web Variants:
- logo-web-192.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-web-192.png"))
- logo-web-512.png ($(identify -format "%wx%h" "$ICONS_DIR/logo-web-512.png"))
- favicon.ico (multi-size)

Total Disk Usage: $(du -sh "$ICONS_DIR" | cut -f1)

Next Steps:
1. Verify icon quality and appearance
2. Update addon config.yaml with new panel_icon
3. Implement web UI favicon integration
4. Test icons across different HA themes
5. Update documentation
EOF

echo "✅ Icon generation complete!"
echo "📁 Generated files in: $ICONS_DIR"
echo "📄 See generation-report.txt for details"
echo ""
echo "🔧 Next steps:"
echo "   1. Review generated icons for quality"
echo "   2. Implement web UI integration (see web-ui-integration.html)"
echo "   3. Test across different Home Assistant themes"
echo "   4. Update main addon README with icon usage"
echo ""
echo "📋 Configuration update applied:"
echo "   - Changed panel_icon from 'mdi:robot-vacuum' to 'mdi:broom'"