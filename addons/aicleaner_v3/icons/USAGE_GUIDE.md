# AICleaner V3 Icon Usage Guide

## Quick Implementation

### 1. Generate All Icon Variants
```bash
cd /home/drewcifer/aicleaner_v3/addons/aicleaner_v3/icons
./generate-icons.sh
```

### 2. Verify Generation
Check that all required files were created:
```bash
ls -la *.png *.ico
```

Expected files:
- logo-64.png, logo-128.png, logo-256.png, logo-512.png
- logo-dark.png, logo-light.png, logo-transparent.png, logo-high-contrast.png  
- logo-circle.png, logo-square-padded.png, logo-panel.png
- logo-web-192.png, logo-web-512.png
- favicon.ico

### 3. Update Web UI
Copy the HTML templates from `web-ui-integration.html` to your web interface files.

## Icon Context Usage

### Home Assistant Addon Store
- **Primary**: Use `logo-128.png` or `logo-256.png`
- **Location**: Main logo.png file in addon root
- **Requirements**: Clear branding, professional appearance

### Panel Integration  
- **Icon**: Updated to `mdi:broom` (more specific than robot-vacuum)
- **Location**: config.yaml `panel_icon` setting
- **Note**: HA panels use MDI icons, not custom PNGs

### Ingress Web UI
- **Favicon**: Use `favicon.ico` with multiple sizes
- **Progressive Web App**: Use `logo-web-192.png` and `logo-web-512.png`
- **Manifest**: Copy `manifest.json` to web root

### Documentation/GitHub
- **README**: Use `logo-transparent.png` for flexible backgrounds
- **Social Media**: Use `logo-256.png` for sharing/OpenGraph

### Mobile/Responsive
- **Small screens**: `logo-64.png` or `logo-panel.png`
- **High-DPI**: `logo-256.png` or `logo-512.png`
- **Circular contexts**: `logo-circle.png`

## Theme Integration

### Automatic Theme Detection
```css
/* Light theme (default) */
.logo-light { display: block; }
.logo-dark { display: none; }

/* Dark theme */
@media (prefers-color-scheme: dark) {
    .logo-light { display: none; }
    .logo-dark { display: block; }
}

/* High contrast */
@media (prefers-contrast: high) {
    .logo-light, .logo-dark { display: none; }
    .logo-high-contrast { display: block; }
}
```

### Home Assistant Theme Integration
```javascript
// Listen for HA theme changes
if (window.parent && window.parent.hassConnection) {
    window.parent.hassConnection.subscribeEvents((event) => {
        if (event.event_type === 'theme_updated') {
            updateLogo(event.data.theme);
        }
    }, 'theme_updated');
}
```

## File Size Optimization

### Recommended Optimizations
```bash
# PNG optimization with pngquant
pngquant --quality=80-95 --ext .png --force *.png

# Additional optimization with optipng  
optipng -o7 *.png

# WebP alternatives for modern browsers
for file in *.png; do
    cwebp -q 85 "$file" -o "${file%.png}.webp"
done
```

### Size Guidelines
- **64x64**: < 5KB optimal, < 10KB maximum
- **128x128**: < 15KB optimal, < 25KB maximum  
- **256x256**: < 35KB optimal, < 50KB maximum
- **512x512**: < 75KB optimal, < 100KB maximum

## Quality Assurance Checklist

### Visual Quality
- [ ] All variants maintain recognizable brand elements
- [ ] Colors match specified hex values (#2196F3, #4CAF50, #FFD700)
- [ ] Tools remain crossed at consistent angle
- [ ] Sparkles visible and properly positioned
- [ ] No artifacts or compression issues

### Technical Quality
- [ ] Correct file dimensions for each variant
- [ ] Proper alpha channel transparency
- [ ] Optimized file sizes
- [ ] Cross-platform compatibility
- [ ] sRGB color profile

### Accessibility
- [ ] High contrast variant meets WCAG 2.1 AA guidelines
- [ ] Recognizable at smallest size (16x16)
- [ ] Works without color (monochrome test)
- [ ] Proper alternative text descriptions

### Home Assistant Integration
- [ ] Panel icon displays correctly in HA sidebar
- [ ] Ingress web UI shows proper favicon
- [ ] Icons work in light and dark themes
- [ ] Addon store presentation is professional
- [ ] PWA installation shows correct icons

## Troubleshooting

### Common Issues

#### Icons Not Displaying in HA
1. Check file permissions (should be readable)
2. Verify file paths in config.yaml
3. Restart Home Assistant addon
4. Clear browser cache for web UI

#### Poor Quality at Small Sizes
1. Use simplified variants (logo-panel.png)
2. Increase contrast for small sizes
3. Remove fine details that don't scale well
4. Consider monochrome versions

#### Theme Switching Not Working
1. Verify CSS media queries
2. Check JavaScript theme detection
3. Test manual theme switching
4. Validate image file paths

#### Large File Sizes
1. Run PNG optimization tools
2. Reduce color depth if possible
3. Consider WebP format for modern browsers
4. Remove unnecessary metadata

### Performance Considerations

#### Lazy Loading
```html
<img src="logo-64.png" 
     data-src-hd="logo-256.png"
     loading="lazy"
     alt="AICleaner V3">
```

#### Responsive Images
```html
<picture>
    <source media="(min-width: 256px)" srcset="logo-256.png">
    <source media="(min-width: 128px)" srcset="logo-128.png">
    <img src="logo-64.png" alt="AICleaner V3">
</picture>
```

## Maintenance

### Regular Updates
- Review icon quality after HA updates
- Test across new HA themes
- Update PWA manifest when HA requirements change
- Optimize files as compression tools improve

### Version Control
- Tag icon updates with semantic versioning
- Document changes in CHANGELOG
- Backup original source files
- Maintain design consistency across updates

## Support Resources

- **Home Assistant Addon Docs**: https://developers.home-assistant.io/docs/add-ons/
- **MDI Icons**: https://materialdesignicons.com/
- **PWA Manifest**: https://web.dev/add-manifest/
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/

## Success Metrics

### Completion Indicators
- [ ] All 14+ icon variants generated successfully
- [ ] Panel icon updated from generic to specific
- [ ] Web UI favicon integration complete
- [ ] PWA manifest configured properly
- [ ] Theme switching functional
- [ ] Accessibility requirements met
- [ ] File sizes optimized
- [ ] Documentation complete

Your AICleaner V3 addon now has comprehensive, professional icon branding across all Home Assistant contexts!