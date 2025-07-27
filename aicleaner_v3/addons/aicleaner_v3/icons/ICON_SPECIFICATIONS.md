# AICleaner V3 Icon Specifications

## Overview
Comprehensive icon variants for Home Assistant addon branding across all contexts.

## Current Logo Analysis
- **File**: `/home/drewcifer/aicleaner_v3/logo.png`
- **Size**: 128x128 pixels
- **Design**: Crossed blue mop and green scrub brush with yellow sparkles
- **Background**: Light gray (#E8E8E8)
- **Colors**: 
  - Blue: #2196F3 (mop)
  - Green: #4CAF50 (brush)
  - Yellow: #FFD700 (sparkles)
  - Background: #E8E8E8

## Required Icon Variants

### 1. Size Variants
All variants maintain original aspect ratio and design elements.

#### logo-64.png
- **Dimensions**: 64x64 pixels
- **Use Cases**: Mobile displays, compact list views, small UI elements
- **Design Notes**: Simplify sparkle details if needed for clarity

#### logo-128.png (Primary)
- **Dimensions**: 128x128 pixels
- **Use Cases**: Standard addon logo, store listing, main branding
- **Source**: Current logo.png (copy to maintain consistency)

#### logo-256.png
- **Dimensions**: 256x256 pixels  
- **Use Cases**: High-DPI displays, detailed views, future-proofing
- **Design Notes**: Enhance details, sharper edges, anti-aliasing

#### logo-512.png
- **Dimensions**: 512x512 pixels
- **Use Cases**: Ultra high-DPI, print materials, scaling reference
- **Design Notes**: Maximum detail retention, vector-quality appearance

### 2. Theme Variants

#### logo-dark.png
- **Dimensions**: 128x128 pixels
- **Background**: Dark gray (#2C2C2C) or pure black (#000000)
- **Tools**: Lighter versions of blue (#64B5F6) and green (#81C784)
- **Sparkles**: Brighter yellow (#FFE082) or white (#FFFFFF)
- **Use Cases**: Dark theme UIs, OLED displays, night mode

#### logo-light.png
- **Dimensions**: 128x128 pixels
- **Background**: White (#FFFFFF) or very light gray (#F5F5F5)
- **Tools**: Original colors with slightly higher contrast
- **Use Cases**: Light theme UIs, print on dark backgrounds

#### logo-transparent.png
- **Dimensions**: 128x128 pixels
- **Background**: Transparent (alpha channel)
- **Tools**: Original colors with slight drop shadow for depth
- **Use Cases**: Overlaying on various backgrounds, flexible integration

#### logo-high-contrast.png
- **Dimensions**: 128x128 pixels
- **Colors**: High contrast for accessibility (WCAG compliance)
- **Background**: Pure white (#FFFFFF) or pure black (#000000)
- **Tools**: Maximum contrast versions
- **Use Cases**: Accessibility compliance, visual impairment support

### 3. Shape Variants

#### logo-circle.png
- **Dimensions**: 128x128 pixels (circular crop)
- **Design**: Tools centered in circle, background extends to edges
- **Use Cases**: Avatar contexts, circular UI elements, profile pictures

#### logo-square-padded.png
- **Dimensions**: 128x128 pixels
- **Design**: Original logo with increased padding (16px minimum on all sides)
- **Use Cases**: App store contexts, grid layouts, uniform spacing

#### logo-panel.png
- **Dimensions**: 64x64 pixels
- **Design**: Simplified version optimized for small panel display
- **Elements**: Simplified sparkles, thicker tool strokes
- **Use Cases**: Home Assistant panel integration, small icon contexts

### 4. Web UI Variants

#### favicon.ico
- **Format**: ICO file with multiple sizes embedded
- **Sizes**: 16x16, 32x32, 48x48 pixels
- **Design**: Highly simplified version focusing on tool crossed pattern
- **Use Cases**: Browser tabs, bookmarks, web UI branding

#### logo-web-192.png
- **Dimensions**: 192x192 pixels
- **Design**: Optimized for Progressive Web App manifest
- **Use Cases**: PWA installation, mobile home screen

#### logo-web-512.png
- **Dimensions**: 512x512 pixels
- **Design**: High-quality PWA icon
- **Use Cases**: PWA splash screens, app store listings

## File Naming Convention

```
icons/
├── logo-64.png          # 64x64 standard
├── logo-128.png         # 128x128 primary (copy of original)
├── logo-256.png         # 256x256 high-res
├── logo-512.png         # 512x512 ultra high-res
├── logo-dark.png        # 128x128 dark theme
├── logo-light.png       # 128x128 light theme  
├── logo-transparent.png # 128x128 transparent background
├── logo-high-contrast.png # 128x128 accessibility
├── logo-circle.png      # 128x128 circular crop
├── logo-square-padded.png # 128x128 with padding
├── logo-panel.png       # 64x64 panel optimized
├── favicon.ico          # Multi-size ICO
├── logo-web-192.png     # 192x192 PWA
└── logo-web-512.png     # 512x512 PWA
```

## Color Specifications

### Primary Palette
- **Mop Blue**: #2196F3 (RGB: 33, 150, 243)
- **Brush Green**: #4CAF50 (RGB: 76, 175, 80)
- **Sparkle Yellow**: #FFD700 (RGB: 255, 215, 0)
- **Background Gray**: #E8E8E8 (RGB: 232, 232, 232)

### Dark Theme Palette
- **Background**: #2C2C2C (RGB: 44, 44, 44)
- **Mop Blue Light**: #64B5F6 (RGB: 100, 181, 246)
- **Brush Green Light**: #81C784 (RGB: 129, 199, 132)
- **Sparkle Bright**: #FFE082 (RGB: 255, 224, 130)

### High Contrast Palette
- **Tools**: #000000 (pure black)
- **Background**: #FFFFFF (pure white)
- **Accents**: #FF0000 (red for critical elements)

## Implementation Guidelines

### Design Consistency
1. **Maintain Tool Proportion**: Keep mop and brush at same relative sizes
2. **Preserve Crossing Angle**: Tools should cross at consistent 45-degree angles
3. **Sparkle Placement**: Keep sparkles in upper-left quadrant for recognition
4. **Border Spacing**: Minimum 8px border from edge to design elements

### Quality Standards
1. **Anti-aliasing**: Use proper anti-aliasing for all curved elements
2. **Edge Sharpness**: Maintain crisp edges on straight lines
3. **Color Accuracy**: Use exact hex values specified
4. **Format Optimization**: PNG-24 with alpha channel support

### Accessibility Requirements
1. **Contrast Ratio**: Minimum 4.5:1 for normal text, 3:1 for large text
2. **Color Independence**: Design must be recognizable without color
3. **Scalability**: Readable at minimum 16x16 pixels
4. **Alternative Text**: Provide descriptive alt text for all contexts

## Usage Guidelines

### Home Assistant Contexts
- **Addon Store**: Use logo-128.png or logo-256.png
- **Panel Integration**: Use optimized MDI icon (see config updates)
- **Ingress Web UI**: Use favicon.ico and logo-web-* variants
- **Documentation**: Use logo-transparent.png for flexible backgrounds

### Progressive Web App
- **Manifest Icons**: Use logo-web-192.png and logo-web-512.png
- **Favicon**: Use favicon.ico
- **App Store**: Use logo-512.png

### Print Materials
- **Business Cards**: Use logo-transparent.png or logo-high-contrast.png
- **Documentation**: Use logo-256.png or higher resolution
- **Merchandise**: Use logo-512.png as base for vector recreation

## Generation Commands

### ImageMagick Commands
```bash
# Resize variants
convert logo.png -resize 64x64 logo-64.png
convert logo.png -resize 256x256 logo-256.png
convert logo.png -resize 512x512 logo-512.png

# Dark theme (invert and adjust)
convert logo.png -negate -modulate 80,120,100 logo-dark.png

# Transparent background
convert logo.png -transparent "#E8E8E8" logo-transparent.png

# Circular crop
convert logo.png -resize 128x128 \
  \( +clone -threshold -1 -negate -fill white -draw "circle 64,64 64,0" \) \
  -alpha off -compose copy_opacity -composite logo-circle.png

# Favicon generation
convert logo.png -resize 16x16 -resize 32x32 -resize 48x48 favicon.ico
```

### Photoshop/GIMP Guidelines
1. Start with original 128x128 logo.png
2. For size variants: Use bicubic resampling for upscaling, Lanczos for downscaling
3. For theme variants: Adjust levels and color balance as specified
4. For shape variants: Use appropriate masking and padding techniques
5. Save as PNG-24 with transparency support

## Quality Assurance Checklist

### Visual Quality
- [ ] All variants maintain recognizable brand elements
- [ ] Colors match specified hex values
- [ ] No artifacts or compression issues
- [ ] Proper transparency handling
- [ ] Consistent visual weight across sizes

### Technical Quality  
- [ ] Correct file dimensions
- [ ] Appropriate file sizes (optimize for web)
- [ ] Proper color profiles (sRGB)
- [ ] Alpha channel integrity
- [ ] Cross-platform compatibility

### Accessibility
- [ ] High contrast variant meets WCAG guidelines
- [ ] Recognizable at smallest sizes
- [ ] Works without color information
- [ ] Descriptive naming convention

## Next Steps
1. Generate all specified icon variants
2. Update addon configuration files
3. Implement web UI favicon integration
4. Test across different Home Assistant themes
5. Validate accessibility compliance
6. Document usage in addon README