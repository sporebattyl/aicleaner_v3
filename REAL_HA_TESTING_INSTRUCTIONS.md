# AICleaner V3 - Real Home Assistant Testing Guide

## 🎯 TESTING STATUS
- **HA Server Found**: ✅ http://192.168.88.125:8123
- **Addon Structure**: ✅ Validated and ready
- **Login Screen**: ✅ Detected (username: drewcifer)

## 📋 MANUAL TESTING CHECKLIST

### Phase 1: Addon Installation
1. **Copy addon to HA server:**
   ```bash
   # On your HA server machine:
   sudo mkdir -p /usr/share/hassio/addons/local/aicleaner_v3
   sudo cp -r /path/to/aicleaner_v3/* /usr/share/hassio/addons/local/aicleaner_v3/
   sudo chown -R root:root /usr/share/hassio/addons/local/aicleaner_v3/
   sudo chmod +x /usr/share/hassio/addons/local/aicleaner_v3/run.sh
   ```

2. **Refresh Home Assistant:**
   - Restart HA Supervisor: `ha supervisor restart`
   - Or restart HA Core: `ha core restart`

3. **Check addon appears:**
   - Login to http://192.168.88.125:8123
   - Navigate to Settings → Add-ons
   - Look for "Local add-ons" section
   - Verify "AI Cleaner v3" appears

### Phase 2: Addon Configuration Testing
4. **Install the addon:**
   - Click on "AI Cleaner v3"
   - Click "Install" button
   - Wait for installation to complete
   - Check logs for any errors

5. **Configure addon:**
   - Go to Configuration tab
   - Add your Gemini API key
   - Configure at least one zone with:
     - Camera entity (must exist in HA)
     - Purpose description
     - Ignore rules

6. **Start addon:**
   - Go to Info tab
   - Click "Start" button
   - Monitor logs for startup success

### Phase 3: Functionality Testing
7. **Web Interface Test:**
   - Check if "Open Web UI" button appears
   - Click it to test ingress functionality
   - Verify web interface loads

8. **Integration Test:**
   - Check if addon creates MQTT entities
   - Verify camera integration works
   - Test zone scanning functionality

### Phase 4: Validation Tests
9. **Performance Test:**
   - Monitor resource usage in Supervisor
   - Check response times
   - Verify stability over 1 hour

10. **Error Handling Test:**
    - Test with invalid API key
    - Test with non-existent camera entity
    - Verify graceful error handling

## 🔍 EXPECTED RESULTS

### Installation Success Indicators:
- [ ] Addon appears in Local add-ons
- [ ] Installation completes without errors
- [ ] Configuration interface loads properly
- [ ] Addon starts successfully
- [ ] No critical errors in logs

### Runtime Success Indicators:
- [ ] Web interface accessible
- [ ] Camera entities detected
- [ ] AI analysis functions work
- [ ] MQTT messages sent (if configured)
- [ ] Todo list integration works

## 🚨 TROUBLESHOOTING

### Common Issues:
1. **Addon not appearing:**
   - Check file permissions
   - Verify config.json syntax
   - Restart HA Supervisor

2. **Installation fails:**
   - Check Docker resources
   - Review addon logs
   - Verify requirements.txt

3. **Startup fails:**
   - Check Gemini API key
   - Verify camera entities exist
   - Review configuration syntax

### Log Locations:
- Addon logs: Supervisor → AI Cleaner v3 → Log
- System logs: Settings → System → Logs
- Core logs: `ha core logs`

## 📊 TEST RESULTS TEMPLATE

Copy and fill out:
```
AICLEANER V3 TESTING RESULTS
============================
Date: ___________
HA Version: ___________
Hardware: AMD 8845HS (GMKtec K8 Plus)

INSTALLATION:
□ Files copied successfully
□ Permissions set correctly
□ Addon appears in local add-ons
□ Installation completes without errors

CONFIGURATION:
□ Configuration interface loads
□ API key field accepts input
□ Zone configuration works
□ Settings save properly

FUNCTIONALITY:
□ Addon starts successfully
□ Web interface accessible
□ Camera integration works
□ AI analysis functions
□ No critical error messages

PERFORMANCE:
CPU Usage: _____%
Memory Usage: _____MB
Startup Time: _____seconds
Response Time: _____seconds

OVERALL STATUS: PASS / FAIL
Notes: ________________________
```

## 📞 SUPPORT

If you encounter issues:
1. Check addon logs first
2. Verify all dependencies are met
3. Test with minimal configuration
4. Review HA compatibility requirements

**Ready for testing!** The addon structure is validated and your HA server is accessible.