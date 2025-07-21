# AICleaner V3 - Zero-Knowledge Installation Test

## Objective
This test simulates a new user's experience installing and configuring AICleaner V3. Follow these instructions **exactly as written** and document any confusion, ambiguity, or difficulty.

## Prerequisites Check
- [ ] Home Assistant OS installed and running
- [ ] Home Assistant accessible via web interface (http://your-ha-ip:8123)
- [ ] MQTT integration configured in Home Assistant
- [ ] Internet connectivity available
- [ ] At least one AI provider API key available (OpenAI, Google Gemini, etc.)

## Test Instructions

### Phase 1: Repository Addition

1. **Open Home Assistant**: Navigate to your Home Assistant web interface
2. **Access Supervisor**: Click on "Settings" → "Add-ons"
3. **Open Add-on Store**: Click "Add-on Store" button
4. **Access Repository Menu**: Click the three dots menu (⋮) in the top-right corner
5. **Add Repository**: Select "Repositories"
6. **Enter URL**: In the text field, enter: `https://github.com/drewcifer/aicleaner_v3`
7. **Add Repository**: Click "Add" button
8. **Wait for Processing**: System will process the repository (30-60 seconds)

**❓ Record any issues or confusion in Phase 1:**
- 
- 
- 

### Phase 2: Add-on Discovery

9. **Refresh Store**: Close and reopen the Add-on Store if needed
10. **Find AICleaner**: Look for "AICleaner V3" in the available add-ons list
11. **Verify Description**: Confirm the description mentions "AI-powered Home Assistant automation"

**❓ Record any issues or confusion in Phase 2:**
- 
- 
- 

### Phase 3: Installation

12. **Click AICleaner V3**: Click on the AICleaner V3 add-on card
13. **Review Information**: Read the add-on description and requirements
14. **Install Add-on**: Click the "Install" button
15. **Wait for Installation**: Installation typically takes 5-15 minutes depending on hardware
16. **Monitor Progress**: Watch for any error messages during installation

**❓ Record any issues or confusion in Phase 3:**
- 
- 
- 

### Phase 4: Configuration

17. **Open Configuration Tab**: Click the "Configuration" tab
18. **Review Options**: Look at available configuration options
19. **Set Primary API Key**:
    - Find the `primary_api_key` field
    - Enter your AI provider API key (starts with "sk-" for OpenAI)
20. **Optional - Set Device ID**: 
    - Change `device_id` to something descriptive like "aicleaner_living_room"
21. **Optional - Set Log Level**:
    - Change `log_level` to "debug" for initial testing
22. **Save Configuration**: Click "Save" button

**❓ Record any issues or confusion in Phase 4:**
- 
- 
- 

### Phase 5: Startup and Validation

23. **Start Add-on**: Click the "Start" button
24. **Monitor Startup**: Watch the startup process (should take 30-60 seconds)
25. **Check Logs**: Click the "Log" tab to view startup messages
26. **Verify Success**: Look for "AICleaner started successfully" or similar message

**❓ Record any issues or confusion in Phase 5:**
- 
- 
- 

### Phase 6: Home Assistant Integration Verification

27. **Go to Entities**: Navigate to Settings → Devices & Services → Entities
28. **Search for AICleaner**: Search for "aicleaner" in the entity list
29. **Expected Entities**:
    - `sensor.aicleaner_v3_status` - Should show "Running" or similar
    - `switch.aicleaner_v3_enabled` - Should be available for toggling
30. **Test Entity**: Try toggling the switch entity on/off

**❓ Record any issues or confusion in Phase 6:**
- 
- 
- 

### Phase 7: Basic Functionality Test

31. **Create Test Automation**: Go to Settings → Automations & Scenes
32. **New Automation**: Click "Create Automation"
33. **Use AICleaner Entity**: 
    - Trigger: State change of `sensor.aicleaner_v3_status`
    - Action: Send notification or log message
34. **Save and Test**: Save automation and test if it responds to state changes

**❓ Record any issues or confusion in Phase 7:**
- 
- 
- 

## Test Completion

### Overall Experience Rating
Rate each phase from 1-5 (1=Very Difficult, 5=Very Easy):
- Phase 1 (Repository Addition): ___/5
- Phase 2 (Add-on Discovery): ___/5
- Phase 3 (Installation): ___/5
- Phase 4 (Configuration): ___/5
- Phase 5 (Startup): ___/5
- Phase 6 (HA Integration): ___/5
- Phase 7 (Functionality): ___/5

### Time Tracking
- Total time for installation: ___ minutes
- Most time-consuming phase: ___
- Any phases that seemed to "hang": ___

### Critical Issues
List any issues that would prevent a typical user from completing the installation:
1. 
2. 
3. 

### Suggestions for Improvement
What would make this process easier or clearer?
1. 
2. 
3. 

### Success Criteria
- [ ] Add-on installs without errors
- [ ] Configuration UI is intuitive
- [ ] Add-on starts successfully
- [ ] Home Assistant entities are created
- [ ] Basic functionality works as expected
- [ ] Documentation is sufficient for self-service

## Notes for Developers
- Pay attention to exact wording of error messages
- Note any inconsistencies between documentation and actual behavior
- Consider the perspective of someone unfamiliar with Home Assistant add-ons
- Document every point of confusion, no matter how minor