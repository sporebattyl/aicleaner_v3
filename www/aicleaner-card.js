/**
 * AICleaner Custom Lovelace Card
 *
 * A comprehensive Home Assistant Lovelace card for managing AICleaner v2.0
 * Features: Zone management, task tracking, analytics, and configuration
 */

console.log('AICleaner Card: Starting to load...');

/**
 * Improved AICleaner Card Validation System
 * Multi-tier validation with graceful degradation and comprehensive logging
 */
class ImprovedAICleanerValidation {
    constructor(hass) {
        this._hass = hass;
        this.validationLog = [];
    }

    /**
     * Log validation step with detailed information
     */
    log(level, message, data = null) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level: level,
            message: message,
            data: data
        };
        this.validationLog.push(logEntry);
        console.log(`AICleaner Validation [${level}]: ${message}`, data || '');
    }

    /**
     * Tier 1: Basic Entity Validation
     */
    validateTier1Basic(entity, zoneName) {
        this.log('INFO', `Tier 1 validation for zone: ${zoneName}`);

        const checks = {
            entityExists: !!entity,
            hasValidState: false,
            hasEntityId: false,
            hasAttributes: false
        };

        if (!entity) {
            this.log('ERROR', 'Entity does not exist', { zoneName });
            return { passed: false, checks, issues: ['Entity does not exist'] };
        }

        // Check state
        const state = entity.state;
        checks.hasValidState = state !== 'unavailable' && state !== 'unknown' && state !== null;

        // Check entity ID
        checks.hasEntityId = !!entity.entity_id;

        // Check attributes
        checks.hasAttributes = !!entity.attributes && typeof entity.attributes === 'object';

        const issues = [];
        if (!checks.hasValidState) issues.push(`Invalid state: ${state}`);
        if (!checks.hasEntityId) issues.push('Missing entity_id');
        if (!checks.hasAttributes) issues.push('Missing or invalid attributes');

        const passed = Object.values(checks).every(check => check);

        this.log(passed ? 'INFO' : 'WARN', `Tier 1 result: ${passed ? 'PASS' : 'FAIL'}`, {
            checks,
            issues,
            entityId: entity.entity_id,
            state: state
        });

        return { passed, checks, issues };
    }

    /**
     * Tier 2: Required Attributes Validation
     */
    validateTier2Attributes(entity, zoneName) {
        this.log('INFO', `Tier 2 validation for zone: ${zoneName}`);

        const attributes = entity.attributes || {};
        const checks = {
            hasFriendlyName: !!attributes.friendly_name,
            hasZoneName: !!(attributes.zone_name || attributes.display_name),
            hasIcon: !!attributes.icon,
            hasTaskData: !!(attributes.tasks || attributes.active_tasks !== undefined)
        };

        const issues = [];
        if (!checks.hasFriendlyName) issues.push('Missing friendly_name');
        if (!checks.hasZoneName) issues.push('Missing zone_name or display_name');
        if (!checks.hasIcon) issues.push('Missing icon');
        if (!checks.hasTaskData) issues.push('Missing task data (tasks or active_tasks)');

        const passed = checks.hasFriendlyName && checks.hasZoneName; // Only require essential attributes

        this.log(passed ? 'INFO' : 'WARN', `Tier 2 result: ${passed ? 'PASS' : 'FAIL'}`, {
            checks,
            issues,
            availableAttributes: Object.keys(attributes)
        });

        return { passed, checks, issues };
    }

    /**
     * Tier 3: Configuration Validation (Graceful)
     */
    validateTier3Configuration(entity, zoneName) {
        this.log('INFO', `Tier 3 validation for zone: ${zoneName}`);

        const attributes = entity.attributes || {};
        const checks = {
            hasCameraEntity: !!attributes.camera_entity,
            cameraEntityExists: false,
            cameraEntityAvailable: false,
            hasTodoEntity: !!attributes.todo_list_entity,
            todoEntityExists: false,
            todoEntityAvailable: false
        };

        const issues = [];
        const warnings = [];

        // Check camera entity (graceful)
        if (checks.hasCameraEntity) {
            const cameraEntity = attributes.camera_entity;
            const cameraState = this._hass.states[cameraEntity];

            checks.cameraEntityExists = !!cameraState;
            if (cameraState) {
                checks.cameraEntityAvailable = cameraState.state !== 'unavailable' && cameraState.state !== 'unknown';
                if (!checks.cameraEntityAvailable) {
                    warnings.push(`Camera entity '${cameraEntity}' is ${cameraState.state}`);
                }
            } else {
                warnings.push(`Camera entity '${cameraEntity}' not found`);
            }
        } else {
            warnings.push('No camera entity configured');
        }

        // Check todo entity (graceful)
        if (checks.hasTodoEntity) {
            const todoEntity = attributes.todo_list_entity;
            const todoState = this._hass.states[todoEntity];

            checks.todoEntityExists = !!todoState;
            if (todoState) {
                checks.todoEntityAvailable = todoState.state !== 'unavailable' && todoState.state !== 'unknown';
                if (!checks.todoEntityAvailable) {
                    warnings.push(`Todo entity '${todoEntity}' is ${todoState.state}`);
                }
            } else {
                warnings.push(`Todo entity '${todoEntity}' not found`);
            }
        } else {
            warnings.push('No todo entity configured');
        }

        // Graceful pass - don't fail for missing external entities
        const passed = true; // Always pass tier 3, just collect warnings

        this.log('INFO', `Tier 3 result: PASS (graceful)`, {
            checks,
            issues,
            warnings,
            cameraEntity: attributes.camera_entity,
            todoEntity: attributes.todo_list_entity
        });

        return { passed, checks, issues, warnings };
    }

    /**
     * Comprehensive zone validation with graceful degradation
     */
    validateZone(entity, zoneName) {
        this.log('INFO', `Starting comprehensive validation for zone: ${zoneName}`, {
            entityId: entity?.entity_id,
            state: entity?.state
        });

        const results = {
            zoneName: zoneName,
            entityId: entity?.entity_id,
            overallStatus: 'unknown',
            tier1: null,
            tier2: null,
            tier3: null,
            recommendation: 'unknown',
            allIssues: [],
            allWarnings: []
        };

        try {
            // Run validation tiers
            results.tier1 = this.validateTier1Basic(entity, zoneName);
            results.tier2 = this.validateTier2Attributes(entity, zoneName);
            results.tier3 = this.validateTier3Configuration(entity, zoneName);

            // Collect all issues and warnings
            [results.tier1, results.tier2, results.tier3].forEach(tier => {
                if (tier.issues) results.allIssues.push(...tier.issues);
                if (tier.warnings) results.allWarnings.push(...tier.warnings);
            });

            // Determine overall status and recommendation
            if (results.tier1.passed && results.tier2.passed) {
                results.overallStatus = 'fully_valid';
                results.recommendation = 'display_zone';
            } else if (results.tier1.passed) {
                results.overallStatus = 'basic_valid';
                results.recommendation = 'display_limited';
            } else {
                results.overallStatus = 'invalid';
                results.recommendation = 'hide_zone';
            }

            this.log('INFO', `Validation complete for ${zoneName}: ${results.overallStatus}`, {
                recommendation: results.recommendation,
                issueCount: results.allIssues.length,
                warningCount: results.allWarnings.length
            });

        } catch (error) {
            this.log('ERROR', `Validation failed for ${zoneName}`, { error: error.message });
            results.overallStatus = 'error';
            results.recommendation = 'hide_zone';
            results.allIssues.push(`Validation error: ${error.message}`);
        }

        return results;
    }
}

class AICleanerCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this._config = {};
        this._hass = {};
        this.currentView = 'dashboard'; // dashboard, zone, config, analytics, setup
        this.selectedZone = null;
        this.autoRefreshInterval = null;
        this.isLoading = false;
        this.lastUpdateTime = null;

        // Setup wizard state
        this.setupWizardStep = 1;
        this.setupWizardData = {
            hasCompletedSetup: localStorage.getItem('aicleaner_setup_completed') === 'true',
            zones: [],
            currentZone: {
                name: '',
                displayName: '',
                camera_entity: '',
                todo_list_entity: '',
                purpose: ''
            }
        };

        // Mobile-specific properties
        this.isMobile = this.detectMobile();
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.swipeThreshold = 50;

        // Initialize default data structures for TDD
        this.zones = [];
        this.systemStatus = {
            status: 'inactive',
            totalZones: 0,
            totalActiveTasks: 0,
            totalCompletedTasks: 0,
            globalCompletionRate: 0,
            version: '2.0'
        };
    }

    /**
     * Called when the card configuration is set
     */
    setConfig(config) {
        if (!config) {
            throw new Error('Invalid configuration');
        }
        
        this._config = {
            title: config.title || 'AICleaner',
            zones: config.zones || [],
            show_analytics: config.show_analytics !== false,
            show_config: config.show_config !== false,
            theme: config.theme || 'default',
            ...config
        };
        
        this.render();
    }

    /**
     * Detect if the device is mobile with enhanced detection
     */
    detectMobile() {
        const userAgent = navigator.userAgent || navigator.vendor || window.opera;
        const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        const isSmallScreen = window.innerWidth <= 768;
        const isTablet = window.innerWidth > 768 && window.innerWidth <= 1024 && isTouchDevice;

        // Store device type for more granular responsive design
        this.deviceType = isSmallScreen ? 'mobile' : isTablet ? 'tablet' : 'desktop';
        this.isPortrait = window.innerHeight > window.innerWidth;
        this.screenSize = {
            width: window.innerWidth,
            height: window.innerHeight,
            ratio: window.devicePixelRatio || 1
        };

        return isMobileUA || (isTouchDevice && isSmallScreen);
    }

    /**
     * Handle touch events for mobile gestures with enhanced functionality
     */
    handleTouchStart(e) {
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
        this.touchStartTime = Date.now();
        this.touchMoved = false;

        // Store initial touch for multi-touch detection
        this.initialTouchCount = e.touches.length;

        // Add visual feedback for touch
        this.addTouchFeedback(e.target);
    }

    handleTouchMove(e) {
        if (!this.touchStartX || !this.touchStartY) return;

        const touchX = e.touches[0].clientX;
        const touchY = e.touches[0].clientY;
        const deltaX = Math.abs(touchX - this.touchStartX);
        const deltaY = Math.abs(touchY - this.touchStartY);

        // Mark as moved if significant movement
        if (deltaX > 10 || deltaY > 10) {
            this.touchMoved = true;
            this.removeTouchFeedback();
        }

        // Show swipe indicators during horizontal swipe
        if (deltaX > deltaY && deltaX > 20) {
            this.showSwipeIndicators(touchX > this.touchStartX ? 'right' : 'left');
        }
    }

    handleTouchEnd(e) {
        if (!this.touchStartX || !this.touchStartY) return;

        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const touchDuration = Date.now() - this.touchStartTime;

        const deltaX = touchEndX - this.touchStartX;
        const deltaY = touchEndY - this.touchStartY;

        // Remove visual feedback
        this.removeTouchFeedback();
        this.hideSwipeIndicators();

        // Handle different gesture types
        if (!this.touchMoved && touchDuration < 300) {
            // Quick tap - let normal click handling work
            return;
        }

        // Horizontal swipe detection with improved sensitivity
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > this.swipeThreshold) {
            e.preventDefault(); // Prevent default swipe behavior

            if (deltaX > 0) {
                this.handleSwipeRight();
            } else {
                this.handleSwipeLeft();
            }
        }

        // Vertical swipe for refresh (pull down)
        if (Math.abs(deltaY) > Math.abs(deltaX) && deltaY > this.swipeThreshold * 2) {
            this.handlePullToRefresh();
        }

        // Reset touch coordinates
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchStartTime = 0;
        this.touchMoved = false;
    }

    handleSwipeLeft() {
        // Navigate to next view with haptic feedback
        const views = ['dashboard', 'analytics', 'config'];
        const currentIndex = views.indexOf(this.currentView);
        const nextIndex = (currentIndex + 1) % views.length;

        this.triggerHapticFeedback('light');
        this.switchView(views[nextIndex]);
        this.showToast(`Switched to ${views[nextIndex]}`, 'info', 1500);
    }

    handleSwipeRight() {
        // Navigate to previous view with haptic feedback
        const views = ['dashboard', 'analytics', 'config'];
        const currentIndex = views.indexOf(this.currentView);
        const prevIndex = currentIndex === 0 ? views.length - 1 : currentIndex - 1;

        this.triggerHapticFeedback('light');
        this.switchView(views[prevIndex]);
        this.showToast(`Switched to ${views[prevIndex]}`, 'info', 1500);
    }

    /**
     * Handle pull-to-refresh gesture
     */
    handlePullToRefresh() {
        if (this.isLoading) return; // Prevent multiple refreshes

        this.triggerHapticFeedback('medium');
        this.showToast('Refreshing data...', 'loading', 0);

        // Add visual feedback
        const card = this.shadowRoot.querySelector('.aicleaner-card');
        if (card) {
            card.style.transform = 'translateY(10px)';
            card.style.transition = 'transform 0.3s ease';

            setTimeout(() => {
                card.style.transform = '';
                card.style.transition = '';
            }, 300);
        }

        // Refresh data
        setTimeout(() => {
            this.refreshData();
        }, 500);
    }

    /**
     * Add visual touch feedback
     */
    addTouchFeedback(element) {
        if (!element || !this.isMobile) return;

        // Add touch feedback class
        element.classList.add('touch-active');

        // Create ripple effect
        const ripple = document.createElement('div');
        ripple.className = 'touch-ripple';

        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (this.touchStartX - rect.left - size / 2) + 'px';
        ripple.style.top = (this.touchStartY - rect.top - size / 2) + 'px';

        element.style.position = 'relative';
        element.appendChild(ripple);

        // Store reference for cleanup
        this.currentRipple = ripple;
    }

    /**
     * Remove visual touch feedback
     */
    removeTouchFeedback() {
        // Remove touch feedback classes
        this.shadowRoot.querySelectorAll('.touch-active').forEach(el => {
            el.classList.remove('touch-active');
        });

        // Remove ripple effect
        if (this.currentRipple) {
            this.currentRipple.remove();
            this.currentRipple = null;
        }
    }

    /**
     * Show swipe indicators during gesture
     */
    showSwipeIndicators(direction) {
        const indicators = this.shadowRoot.querySelectorAll('.swipe-indicator');
        indicators.forEach(indicator => {
            if ((direction === 'left' && indicator.classList.contains('left')) ||
                (direction === 'right' && indicator.classList.contains('right'))) {
                indicator.style.opacity = '1';
                indicator.style.transform = 'translateY(-50%) scale(1.2)';
            }
        });
    }

    /**
     * Hide swipe indicators
     */
    hideSwipeIndicators() {
        const indicators = this.shadowRoot.querySelectorAll('.swipe-indicator');
        indicators.forEach(indicator => {
            indicator.style.opacity = '';
            indicator.style.transform = '';
        });
    }

    /**
     * Trigger haptic feedback on supported devices
     */
    triggerHapticFeedback(type = 'light') {
        if (!this.isMobile || !navigator.vibrate) return;

        const patterns = {
            light: [10],
            medium: [20],
            heavy: [30],
            success: [10, 50, 10],
            error: [50, 100, 50]
        };

        navigator.vibrate(patterns[type] || patterns.light);
    }

    /**
     * Switch to a different view with animation
     */
    switchView(newView) {
        if (this.currentView === newView) return;

        const oldView = this.currentView;
        this.currentView = newView;

        // Add transition animation for mobile
        if (this.isMobile) {
            const card = this.shadowRoot.querySelector('.aicleaner-card');
            if (card) {
                card.style.opacity = '0.7';
                card.style.transform = 'scale(0.98)';
                card.style.transition = 'all 0.2s ease';

                setTimeout(() => {
                    this.render();
                    card.style.opacity = '';
                    card.style.transform = '';
                    card.style.transition = '';
                }, 200);
            } else {
                this.render();
            }
        } else {
            this.render();
        }
    }

    /**
     * Called when Home Assistant state updates
     */
    set hass(hass) {
        this._hass = hass;
        this.updateData();
        this.render();
    }

    /**
     * Get configured zone names from system status sensor
     */
    getConfiguredZoneNames() {
        const systemEntity = this._hass.states['sensor.aicleaner_system_status'];
        if (systemEntity?.attributes?.zones) {
            const configuredZones = systemEntity.attributes.zones.map(zone => ({
                name: zone.name,
                entityName: this.zoneNameToEntityName(zone.name)
            }));

            console.log('AICleaner Card: Found configured zones from system status:', configuredZones);
            return configuredZones;
        }

        console.log('AICleaner Card: No system status or zones found, falling back to entity discovery');
        return [];
    }

    /**
     * Convert zone display name to entity name format
     */
    zoneNameToEntityName(zoneName) {
        return zoneName.toLowerCase()
                      .replace(/[^a-z0-9]/g, '_')
                      .replace(/_+/g, '_')
                      .replace(/^_|_$/g, '');
    }

    /**
     * Configuration-driven zone discovery with entity fallback
     */
    updateData() {
        this.zones = [];
        this.systemStatus = {};

        // Ensure we have hass and states
        if (!this._hass || !this._hass.states) {
            console.log('AICleaner Card: No hass or states available');
            return;
        }

        console.log('AICleaner Card: Starting configuration-driven zone discovery');

        // Get configured zones from system status
        const configuredZones = this.getConfiguredZoneNames();

        if (configuredZones.length > 0) {
            // Configuration-driven approach
            console.log('AICleaner Card: Using configuration-driven discovery');
            this.updateDataFromConfiguration(configuredZones);
        } else {
            // Fallback to entity discovery
            console.log('AICleaner Card: Using entity discovery fallback');
            this.updateDataFromEntities();
        }

        // Load system status
        this.loadSystemStatus();

        // Filter out hidden zones
        this.zones = this.zones.filter(zone => !this.isZoneHidden(zone.name));

        // Log comprehensive discovery summary
        this.logDiscoverySummary();
    }

    /**
     * Configuration-driven zone discovery
     */
    updateDataFromConfiguration(configuredZones) {
        console.log('AICleaner Card: Processing configured zones:', configuredZones);

        for (const configZone of configuredZones) {
            const entityId = `sensor.aicleaner_${configZone.entityName}_tasks`;
            const entity = this._hass.states[entityId];

            console.log(`AICleaner Card: Looking for entity ${entityId} for zone "${configZone.name}"`);

            if (entity) {
                // Validate and add the zone
                const validationResult = this.validateZoneConfiguration(entity, configZone.entityName);

                if (validationResult.isValid) {
                    console.log(`AICleaner Card: ✅ Adding configured zone "${configZone.name}"`);
                    this.addZoneFromEntity(entity, configZone.entityName, configZone.name);
                } else {
                    console.log(`AICleaner Card: ⚠️  Configured zone "${configZone.name}" has validation issues:`, validationResult.errors);
                    // Add zone with error state for user feedback
                    this.addZoneWithErrors(configZone.name, validationResult.errors);
                }
            } else {
                console.log(`AICleaner Card: ❌ Entity missing for configured zone "${configZone.name}"`);
                // Add zone in "needs setup" state
                this.addZoneNeedsSetup(configZone.name, entityId);
            }
        }
    }

    /**
     * Entity discovery fallback
     */
    updateDataFromEntities() {
        console.log('AICleaner Card: Processing entities for zone discovery');

        Object.keys(this._hass.states).forEach(entityId => {
            if (entityId.startsWith('sensor.aicleaner_') && entityId.endsWith('_tasks')) {
                const zoneName = entityId.replace('sensor.aicleaner_', '').replace('_tasks', '');
                const entity = this._hass.states[entityId];

                console.log(`AICleaner Card: Discovered entity ${entityId} for zone ${zoneName}`);

                // Use improved validation system
                const validationResult = this.validateZoneConfiguration(entity, zoneName);

                if (validationResult.isValid) {
                    console.log(`AICleaner Card: ✅ Adding discovered zone ${zoneName}`);
                    this.addZoneFromEntity(entity, zoneName);
                } else {
                    console.log(`AICleaner Card: ❌ Skipping zone ${zoneName} - validation failed:`, validationResult.errors);
                }
            }
        });
    }

    /**
     * Add zone from valid entity
     */
    addZoneFromEntity(entity, zoneName, displayName = null) {
        this.zones.push({
            name: zoneName,
            displayName: displayName || entity.attributes.zone_name || zoneName,
            tasks: entity.attributes.tasks || [],
            activeTasks: entity.attributes.active_tasks || 0,
            completedTasks: entity.attributes.completed_tasks || 0,
            completionRate: entity.attributes.completion_rate || 0,
            efficiencyScore: entity.attributes.efficiency_score || 0,
            lastAnalysis: entity.attributes.last_analysis,
            status: entity.state,
            camera: entity.attributes.camera_entity,
            purpose: entity.attributes.purpose,
            configurationStatus: 'valid',
            entityId: entity.entity_id
        });
    }

    /**
     * Add zone with configuration errors
     */
    addZoneWithErrors(zoneName, errors) {
        this.zones.push({
            name: zoneName,
            displayName: zoneName,
            tasks: [],
            activeTasks: 0,
            completedTasks: 0,
            completionRate: 0,
            efficiencyScore: 0,
            lastAnalysis: null,
            status: 'configuration_error',
            camera: null,
            purpose: null,
            configurationStatus: 'error',
            configurationErrors: errors,
            showTroubleshootButton: true
        });
    }

    /**
     * Add zone that needs setup
     */
    addZoneNeedsSetup(zoneName, expectedEntityId) {
        this.zones.push({
            name: zoneName,
            displayName: zoneName,
            tasks: [],
            activeTasks: 0,
            completedTasks: 0,
            completionRate: 0,
            efficiencyScore: 0,
            lastAnalysis: null,
            status: 'needs_setup',
            camera: null,
            purpose: null,
            configurationStatus: 'needs_setup',
            expectedEntityId: expectedEntityId,
            showSetupButton: true
        });
    }

    /**
     * Load system status data
     */
    loadSystemStatus() {
        const systemEntity = this._hass.states['sensor.aicleaner_system_status'];
        if (systemEntity) {
            this.systemStatus = {
                status: systemEntity.state,
                totalZones: systemEntity.attributes.total_zones || 0,
                totalActiveTasks: systemEntity.attributes.total_active_tasks || 0,
                totalCompletedTasks: systemEntity.attributes.total_completed_tasks || 0,
                globalCompletionRate: systemEntity.attributes.global_completion_rate || 0,
                averageEfficiencyScore: systemEntity.attributes.average_efficiency_score || 0,
                lastGlobalAnalysis: systemEntity.attributes.last_analysis,
                version: systemEntity.attributes.version || '2.0',
                configuredZones: systemEntity.attributes.zones || []
            };

            console.log('AICleaner Card: System status loaded:', {
                status: this.systemStatus.status,
                totalZones: this.systemStatus.totalZones,
                configuredZones: this.systemStatus.configuredZones.length
            });
        } else {
            console.log('AICleaner Card: No system status entity found');
        }
    }

    /**
     * Log comprehensive discovery summary for debugging
     */
    logDiscoverySummary() {
        console.log('\n' + '='.repeat(60));
        console.log('AICleaner Card: ZONE DISCOVERY SUMMARY');
        console.log('='.repeat(60));

        console.log(`Total zones discovered: ${this.zones.length}`);
        console.log(`System status available: ${!!this.systemStatus.status}`);

        if (this.systemStatus.configuredZones) {
            console.log(`Configured zones in system: ${this.systemStatus.configuredZones.length}`);
        }

        // Log each zone with details
        this.zones.forEach((zone, index) => {
            console.log(`\nZone ${index + 1}: "${zone.displayName}"`);
            console.log(`  Entity ID: ${zone.entityId || 'N/A'}`);
            console.log(`  Status: ${zone.status}`);
            console.log(`  Configuration: ${zone.configurationStatus}`);
            console.log(`  Active Tasks: ${zone.activeTasks}`);
            console.log(`  Camera: ${zone.camera || 'Not configured'}`);

            if (zone.configurationErrors?.length > 0) {
                console.log(`  ⚠️  Errors: ${zone.configurationErrors.join(', ')}`);
            }

            if (zone.configurationWarnings?.length > 0) {
                console.log(`  ⚠️  Warnings: ${zone.configurationWarnings.join(', ')}`);
            }
        });

        // Log validation summary if available
        if (this.validator) {
            const validationSummary = this.validator.getValidationSummary();
            console.log(`\nValidation Log Entries: ${validationSummary.summary.totalEntries}`);
            console.log(`  Errors: ${validationSummary.summary.errorCount}`);
            console.log(`  Warnings: ${validationSummary.summary.warningCount}`);
            console.log(`  Info: ${validationSummary.summary.infoCount}`);
        }

        console.log('\n' + '='.repeat(60));
        console.log('AICleaner Card: END DISCOVERY SUMMARY');
        console.log('='.repeat(60) + '\n');
    }

    /**
     * Improved zone validation with graceful degradation
     * @param {Object} entity - The zone sensor entity
     * @param {string} zoneName - The name of the zone
     * @returns {Object} Validation result with isValid flag and errors array
     */
    validateZoneConfiguration(entity, zoneName) {
        // Initialize improved validation system
        if (!this.validator) {
            this.validator = new ImprovedAICleanerValidation(this._hass);
        }

        // Run comprehensive validation
        const validationResult = this.validator.validateZone(entity, zoneName);

        // Convert to legacy format for compatibility
        const isValid = validationResult.recommendation !== 'hide_zone';
        const errors = validationResult.allIssues;
        const warnings = validationResult.allWarnings || [];

        // Enhanced logging
        console.log(`AICleaner Card: Zone ${zoneName} validation result:`, {
            status: validationResult.overallStatus,
            recommendation: validationResult.recommendation,
            errors: errors,
            warnings: warnings,
            entityId: entity?.entity_id,
            state: entity?.state
        });

        // Log warnings separately (don't fail validation for warnings)
        if (warnings.length > 0) {
            console.warn(`AICleaner Card: Zone ${zoneName} warnings:`, warnings);
        }

        return { isValid, errors, warnings, validationResult };
    }

    /**
     * Main render method with enhanced state handling
     */
    render() {
        if (!this.shadowRoot) return;

        // Check for various states and render accordingly
        let content;

        if (this.isLoading) {
            content = this.renderLoadingState();
        } else if (this.showErrorState) {
            content = this.renderErrorState();
        } else if (!this._hass || !this._hass.states) {
            content = this.renderConnectionError();
        } else if (!this.zones || this.zones.length === 0) {
            content = this.renderEmptyState();
        } else {
            content = this.renderNormalState();
        }

        this.shadowRoot.innerHTML = `
            ${this.getStyles()}
            <div class="aicleaner-card">
                ${content}
            </div>
        `;

        this.attachEventListeners();

        // Additional fix for setup wizard button
        this.fixSetupWizardButton();

        // Initialize charts if we're on the analytics view
        if (this.currentView === 'analytics') {
            // Delay chart initialization to ensure DOM is ready
            setTimeout(() => this.initializeCharts(), 100);
        }
    }

    /**
     * Render loading state
     */
    renderLoadingState() {
        return `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <div class="loading-message">${this.loadingMessage || 'Loading AICleaner...'}</div>
            </div>
        `;
    }

    /**
     * Render error state
     */
    renderErrorState() {
        return this.showError(
            'Unable to load AICleaner data. Please check the addon status and try again.',
            'this.retryConnection()'
        );
    }

    /**
     * Render connection error state
     */
    renderConnectionError() {
        return this.showError(
            'Home Assistant connection not available. Please check your network connection.',
            'this.retryConnection()'
        );
    }

    /**
     * Render empty state when no zones are configured
     */
    renderEmptyState() {
        // If setup hasn't been completed, show setup wizard
        if (!this.setupWizardData.hasCompletedSetup) {
            return this.showEmptyState(
                'Welcome to AICleaner!',
                'Let\'s get you set up with your first zone. The setup wizard will guide you through configuring cameras, todo lists, and zone settings.',
                'Start Setup Wizard',
                'startSetupWizard'
            );
        }

        // Otherwise show standard empty state
        return this.showEmptyState(
            'No Zones Configured',
            'Get started by configuring zones in the AICleaner addon settings. Zones help organize your cleaning tasks by room or area.',
            'Open Setup Wizard',
            'startSetupWizard'
        );
    }

    /**
     * Render normal state with full UI
     */
    renderNormalState() {
        return `
            ${this.renderHeader()}
            ${this.renderNavigation()}
            ${this.renderContent()}
        `;
    }

    /**
     * Retry connection method
     */
    retryConnection() {
        this.showErrorState = false;
        this.showLoading('Reconnecting to Home Assistant...');

        setTimeout(() => {
            this.hideLoading();
            this.refreshData();
        }, 1000);
    }

    /**
     * Open addon settings (placeholder for future implementation)
     */
    openAddonSettings() {
        this.showToast('Opening addon settings...', 'info');
        // In a real implementation, this would navigate to the addon settings
        // For now, show helpful information
        alert('To configure zones:\n\n1. Go to Settings → Add-ons\n2. Find AICleaner addon\n3. Click Configuration tab\n4. Add your zones and restart the addon');
    }

    /**
     * Start the setup wizard
     */
    startSetupWizard() {
        console.log('🚀 startSetupWizard called successfully!');
        this.currentView = 'setup';
        this.setupWizardStep = 1;
        this.setupWizardData.currentZone = {
            name: '',
            displayName: '',
            camera_entity: '',
            todo_list_entity: '',
            purpose: ''
        };
        this.render();
        this.showToast('Welcome to the AICleaner setup wizard!', 'info');
    }

    /**
     * Debug method for troubleshooting button issues - can be called from console
     */
    debugSetupWizardButton() {
        console.log('🔧 === AICleaner Setup Wizard Debug ===');

        // Check card instance
        console.log('🔧 Card instance:', this);
        console.log('🔧 Card constructor:', this.constructor.name);

        // Check method availability
        console.log('🔧 startSetupWizard method:', {
            exists: typeof this.startSetupWizard === 'function',
            type: typeof this.startSetupWizard,
            method: this.startSetupWizard
        });

        // Check shadow DOM
        console.log('🔧 Shadow root:', this.shadowRoot);

        // Find buttons
        const buttons = this.shadowRoot.querySelectorAll('.empty-action-button');
        console.log('🔧 Found buttons:', buttons);

        buttons.forEach((button, index) => {
            console.log(`🔧 Button ${index}:`, {
                id: button.id,
                textContent: button.textContent,
                dataAction: button.dataset.action,
                dataMethod: button.dataset.method,
                onclick: button.onclick,
                hasClickListener: button.onclick !== null
            });
        });

        // Check pending callbacks
        console.log('🔧 Pending callbacks:', this._pendingButtonCallbacks);

        // Test method call
        try {
            console.log('🔧 Testing direct method call...');
            this.startSetupWizard();
            console.log('✅ Direct method call successful!');
        } catch (error) {
            console.error('❌ Direct method call failed:', error);
        }

        return {
            card: this,
            buttons: buttons,
            hasMethod: typeof this.startSetupWizard === 'function',
            pendingCallbacks: this._pendingButtonCallbacks
        };
    }

    /**
     * Complete the setup wizard
     */
    completeSetupWizard() {
        localStorage.setItem('aicleaner_setup_completed', 'true');
        this.setupWizardData.hasCompletedSetup = true;
        this.currentView = 'dashboard';
        this.render();
        this.showToast('Setup completed! Your zones are now configured.', 'success');
    }

    /**
     * Skip the setup wizard
     */
    skipSetupWizard() {
        localStorage.setItem('aicleaner_setup_completed', 'true');
        this.setupWizardData.hasCompletedSetup = true;
        this.currentView = 'dashboard';
        this.render();
        this.showToast('Setup skipped. You can configure zones manually in addon settings.', 'info');
    }

    /**
     * Render setup wizard
     */
    renderSetupWizard() {
        const totalSteps = 5;
        const progress = Math.round((this.setupWizardStep / totalSteps) * 100);

        return `
            <div class="setup-wizard">
                <div class="setup-header">
                    <h2>AICleaner Setup Wizard</h2>
                    <div class="setup-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${progress}%"></div>
                        </div>
                        <div class="progress-text">Step ${this.setupWizardStep} of ${totalSteps}</div>
                    </div>
                </div>

                <div class="setup-content">
                    ${this.renderSetupStep()}
                </div>

                <div class="setup-actions">
                    ${this.renderSetupActions()}
                </div>
            </div>
        `;
    }

    /**
     * Render current setup step content
     */
    renderSetupStep() {
        switch (this.setupWizardStep) {
            case 1:
                return this.renderSetupWelcome();
            case 2:
                return this.renderSetupZoneBasics();
            case 3:
                return this.renderSetupCameraEntity();
            case 4:
                return this.renderSetupTodoEntity();
            case 5:
                return this.renderSetupReview();
            default:
                return this.renderSetupWelcome();
        }
    }

    /**
     * Render setup wizard actions (Next, Back, Skip buttons)
     */
    renderSetupActions() {
        const isFirstStep = this.setupWizardStep === 1;
        const isLastStep = this.setupWizardStep === 5;

        return `
            <div class="setup-button-group">
                ${!isFirstStep ? `
                    <button class="setup-button secondary" data-action="setup-back">
                        ← Back
                    </button>
                ` : ''}

                <button class="setup-button secondary" data-action="setup-skip">
                    Skip Setup
                </button>

                ${!isLastStep ? `
                    <button class="setup-button primary" data-action="setup-next">
                        Next →
                    </button>
                ` : `
                    <button class="setup-button primary" data-action="setup-complete">
                        Complete Setup
                    </button>
                `}
            </div>
        `;
    }

    /**
     * Render setup welcome step
     */
    renderSetupWelcome() {
        return `
            <div class="setup-step">
                <div class="step-icon">🏠</div>
                <h3>Welcome to AICleaner!</h3>
                <p>This wizard will help you set up your first cleaning zone. A zone represents a room or area in your home that you want to monitor and manage cleaning tasks for.</p>

                <div class="setup-info">
                    <h4>What you'll need:</h4>
                    <ul>
                        <li>📷 A camera entity pointing to the room/area</li>
                        <li>📝 A todo list entity for managing tasks (optional)</li>
                        <li>🎯 A clear purpose for the zone</li>
                    </ul>
                </div>

                <div class="setup-benefits">
                    <h4>What AICleaner will do:</h4>
                    <ul>
                        <li>🤖 Analyze camera images to assess cleanliness</li>
                        <li>📋 Generate and manage cleaning tasks</li>
                        <li>📊 Track completion rates and efficiency</li>
                        <li>🔄 Provide automated cleaning reminders</li>
                    </ul>
                </div>
            </div>
        `;
    }

    /**
     * Render zone basics setup step
     */
    renderSetupZoneBasics() {
        return `
            <div class="setup-step">
                <div class="step-icon">🏷️</div>
                <h3>Zone Information</h3>
                <p>Let's start by giving your zone a name and purpose.</p>

                <div class="setup-form">
                    <div class="form-group">
                        <label for="zone-name">Zone Name</label>
                        <input type="text" id="zone-name" placeholder="e.g., kitchen, living-room, bedroom"
                               value="${this.setupWizardData.currentZone.name}"
                               data-field="name">
                        <small>Use lowercase letters, numbers, and hyphens only</small>
                    </div>

                    <div class="form-group">
                        <label for="zone-display-name">Display Name</label>
                        <input type="text" id="zone-display-name" placeholder="e.g., Kitchen, Living Room, Master Bedroom"
                               value="${this.setupWizardData.currentZone.displayName}"
                               data-field="displayName">
                        <small>This is how the zone will appear in the UI</small>
                    </div>

                    <div class="form-group">
                        <label for="zone-purpose">Purpose</label>
                        <textarea id="zone-purpose" placeholder="e.g., Keep kitchen clean and organized, manage cooking area cleanliness"
                                  data-field="purpose">${this.setupWizardData.currentZone.purpose}</textarea>
                        <small>Describe what this zone is used for - this helps the AI provide better analysis</small>
                    </div>
                </div>

                ${this.renderValidationMessages()}
            </div>
        `;
    }

    /**
     * Render camera entity setup step
     */
    renderSetupCameraEntity() {
        const availableCameras = this.getAvailableCameraEntities();

        return `
            <div class="setup-step">
                <div class="step-icon">📷</div>
                <h3>Camera Configuration</h3>
                <p>Select a camera entity that can see the "${this.setupWizardData.currentZone.displayName || this.setupWizardData.currentZone.name}" area.</p>

                <div class="setup-form">
                    ${availableCameras.length > 0 ? `
                        <div class="form-group">
                            <label>Available Cameras</label>
                            <div class="entity-list">
                                ${availableCameras.map(camera => `
                                    <div class="entity-item ${this.setupWizardData.currentZone.camera_entity === camera.entity_id ? 'selected' : ''}"
                                         data-entity="${camera.entity_id}"
                                         data-action="select-camera">
                                        <div class="entity-info">
                                            <div class="entity-name">${camera.friendly_name || camera.entity_id}</div>
                                            <div class="entity-id">${camera.entity_id}</div>
                                            <div class="entity-state ${camera.state === 'idle' ? 'available' : 'unavailable'}">
                                                ${camera.state === 'idle' ? '✅ Available' : '⚠️ ' + camera.state}
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : `
                        <div class="setup-warning">
                            <div class="warning-icon">⚠️</div>
                            <div class="warning-content">
                                <h4>No Camera Entities Found</h4>
                                <p>No camera entities were detected in your Home Assistant setup.</p>
                                <div class="warning-actions">
                                    <button class="setup-button secondary" data-action="refresh-entities">
                                        🔄 Refresh Entities
                                    </button>
                                </div>
                            </div>
                        </div>
                    `}

                    <div class="form-group">
                        <label for="manual-camera">Or Enter Camera Entity Manually</label>
                        <input type="text" id="manual-camera" placeholder="camera.kitchen"
                               value="${this.setupWizardData.currentZone.camera_entity}"
                               data-field="camera_entity">
                        <small>Enter the full entity ID of your camera</small>
                    </div>
                </div>

                ${this.renderCameraPreview()}
            </div>
        `;
    }

    /**
     * Render todo entity setup step
     */
    renderSetupTodoEntity() {
        const availableTodoLists = this.getAvailableTodoEntities();

        return `
            <div class="setup-step">
                <div class="step-icon">📝</div>
                <h3>Todo List Configuration (Optional)</h3>
                <p>Select a todo list entity to manage cleaning tasks for "${this.setupWizardData.currentZone.displayName || this.setupWizardData.currentZone.name}".</p>

                <div class="setup-form">
                    ${availableTodoLists.length > 0 ? `
                        <div class="form-group">
                            <label>Available Todo Lists</label>
                            <div class="entity-list">
                                ${availableTodoLists.map(todo => `
                                    <div class="entity-item ${this.setupWizardData.currentZone.todo_list_entity === todo.entity_id ? 'selected' : ''}"
                                         data-entity="${todo.entity_id}"
                                         data-action="select-todo">
                                        <div class="entity-info">
                                            <div class="entity-name">${todo.friendly_name || todo.entity_id}</div>
                                            <div class="entity-id">${todo.entity_id}</div>
                                            <div class="entity-state available">✅ Available</div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : `
                        <div class="setup-info">
                            <div class="info-icon">ℹ️</div>
                            <div class="info-content">
                                <h4>No Todo List Entities Found</h4>
                                <p>You can skip this step and configure todo lists later, or create one now.</p>
                                <div class="info-actions">
                                    <button class="setup-button secondary" data-action="create-todo-guide">
                                        📖 How to Create Todo Lists
                                    </button>
                                </div>
                            </div>
                        </div>
                    `}

                    <div class="form-group">
                        <label for="manual-todo">Or Enter Todo List Entity Manually</label>
                        <input type="text" id="manual-todo" placeholder="todo.kitchen_tasks"
                               value="${this.setupWizardData.currentZone.todo_list_entity}"
                               data-field="todo_list_entity">
                        <small>Enter the full entity ID of your todo list (optional)</small>
                    </div>

                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="skip-todo" ${!this.setupWizardData.currentZone.todo_list_entity ? 'checked' : ''}>
                            Skip todo list configuration for now
                        </label>
                        <small>You can add todo list integration later in the addon settings</small>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render setup review step
     */
    renderSetupReview() {
        const zone = this.setupWizardData.currentZone;
        const validation = this.validateSetupData();

        return `
            <div class="setup-step">
                <div class="step-icon">✅</div>
                <h3>Review Configuration</h3>
                <p>Please review your zone configuration before completing setup.</p>

                <div class="setup-review">
                    <div class="review-section">
                        <h4>Zone Information</h4>
                        <div class="review-item">
                            <span class="review-label">Name:</span>
                            <span class="review-value">${zone.name || 'Not set'}</span>
                        </div>
                        <div class="review-item">
                            <span class="review-label">Display Name:</span>
                            <span class="review-value">${zone.displayName || 'Not set'}</span>
                        </div>
                        <div class="review-item">
                            <span class="review-label">Purpose:</span>
                            <span class="review-value">${zone.purpose || 'Not set'}</span>
                        </div>
                    </div>

                    <div class="review-section">
                        <h4>Camera Configuration</h4>
                        <div class="review-item">
                            <span class="review-label">Camera Entity:</span>
                            <span class="review-value ${zone.camera_entity ? 'valid' : 'invalid'}">
                                ${zone.camera_entity || 'Not configured'}
                                ${zone.camera_entity ? '✅' : '❌'}
                            </span>
                        </div>
                    </div>

                    <div class="review-section">
                        <h4>Todo List Configuration</h4>
                        <div class="review-item">
                            <span class="review-label">Todo Entity:</span>
                            <span class="review-value ${zone.todo_list_entity ? 'valid' : 'optional'}">
                                ${zone.todo_list_entity || 'Not configured (optional)'}
                                ${zone.todo_list_entity ? '✅' : 'ℹ️'}
                            </span>
                        </div>
                    </div>
                </div>

                ${validation.isValid ? `
                    <div class="setup-success">
                        <div class="success-icon">🎉</div>
                        <div class="success-content">
                            <h4>Configuration Valid!</h4>
                            <p>Your zone is ready to be created. Click "Complete Setup" to finish.</p>
                        </div>
                    </div>
                ` : `
                    <div class="setup-errors">
                        <div class="error-icon">⚠️</div>
                        <div class="error-content">
                            <h4>Configuration Issues</h4>
                            <ul>
                                ${validation.errors.map(error => `<li>${error}</li>`).join('')}
                            </ul>
                            <p>Please go back and fix these issues before completing setup.</p>
                        </div>
                    </div>
                `}

                <div class="setup-next-steps">
                    <h4>What happens next?</h4>
                    <ul>
                        <li>Your zone configuration will be saved</li>
                        <li>AICleaner will start monitoring the camera</li>
                        <li>You can add more zones in the addon settings</li>
                        <li>Analysis will begin automatically</li>
                    </ul>
                </div>
            </div>
        `;
    }

    /**
     * Get available camera entities from Home Assistant
     */
    getAvailableCameraEntities() {
        if (!this._hass || !this._hass.states) return [];

        return Object.keys(this._hass.states)
            .filter(entityId => entityId.startsWith('camera.'))
            .map(entityId => {
                const entity = this._hass.states[entityId];
                return {
                    entity_id: entityId,
                    friendly_name: entity.attributes.friendly_name,
                    state: entity.state
                };
            })
            .sort((a, b) => (a.friendly_name || a.entity_id).localeCompare(b.friendly_name || b.entity_id));
    }

    /**
     * Get available todo list entities from Home Assistant
     */
    getAvailableTodoEntities() {
        if (!this._hass || !this._hass.states) return [];

        return Object.keys(this._hass.states)
            .filter(entityId => entityId.startsWith('todo.'))
            .map(entityId => {
                const entity = this._hass.states[entityId];
                return {
                    entity_id: entityId,
                    friendly_name: entity.attributes.friendly_name,
                    state: entity.state
                };
            })
            .sort((a, b) => (a.friendly_name || a.entity_id).localeCompare(b.friendly_name || b.entity_id));
    }

    /**
     * Render camera preview if camera entity is selected
     */
    renderCameraPreview() {
        const cameraEntity = this.setupWizardData.currentZone.camera_entity;
        if (!cameraEntity || !this._hass.states[cameraEntity]) {
            return '';
        }

        return `
            <div class="camera-preview">
                <h4>Camera Preview</h4>
                <div class="preview-container">
                    <img src="/api/camera_proxy/${cameraEntity}"
                         alt="Camera preview"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="preview-error" style="display: none;">
                        <div class="error-icon">📷</div>
                        <div class="error-text">Unable to load camera preview</div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render validation messages for current step
     */
    renderValidationMessages() {
        const validation = this.validateCurrentStep();
        if (validation.isValid) return '';

        return `
            <div class="validation-messages">
                <div class="validation-icon">⚠️</div>
                <div class="validation-content">
                    <h4>Please fix the following:</h4>
                    <ul>
                        ${validation.errors.map(error => `<li>${error}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    }

    /**
     * Validate current setup step
     */
    validateCurrentStep() {
        const errors = [];
        const zone = this.setupWizardData.currentZone;

        switch (this.setupWizardStep) {
            case 2: // Zone basics
                if (!zone.name) errors.push('Zone name is required');
                if (zone.name && !/^[a-z0-9_-]+$/.test(zone.name)) {
                    errors.push('Zone name can only contain lowercase letters, numbers, hyphens, and underscores');
                }
                if (!zone.displayName) errors.push('Display name is required');
                break;

            case 3: // Camera entity
                if (!zone.camera_entity) errors.push('Camera entity is required');
                if (zone.camera_entity && !this._hass.states[zone.camera_entity]) {
                    errors.push('Selected camera entity does not exist in Home Assistant');
                }
                break;
        }

        return { isValid: errors.length === 0, errors };
    }

    /**
     * Validate complete setup data
     */
    validateSetupData() {
        const errors = [];
        const zone = this.setupWizardData.currentZone;

        if (!zone.name) errors.push('Zone name is required');
        if (!zone.displayName) errors.push('Display name is required');
        if (!zone.camera_entity) errors.push('Camera entity is required');

        if (zone.camera_entity && !this._hass.states[zone.camera_entity]) {
            errors.push('Camera entity does not exist in Home Assistant');
        }

        if (zone.todo_list_entity && !this._hass.states[zone.todo_list_entity]) {
            errors.push('Todo list entity does not exist in Home Assistant');
        }

        return { isValid: errors.length === 0, errors };
    }

    /**
     * CSS Styles for the card
     */
    getStyles() {
        return `
            <style>
                .aicleaner-card {
                    background: var(--card-background-color, #fff);
                    border-radius: var(--ha-card-border-radius, 12px);
                    box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
                    padding: 16px;
                    font-family: var(--paper-font-body1_-_font-family);
                    color: var(--primary-text-color);
                }
                
                .header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                    padding-bottom: 12px;
                    border-bottom: 1px solid var(--divider-color);
                }
                
                .title {
                    font-size: 1.5em;
                    font-weight: 500;
                    color: var(--primary-text-color);
                }
                
                .system-status {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    font-size: 0.9em;
                    color: var(--secondary-text-color);
                }

                .status-indicator {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: var(--success-color, #4caf50);
                    position: relative;
                    animation: pulse 2s infinite;
                }

                .status-indicator.warning {
                    background: var(--warning-color, #ff9800);
                    animation: pulse-warning 1.5s infinite;
                }

                .status-indicator.error {
                    background: var(--error-color, #f44336);
                    animation: pulse-error 1s infinite;
                }

                .status-indicator.inactive {
                    background: var(--disabled-text-color, #999);
                    animation: none;
                }

                .system-metrics {
                    display: flex;
                    gap: 16px;
                    align-items: center;
                }

                .metric-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 0.85em;
                }

                .metric-icon {
                    font-size: 0.9em;
                    opacity: 0.8;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.6; }
                }

                @keyframes pulse-warning {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.4; }
                }

                @keyframes pulse-error {
                    0%, 100% { opacity: 1; }
                    25%, 75% { opacity: 0.3; }
                }

                .quick-actions-panel {
                    background: var(--card-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 20px;
                }

                .quick-actions-title {
                    font-size: 1.1em;
                    font-weight: 600;
                    margin-bottom: 12px;
                    color: var(--primary-text-color);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .quick-actions-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 12px;
                }

                .quick-action-btn {
                    padding: 16px;
                    border: none;
                    border-radius: 8px;
                    background: var(--secondary-background-color);
                    color: var(--primary-text-color);
                    cursor: pointer;
                    transition: all 0.2s ease;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                    text-align: center;
                    border: 1px solid var(--divider-color);
                }

                .quick-action-btn:hover {
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }

                .quick-action-icon {
                    font-size: 1.5em;
                }

                .quick-action-label {
                    font-size: 0.9em;
                    font-weight: 500;
                }

                .quick-action-desc {
                    font-size: 0.75em;
                    opacity: 0.8;
                    line-height: 1.2;
                }

                .quick-action-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                    transform: none !important;
                    box-shadow: none !important;
                }

                .quick-action-btn:disabled:hover {
                    background: var(--secondary-background-color);
                    color: var(--primary-text-color);
                }

                /* Zone Detail View Styles */
                .zone-detail-header {
                    margin-bottom: 24px;
                }

                .back-button {
                    background: var(--secondary-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    padding: 8px 16px;
                    color: var(--primary-text-color);
                    cursor: pointer;
                    margin-bottom: 16px;
                    font-size: 0.9em;
                    transition: all 0.2s ease;
                }

                .back-button:hover {
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                }

                .zone-detail-title {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                }

                .zone-detail-icon {
                    font-size: 2.5em;
                }

                .zone-detail-title h2 {
                    margin: 0;
                    font-size: 1.8em;
                    color: var(--primary-text-color);
                }

                .zone-purpose {
                    margin: 4px 0 0 0;
                    color: var(--secondary-text-color);
                    font-style: italic;
                }

                .zone-detail-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    grid-template-rows: auto auto;
                    gap: 20px;
                }

                .zone-stats-panel,
                .zone-tasks-panel,
                .zone-controls-panel {
                    background: var(--card-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 12px;
                    padding: 20px;
                }

                .zone-tasks-panel {
                    grid-row: span 2;
                }

                .zone-detail-grid h3 {
                    margin: 0 0 16px 0;
                    font-size: 1.1em;
                    color: var(--primary-text-color);
                }

                .stats-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 16px;
                }

                .stat-card {
                    background: var(--secondary-background-color);
                    border-radius: 8px;
                    padding: 16px;
                    text-align: center;
                }

                .stat-value {
                    font-size: 1.8em;
                    font-weight: 700;
                    color: var(--primary-color);
                    margin-bottom: 4px;
                }

                .stat-label {
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .last-analysis-info {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 0.9em;
                    color: var(--secondary-text-color);
                    background: var(--secondary-background-color);
                    padding: 12px;
                    border-radius: 8px;
                }

                /* Task List Styles */
                .no-tasks {
                    text-align: center;
                    padding: 40px 20px;
                    color: var(--secondary-text-color);
                }

                .no-tasks-icon {
                    font-size: 3em;
                    margin-bottom: 12px;
                }

                .no-tasks-text {
                    font-size: 1.2em;
                    font-weight: 500;
                    margin-bottom: 4px;
                }

                .no-tasks-desc {
                    font-size: 0.9em;
                    opacity: 0.8;
                }

                .task-list {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    max-height: 400px;
                    overflow-y: auto;
                }

                .task-item {
                    background: var(--secondary-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    padding: 16px;
                    transition: all 0.2s ease;
                }

                .task-item:hover {
                    border-color: var(--primary-color);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }

                .task-content {
                    margin-bottom: 12px;
                }

                .task-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 6px;
                }

                .task-priority {
                    font-size: 0.9em;
                }

                .task-description {
                    flex: 1;
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .task-meta {
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                }

                .task-actions {
                    display: flex;
                    gap: 8px;
                }

                .task-action-btn {
                    flex: 1;
                    padding: 8px 12px;
                    border: none;
                    border-radius: 6px;
                    font-size: 0.8em;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .task-action-btn.complete {
                    background: var(--success-color, #4caf50);
                    color: white;
                }

                .task-action-btn.dismiss {
                    background: var(--secondary-background-color);
                    color: var(--secondary-text-color);
                    border: 1px solid var(--divider-color);
                }

                .task-action-btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.15);
                }

                /* Zone Controls Styles */
                .zone-controls {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                .control-btn {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px;
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    background: var(--secondary-background-color);
                    color: var(--primary-text-color);
                    cursor: pointer;
                    transition: all 0.2s ease;
                    text-align: left;
                }

                .control-btn:hover {
                    border-color: var(--primary-color);
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                    transform: translateY(-1px);
                }

                .control-btn.primary {
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                    border-color: var(--primary-color);
                }

                .control-icon {
                    font-size: 1.2em;
                    min-width: 24px;
                }

                .control-content {
                    flex: 1;
                }

                .control-label {
                    font-weight: 500;
                    margin-bottom: 2px;
                }

                .control-desc {
                    font-size: 0.8em;
                    opacity: 0.8;
                }

                /* Configuration Panel Styles */
                .config-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                }

                .config-section {
                    background: var(--card-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 12px;
                    padding: 20px;
                }

                .config-section h3 {
                    margin: 0 0 16px 0;
                    font-size: 1.1em;
                    color: var(--primary-text-color);
                }

                .personality-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 12px;
                    margin-bottom: 16px;
                }

                .personality-card {
                    background: var(--secondary-background-color);
                    border: 2px solid var(--divider-color);
                    border-radius: 8px;
                    padding: 16px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .personality-card:hover {
                    border-color: var(--primary-color);
                    transform: translateY(-2px);
                }

                .personality-card.selected {
                    border-color: var(--primary-color);
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                }

                .personality-icon {
                    font-size: 1.5em;
                    margin-bottom: 8px;
                }

                .personality-name {
                    font-weight: 500;
                    margin-bottom: 4px;
                }

                .personality-desc {
                    font-size: 0.8em;
                    opacity: 0.8;
                }

                .config-input-group {
                    margin-bottom: 16px;
                }

                .config-label {
                    display: block;
                    margin-bottom: 6px;
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .config-input {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid var(--divider-color);
                    border-radius: 6px;
                    background: var(--secondary-background-color);
                    color: var(--primary-text-color);
                    font-size: 0.9em;
                }

                .config-input:focus {
                    outline: none;
                    border-color: var(--primary-color);
                }

                .config-checkbox {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 12px;
                }

                .config-checkbox input {
                    width: auto;
                }

                .ignore-rule-item {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px;
                    background: var(--secondary-background-color);
                    border-radius: 6px;
                    margin-bottom: 8px;
                }

                .ignore-rule-text {
                    flex: 1;
                    font-size: 0.9em;
                }

                .remove-rule-btn {
                    background: var(--error-color, #f44336);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 8px;
                    cursor: pointer;
                    font-size: 0.8em;
                }

                .add-rule-form {
                    display: flex;
                    gap: 8px;
                    margin-top: 12px;
                }

                .add-rule-input {
                    flex: 1;
                }

                .add-rule-btn {
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                    border: none;
                    border-radius: 6px;
                    padding: 10px 16px;
                    cursor: pointer;
                    font-size: 0.9em;
                }

                /* Analytics Dashboard Styles */
                .analytics-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                    gap: 20px;
                }

                .analytics-section {
                    background: var(--card-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 12px;
                    padding: 20px;
                }

                .analytics-section h3 {
                    margin: 0 0 16px 0;
                    font-size: 1.1em;
                    color: var(--primary-text-color);
                }

                .chart-container {
                    position: relative;
                    height: 300px;
                    width: 100%;
                }

                .chart-container canvas {
                    max-height: 100%;
                    max-width: 100%;
                }

                .insights-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                    gap: 16px;
                }

                .insight-card {
                    background: var(--secondary-background-color);
                    border-radius: 8px;
                    padding: 16px;
                    text-align: center;
                }

                .insight-value {
                    font-size: 1.8em;
                    font-weight: 700;
                    color: var(--primary-color);
                    margin-bottom: 4px;
                }

                .insight-label {
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .insight-trend {
                    font-size: 0.75em;
                    margin-top: 4px;
                }

                .insight-trend.up {
                    color: var(--success-color, #4caf50);
                }

                .insight-trend.down {
                    color: var(--error-color, #f44336);
                }

                .insight-trend.neutral {
                    color: var(--secondary-text-color);
                }
                
                .navigation {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 16px;
                }
                
                .nav-button {
                    padding: 8px 16px;
                    border: none;
                    border-radius: 20px;
                    background: var(--secondary-background-color);
                    color: var(--secondary-text-color);
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9em;
                }
                
                .nav-button:hover {
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                }
                
                .nav-button.active {
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                }
                
                .content {
                    min-height: 200px;
                }
                
                .zone-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 16px;
                    margin-top: 8px;
                }

                .zone-card {
                    background: var(--card-background-color);
                    border: 1px solid var(--divider-color);
                    border-radius: 12px;
                    padding: 20px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }

                .zone-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                    border-color: var(--primary-color);
                }

                .zone-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: linear-gradient(90deg, var(--primary-color), var(--accent-color, var(--primary-color)));
                }

                /* Error zone card styles */
                .zone-card-error {
                    border-color: var(--error-color, #ff5722);
                    background: var(--error-background-color, rgba(255, 87, 34, 0.05));
                }

                .zone-card-error::before {
                    background: var(--error-color, #ff5722);
                }

                .zone-card-error:hover {
                    border-color: var(--error-color, #ff5722);
                    box-shadow: 0 8px 24px rgba(255, 87, 34, 0.2);
                }

                .error-badge {
                    background: var(--error-color, #ff5722);
                    color: white;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 0.8em;
                    font-weight: 500;
                    margin-left: auto;
                }

                .zone-error-content {
                    padding: 12px 0;
                }

                .error-message {
                    margin-bottom: 16px;
                    color: var(--error-text-color, #d32f2f);
                }

                .error-list {
                    margin: 8px 0 0 16px;
                    padding: 0;
                    color: var(--secondary-text-color);
                }

                .error-list li {
                    margin-bottom: 4px;
                    font-size: 0.9em;
                }

                .zone-error-actions {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }

                .action-button.error {
                    background: var(--error-color, #ff5722);
                    color: white;
                }

                .action-button.error:hover {
                    background: var(--error-color-dark, #e64a19);
                }

                .zone-name {
                    font-size: 1.3em;
                    font-weight: 600;
                    margin-bottom: 12px;
                    color: var(--primary-text-color);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .zone-icon {
                    font-size: 1.1em;
                    opacity: 0.8;
                }

                .zone-stats {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 16px;
                }

                .stat-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 12px;
                    background: var(--secondary-background-color);
                    border-radius: 8px;
                    transition: background 0.2s ease;
                }

                .stat-number {
                    font-size: 1.8em;
                    font-weight: 700;
                    line-height: 1;
                    margin-bottom: 4px;
                }

                .stat-label {
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .stat-item.active .stat-number { color: var(--warning-color, #ff9800); }
                .stat-item.completed .stat-number { color: var(--success-color, #4caf50); }
                
                .zone-progress {
                    margin-bottom: 16px;
                }

                .progress-bar {
                    width: 100%;
                    height: 6px;
                    background: var(--divider-color);
                    border-radius: 3px;
                    overflow: hidden;
                    margin-bottom: 6px;
                }

                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, var(--success-color), var(--primary-color));
                    transition: width 0.3s ease;
                }

                .progress-text {
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                    text-align: center;
                }

                .efficiency-score {
                    font-size: 0.75em;
                    color: var(--primary-color);
                    text-align: center;
                    margin-top: 4px;
                    font-weight: 500;
                }

                .efficiency-icon {
                    margin-right: 4px;
                }

                .cleanliness-score {
                    margin-top: 8px;
                    padding: 8px;
                    background: var(--card-background-color, #fff);
                    border-radius: 8px;
                    border: 1px solid var(--divider-color);
                }

                .cleanliness-header {
                    display: flex;
                    align-items: center;
                    margin-bottom: 6px;
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                }

                .cleanliness-icon {
                    margin-right: 6px;
                    font-size: 1.1em;
                }

                .cleanliness-details {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    flex-wrap: wrap;
                    gap: 8px;
                }

                .score-display {
                    display: flex;
                    align-items: baseline;
                    gap: 2px;
                }

                .score-number {
                    font-size: 1.4em;
                    font-weight: bold;
                }

                .score-max {
                    font-size: 0.9em;
                    color: var(--secondary-text-color);
                }

                .score-state {
                    font-size: 0.85em;
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .confidence-level {
                    font-size: 0.75em;
                    color: var(--secondary-text-color);
                }

                .last-analysis {
                    font-size: 0.85em;
                    color: var(--secondary-text-color);
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    margin-bottom: 16px;
                    padding: 8px;
                    background: var(--secondary-background-color);
                    border-radius: 6px;
                }

                .analysis-icon {
                    opacity: 0.7;
                }
                
                .quick-actions {
                    display: flex;
                    gap: 8px;
                    margin-top: 12px;
                }
                
                .action-button {
                    flex: 1;
                    padding: 12px 16px;
                    border: none;
                    border-radius: 8px;
                    background: var(--primary-color);
                    color: var(--text-primary-color);
                    cursor: pointer;
                    font-size: 0.85em;
                    font-weight: 500;
                    transition: all 0.2s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 6px;
                }

                .action-button:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }

                .action-button.secondary {
                    background: var(--secondary-background-color);
                    color: var(--primary-text-color);
                    border: 1px solid var(--divider-color);
                }

                .action-button.secondary:hover {
                    background: var(--divider-color);
                }

                .button-icon {
                    font-size: 0.9em;
                }
                
                @media (max-width: 768px) {
                    .zone-grid {
                        grid-template-columns: 1fr;
                    }

                    .navigation {
                        flex-wrap: wrap;
                    }

                    .nav-button {
                        flex: 1;
                        min-width: 80px;
                    }

                    .system-metrics {
                        flex-direction: column;
                        gap: 8px;
                        align-items: flex-start;
                    }

                    .quick-actions-grid {
                        grid-template-columns: 1fr 1fr;
                    }

                    .zone-detail-grid {
                        grid-template-columns: 1fr;
                        grid-template-rows: auto;
                    }

                    .zone-tasks-panel {
                        grid-row: auto;
                    }

                    .stats-grid {
                        grid-template-columns: 1fr 1fr;
                    }

                    .task-actions {
                        flex-direction: column;
                    }

                    .zone-detail-title {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 12px;
                    }

                    .zone-detail-icon {
                        font-size: 2em;
                    }
                }

                @media (max-width: 480px) {
                    .quick-actions-grid {
                        grid-template-columns: 1fr;
                    }

                    .stats-grid {
                        grid-template-columns: 1fr;
                    }

                    .system-metrics {
                        display: none;
                    }

                    .zone-card {
                        padding: 16px;
                    }

                    .zone-stats {
                        grid-template-columns: 1fr;
                        gap: 8px;
                    }
                }

                /* Mobile-specific styles */
                @media (max-width: 768px) {
                    .aicleaner-card {
                        padding: 12px;
                        margin: 0;
                        border-radius: 8px;
                    }

                    .header {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 8px;
                        margin-bottom: 12px;
                    }

                    .title {
                        font-size: 1.3em;
                    }

                    .system-status {
                        font-size: 0.8em;
                        gap: 8px;
                    }

                    .navigation {
                        flex-wrap: wrap;
                        gap: 4px;
                    }

                    .nav-button {
                        min-height: 44px; /* Touch-friendly size */
                        padding: 8px 12px;
                        font-size: 0.9em;
                        flex: 1;
                        min-width: 80px;
                    }

                    .zones-grid {
                        grid-template-columns: 1fr;
                        gap: 12px;
                    }

                    .zone-card {
                        padding: 12px;
                        min-height: 120px;
                    }

                    .zone-header {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 4px;
                    }

                    .zone-name {
                        font-size: 1.1em;
                    }

                    .zone-stats {
                        grid-template-columns: 1fr 1fr;
                        gap: 8px;
                        margin-top: 8px;
                    }

                    .stat-item {
                        padding: 6px;
                        font-size: 0.8em;
                    }

                    .analytics-grid {
                        grid-template-columns: 1fr;
                        gap: 12px;
                    }

                    .chart-container {
                        height: 200px;
                    }

                    .config-section {
                        padding: 12px;
                        margin-bottom: 12px;
                    }

                    .form-group {
                        margin-bottom: 12px;
                    }

                    .form-group label {
                        font-size: 0.9em;
                        margin-bottom: 4px;
                    }

                    .form-group input,
                    .form-group select,
                    .form-group textarea {
                        min-height: 44px; /* Touch-friendly */
                        font-size: 16px; /* Prevent zoom on iOS */
                        padding: 8px 12px;
                    }

                    .button-group {
                        flex-direction: column;
                        gap: 8px;
                    }

                    .button-group button {
                        min-height: 44px;
                        width: 100%;
                    }

                    /* Mobile swipe indicators */
                    .swipe-indicator {
                        position: absolute;
                        top: 50%;
                        transform: translateY(-50%);
                        width: 20px;
                        height: 40px;
                        background: rgba(0,0,0,0.1);
                        border-radius: 10px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: rgba(0,0,0,0.3);
                        font-size: 12px;
                        z-index: 10;
                        pointer-events: none;
                        opacity: 0;
                        transition: opacity 0.3s ease;
                    }

                    .swipe-indicator.left {
                        left: 5px;
                    }

                    .swipe-indicator.right {
                        right: 5px;
                    }

                    .aicleaner-card:hover .swipe-indicator {
                        opacity: 1;
                    }

                    /* Touch feedback */
                    .nav-button:active,
                    .zone-card:active,
                    .button:active {
                        transform: scale(0.98);
                        transition: transform 0.1s ease;
                    }

                    /* Improved scrolling on mobile */
                    .scrollable-content {
                        -webkit-overflow-scrolling: touch;
                        scroll-behavior: smooth;
                    }

                    /* Hide desktop-only elements on mobile */
                    .desktop-only {
                        display: none !important;
                    }

                    /* Enhanced mobile touch interactions */
                    .touch-active {
                        background: var(--primary-color-light, rgba(25, 118, 210, 0.1)) !important;
                        transform: scale(0.98);
                    }

                    .touch-ripple {
                        position: absolute;
                        border-radius: 50%;
                        background: rgba(255, 255, 255, 0.3);
                        transform: scale(0);
                        animation: ripple 0.6s linear;
                        pointer-events: none;
                        z-index: 1;
                    }

                    @keyframes ripple {
                        to {
                            transform: scale(4);
                            opacity: 0;
                        }
                    }

                    /* Mobile-optimized navigation */
                    .navigation {
                        position: sticky;
                        top: 0;
                        background: var(--card-background-color);
                        z-index: 10;
                        padding: 8px 0;
                        margin: 0 -12px 16px -12px;
                        padding-left: 12px;
                        padding-right: 12px;
                        border-bottom: 1px solid var(--divider-color);
                    }

                    .nav-buttons {
                        scrollbar-width: none;
                        -ms-overflow-style: none;
                    }

                    .nav-buttons::-webkit-scrollbar {
                        display: none;
                    }

                    /* Mobile-optimized zone cards */
                    .zone-card {
                        border-radius: 16px;
                        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                        position: relative;
                        overflow: hidden;
                    }

                    .zone-card:active {
                        transform: scale(0.97);
                        box-shadow: 0 1px 6px rgba(0,0,0,0.12);
                    }

                    /* Mobile-optimized buttons */
                    .action-button {
                        min-height: 44px;
                        border-radius: 12px;
                        font-weight: 500;
                        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
                    }

                    .action-button:active {
                        transform: scale(0.95);
                    }

                    /* Mobile-optimized forms */
                    input, textarea, select {
                        min-height: 44px;
                        font-size: 16px; /* Prevents zoom on iOS */
                        border-radius: 8px;
                        padding: 12px;
                    }

                    /* Mobile-optimized modals */
                    .modal-content {
                        margin: 20px;
                        max-height: calc(100vh - 40px);
                        border-radius: 16px;
                        overflow-y: auto;
                    }

                    /* Pull-to-refresh indicator */
                    .pull-to-refresh {
                        position: absolute;
                        top: -60px;
                        left: 50%;
                        transform: translateX(-50%);
                        padding: 10px 20px;
                        background: var(--primary-color);
                        color: white;
                        border-radius: 20px;
                        font-size: 0.9em;
                        opacity: 0;
                        transition: all 0.3s ease;
                    }

                    .pull-to-refresh.active {
                        opacity: 1;
                        top: 10px;
                    }
                }

                /* Tablet-specific styles */
                @media (min-width: 769px) and (max-width: 1024px) {
                    .zones-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }

                    .analytics-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }

                /* Mobile landscape orientation */
                @media (max-width: 768px) and (orientation: landscape) {
                    .zones-grid {
                        grid-template-columns: repeat(2, 1fr);
                        gap: 8px;
                    }

                    .zone-card {
                        min-height: 100px;
                        padding: 8px;
                    }

                    .header {
                        flex-direction: row;
                        align-items: center;
                    }
                }

                /* Loading, Error, and Empty States */
                .loading-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 40px 20px;
                    text-align: center;
                    color: var(--secondary-text-color);
                }

                .loading-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid var(--divider-color);
                    border-top: 3px solid var(--primary-color);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 16px;
                }

                .loading-message {
                    font-size: 0.9em;
                    margin-top: 8px;
                }

                .error-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 40px 20px;
                    text-align: center;
                    color: var(--error-text-color, #d32f2f);
                }

                .error-icon {
                    font-size: 3em;
                    margin-bottom: 16px;
                    opacity: 0.7;
                }

                .error-title {
                    font-size: 1.2em;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: var(--primary-text-color);
                }

                .error-message {
                    font-size: 0.9em;
                    line-height: 1.4;
                    margin-bottom: 20px;
                    max-width: 300px;
                }

                .retry-button {
                    background: var(--primary-color);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.9em;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    transition: background 0.2s ease;
                }

                .retry-button:hover {
                    background: var(--primary-color-dark, #1565c0);
                }

                .retry-icon {
                    font-size: 1em;
                }

                .empty-state {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 40px 20px;
                    text-align: center;
                    color: var(--secondary-text-color);
                }

                .empty-icon {
                    font-size: 3em;
                    margin-bottom: 16px;
                    opacity: 0.5;
                }

                .empty-title {
                    font-size: 1.2em;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: var(--primary-text-color);
                }

                .empty-message {
                    font-size: 0.9em;
                    line-height: 1.4;
                    margin-bottom: 20px;
                    max-width: 300px;
                }

                .empty-action-button {
                    background: var(--primary-color);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.9em;
                    transition: background 0.2s ease;
                }

                .empty-action-button:hover {
                    background: var(--primary-color-dark, #1565c0);
                }

                /* Loading overlay for buttons */
                .button-loading {
                    position: relative;
                    pointer-events: none;
                    opacity: 0.7;
                }

                .button-loading::after {
                    content: '';
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 16px;
                    height: 16px;
                    border: 2px solid transparent;
                    border-top: 2px solid currentColor;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                /* Connection status indicator */
                .connection-status {
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: var(--success-color, #4caf50);
                    transition: background 0.3s ease;
                }

                .connection-status.disconnected {
                    background: var(--error-color, #f44336);
                    animation: pulse 2s infinite;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                /* Enhanced Accessibility improvements */
                .sr-only {
                    position: absolute;
                    width: 1px;
                    height: 1px;
                    padding: 0;
                    margin: -1px;
                    overflow: hidden;
                    clip: rect(0, 0, 0, 0);
                    white-space: nowrap;
                    border: 0;
                }

                /* Enhanced Focus indicators */
                button:focus,
                .action-button:focus,
                .nav-button:focus,
                .zone-card:focus,
                .entity-item:focus,
                .setup-button:focus {
                    outline: 3px solid var(--primary-color);
                    outline-offset: 2px;
                    box-shadow: 0 0 0 1px var(--card-background-color);
                }

                /* Focus visible for keyboard navigation */
                button:focus-visible,
                .action-button:focus-visible,
                .nav-button:focus-visible {
                    outline: 3px solid var(--focus-color, #4285f4);
                    outline-offset: 2px;
                }

                /* Keyboard navigation support */
                [tabindex="0"]:focus,
                [tabindex="-1"]:focus {
                    outline: 2px solid var(--primary-color);
                    outline-offset: 1px;
                }

                /* High contrast mode enhancements */
                @media (prefers-contrast: high) {
                    button:focus,
                    .action-button:focus,
                    .nav-button:focus {
                        outline-width: 4px;
                        outline-color: ButtonText;
                    }

                    .zone-card {
                        border-width: 3px;
                    }
                }

                /* Reduced motion support */
                @media (prefers-reduced-motion: reduce) {
                    * {
                        animation-duration: 0.01ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                    }

                    .touch-ripple {
                        animation: none;
                    }
                }

                /* High contrast mode support */
                @media (prefers-contrast: high) {
                    .zone-card {
                        border-width: 2px;
                    }

                    .error-state,
                    .empty-state {
                        border: 2px solid var(--divider-color);
                        border-radius: 8px;
                    }
                }

                /* Setup Wizard Styles */
                .setup-wizard {
                    padding: 20px;
                    max-width: 600px;
                    margin: 0 auto;
                }

                .setup-header {
                    text-align: center;
                    margin-bottom: 30px;
                }

                .setup-header h2 {
                    margin: 0 0 20px 0;
                    color: var(--primary-text-color);
                    font-size: 1.5em;
                }

                .setup-progress {
                    margin-bottom: 10px;
                }

                .progress-bar {
                    width: 100%;
                    height: 8px;
                    background: var(--divider-color);
                    border-radius: 4px;
                    overflow: hidden;
                    margin-bottom: 8px;
                }

                .progress-fill {
                    height: 100%;
                    background: linear-gradient(90deg, var(--primary-color), var(--accent-color, var(--primary-color)));
                    transition: width 0.3s ease;
                }

                .progress-text {
                    font-size: 0.9em;
                    color: var(--secondary-text-color);
                }

                .setup-content {
                    margin-bottom: 30px;
                }

                .setup-step {
                    text-align: center;
                }

                .step-icon {
                    font-size: 3em;
                    margin-bottom: 20px;
                }

                .setup-step h3 {
                    margin: 0 0 15px 0;
                    color: var(--primary-text-color);
                    font-size: 1.3em;
                }

                .setup-step p {
                    color: var(--secondary-text-color);
                    line-height: 1.5;
                    margin-bottom: 25px;
                }

                .setup-info,
                .setup-benefits {
                    background: var(--card-background-color, #f5f5f5);
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                    text-align: left;
                }

                .setup-info h4,
                .setup-benefits h4 {
                    margin: 0 0 10px 0;
                    color: var(--primary-text-color);
                    font-size: 1.1em;
                }

                .setup-info ul,
                .setup-benefits ul {
                    margin: 0;
                    padding-left: 20px;
                    color: var(--secondary-text-color);
                }

                .setup-info li,
                .setup-benefits li {
                    margin-bottom: 8px;
                    line-height: 1.4;
                }

                .setup-form {
                    text-align: left;
                    max-width: 500px;
                    margin: 0 auto;
                }

                .form-group {
                    margin-bottom: 20px;
                }

                .form-group label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .form-group input,
                .form-group textarea {
                    width: 100%;
                    padding: 10px;
                    border: 1px solid var(--divider-color);
                    border-radius: 4px;
                    font-size: 0.9em;
                    background: var(--card-background-color, white);
                    color: var(--primary-text-color);
                    box-sizing: border-box;
                }

                .form-group textarea {
                    height: 80px;
                    resize: vertical;
                }

                .form-group small {
                    display: block;
                    margin-top: 5px;
                    color: var(--secondary-text-color);
                    font-size: 0.8em;
                }

                .entity-list {
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    overflow: hidden;
                    margin-bottom: 15px;
                }

                .entity-item {
                    padding: 15px;
                    border-bottom: 1px solid var(--divider-color);
                    cursor: pointer;
                    transition: background 0.2s ease;
                }

                .entity-item:last-child {
                    border-bottom: none;
                }

                .entity-item:hover {
                    background: var(--hover-color, rgba(0,0,0,0.05));
                }

                .entity-item.selected {
                    background: var(--primary-color-light, rgba(25, 118, 210, 0.1));
                    border-left: 4px solid var(--primary-color);
                }

                .entity-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .entity-name {
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .entity-id {
                    font-size: 0.8em;
                    color: var(--secondary-text-color);
                    font-family: monospace;
                }

                .entity-state {
                    font-size: 0.8em;
                    font-weight: 500;
                }

                .entity-state.available {
                    color: var(--success-color, #4caf50);
                }

                .entity-state.unavailable {
                    color: var(--warning-color, #ff9800);
                }

                .setup-warning,
                .setup-info,
                .setup-success,
                .setup-errors {
                    display: flex;
                    align-items: flex-start;
                    gap: 15px;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }

                .setup-warning {
                    background: var(--warning-background, rgba(255, 152, 0, 0.1));
                    border: 1px solid var(--warning-color, #ff9800);
                }

                .setup-success {
                    background: var(--success-background, rgba(76, 175, 80, 0.1));
                    border: 1px solid var(--success-color, #4caf50);
                }

                .setup-errors {
                    background: var(--error-background, rgba(244, 67, 54, 0.1));
                    border: 1px solid var(--error-color, #f44336);
                }

                .warning-icon,
                .success-icon,
                .error-icon,
                .info-icon {
                    font-size: 1.5em;
                    flex-shrink: 0;
                }

                .warning-content,
                .success-content,
                .error-content,
                .info-content {
                    flex: 1;
                }

                .warning-content h4,
                .success-content h4,
                .error-content h4,
                .info-content h4 {
                    margin: 0 0 8px 0;
                    color: var(--primary-text-color);
                }

                .camera-preview {
                    margin-top: 20px;
                    text-align: center;
                }

                .camera-preview h4 {
                    margin-bottom: 10px;
                    color: var(--primary-text-color);
                }

                .preview-container {
                    border: 1px solid var(--divider-color);
                    border-radius: 8px;
                    overflow: hidden;
                    max-width: 300px;
                    margin: 0 auto;
                }

                .preview-container img {
                    width: 100%;
                    height: auto;
                    display: block;
                }

                .preview-error {
                    padding: 40px 20px;
                    text-align: center;
                    color: var(--secondary-text-color);
                }

                .setup-review {
                    text-align: left;
                    margin: 20px 0;
                }

                .review-section {
                    margin-bottom: 25px;
                    padding: 15px;
                    background: var(--card-background-color, #f9f9f9);
                    border-radius: 8px;
                }

                .review-section h4 {
                    margin: 0 0 15px 0;
                    color: var(--primary-text-color);
                    font-size: 1.1em;
                }

                .review-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                    padding: 8px 0;
                    border-bottom: 1px solid var(--divider-color);
                }

                .review-item:last-child {
                    border-bottom: none;
                    margin-bottom: 0;
                }

                .review-label {
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .review-value {
                    color: var(--secondary-text-color);
                    text-align: right;
                    max-width: 60%;
                    word-break: break-word;
                }

                .review-value.valid {
                    color: var(--success-color, #4caf50);
                }

                .review-value.invalid {
                    color: var(--error-color, #f44336);
                }

                .review-value.optional {
                    color: var(--info-color, #2196f3);
                }

                .setup-next-steps {
                    background: var(--info-background, rgba(33, 150, 243, 0.1));
                    border: 1px solid var(--info-color, #2196f3);
                    border-radius: 8px;
                    padding: 20px;
                    margin-top: 20px;
                    text-align: left;
                }

                .setup-next-steps h4 {
                    margin: 0 0 10px 0;
                    color: var(--primary-text-color);
                }

                .setup-next-steps ul {
                    margin: 0;
                    padding-left: 20px;
                    color: var(--secondary-text-color);
                }

                .setup-actions {
                    text-align: center;
                    padding-top: 20px;
                    border-top: 1px solid var(--divider-color);
                }

                .setup-button-group {
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .setup-button {
                    padding: 12px 24px;
                    border: none;
                    border-radius: 6px;
                    font-size: 0.9em;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    min-width: 100px;
                }

                .setup-button.primary {
                    background: var(--primary-color);
                    color: white;
                }

                .setup-button.primary:hover {
                    background: var(--primary-color-dark, #1565c0);
                }

                .setup-button.secondary {
                    background: var(--card-background-color, #f5f5f5);
                    color: var(--primary-text-color);
                    border: 1px solid var(--divider-color);
                }

                .setup-button.secondary:hover {
                    background: var(--hover-color, rgba(0,0,0,0.05));
                }

                .validation-messages {
                    display: flex;
                    align-items: flex-start;
                    gap: 15px;
                    padding: 15px;
                    background: var(--warning-background, rgba(255, 152, 0, 0.1));
                    border: 1px solid var(--warning-color, #ff9800);
                    border-radius: 8px;
                    margin-top: 20px;
                }

                .validation-icon {
                    font-size: 1.2em;
                    flex-shrink: 0;
                }

                .validation-content h4 {
                    margin: 0 0 8px 0;
                    color: var(--primary-text-color);
                    font-size: 1em;
                }

                .validation-content ul {
                    margin: 0;
                    padding-left: 20px;
                    color: var(--secondary-text-color);
                }

                /* Mobile responsiveness for setup wizard */
                @media (max-width: 768px) {
                    .setup-wizard {
                        padding: 15px;
                    }

                    .setup-button-group {
                        flex-direction: column;
                        align-items: center;
                    }

                    .setup-button {
                        width: 100%;
                        max-width: 200px;
                    }

                    .entity-item {
                        padding: 12px;
                    }

                    .review-item {
                        flex-direction: column;
                        align-items: flex-start;
                        gap: 5px;
                    }

                    .review-value {
                        max-width: 100%;
                        text-align: left;
                    }
                }
            </style>
        `;
    }

    /**
     * Render the card header
     */
    renderHeader() {
        const status = this.systemStatus.status || 'inactive';
        const statusClass = status === 'active' ? '' :
                           status === 'busy' ? 'warning' :
                           status === 'warning' ? 'warning' :
                           status === 'inactive' ? 'inactive' : 'error';

        const statusText = {
            'active': 'System Active',
            'busy': 'System Busy',
            'warning': 'Needs Attention',
            'error': 'System Error',
            'inactive': 'System Inactive'
        }[status] || 'Unknown Status';

        const lastAnalysis = this.systemStatus.lastGlobalAnalysis ?
            this.formatRelativeTime(new Date(this.systemStatus.lastGlobalAnalysis)) : 'Never';

        return `
            <div class="header">
                <div class="title">${this._config.title}</div>
                <div class="system-status">
                    <div class="status-indicator ${statusClass}" title="${statusText}"></div>
                    <div class="system-metrics">
                        <div class="metric-item">
                            <span class="metric-icon">🏠</span>
                            <span>${this.systemStatus.totalZones || 0} zones</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-icon">📋</span>
                            <span>${this.systemStatus.totalActiveTasks || 0} active</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-icon">✅</span>
                            <span>${this.systemStatus.totalCompletedTasks || 0} completed</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-icon">🕒</span>
                            <span>${lastAnalysis}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render navigation buttons with enhanced accessibility
     */
    renderNavigation() {
        const views = [
            { id: 'dashboard', label: 'Dashboard', icon: '🏠', description: 'Zone overview and status' },
            { id: 'analytics', label: 'Analytics', icon: '📊', description: 'Performance metrics and charts' },
            { id: 'config', label: 'Settings', icon: '⚙️', description: 'Configuration and preferences' }
        ];

        return `
            <nav class="navigation" role="navigation" aria-label="AICleaner main navigation">
                <div class="nav-buttons" role="tablist">
                    ${views.map(view => `
                        <button class="nav-button ${this.currentView === view.id ? 'active' : ''}"
                                data-view="${view.id}"
                                role="tab"
                                aria-selected="${this.currentView === view.id}"
                                aria-controls="${view.id}-panel"
                                tabindex="${this.currentView === view.id ? '0' : '-1'}"
                                aria-label="${view.label} - ${view.description}">
                            <span class="nav-icon" aria-hidden="true">${view.icon}</span>
                            <span class="nav-text">${view.label}</span>
                            <span class="sr-only">${view.description}</span>
                        </button>
                    `).join('')}
                </div>
            </nav>
        `;
    }

    /**
     * Render main content based on current view
     */
    renderContent() {
        switch (this.currentView) {
            case 'dashboard':
                return this.renderDashboard();
            case 'zone':
                return this.renderZoneDetail();
            case 'analytics':
                return this.renderAnalytics();
            case 'config':
                return this.renderConfig();
            case 'setup':
                return this.renderSetupWizard();
            default:
                return this.renderDashboard();
        }
    }

    /**
     * Render dashboard view with zone overview
     */
    renderDashboard() {
        if (!this.zones || this.zones.length === 0) {
            return `
                <div class="content">
                    <div style="text-align: center; padding: 40px; color: var(--secondary-text-color);">
                        <div style="font-size: 3em; margin-bottom: 16px;">🏠</div>
                        <div style="font-size: 1.2em; margin-bottom: 8px;">No zones configured</div>
                        <div>Add zones in your AICleaner configuration to get started</div>
                    </div>
                </div>
            `;
        }

        return `
            <div class="content">
                ${this.renderQuickActions()}
                <div class="zone-grid">
                    ${this.zones.map(zone => this.renderZoneCard(zone)).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Render quick actions panel
     */
    renderQuickActions() {
        const totalActiveTasks = this.systemStatus.totalActiveTasks || 0;
        const hasZones = this.zones && this.zones.length > 0;

        return `
            <div class="quick-actions-panel">
                <div class="quick-actions-title">
                    <span>⚡</span>
                    Quick Actions
                </div>
                <div class="quick-actions-grid">
                    <button class="quick-action-btn" data-action="analyze-all" ${!hasZones ? 'disabled' : ''}>
                        <div class="quick-action-icon">🔍</div>
                        <div class="quick-action-label">Analyze All Zones</div>
                        <div class="quick-action-desc">Run analysis on all configured zones</div>
                    </button>
                    <button class="quick-action-btn" data-action="refresh">
                        <div class="quick-action-icon">🔄</div>
                        <div class="quick-action-label">Refresh Data</div>
                        <div class="quick-action-desc">Update all sensor data from Home Assistant</div>
                    </button>
                    <button class="quick-action-btn" data-action="complete-all" ${totalActiveTasks === 0 ? 'disabled' : ''}>
                        <div class="quick-action-icon">✅</div>
                        <div class="quick-action-label">Mark All Complete</div>
                        <div class="quick-action-desc">Mark all active tasks as completed</div>
                    </button>
                    <button class="quick-action-btn" data-action="system-info">
                        <div class="quick-action-icon">ℹ️</div>
                        <div class="quick-action-label">System Info</div>
                        <div class="quick-action-desc">View system status and diagnostics</div>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render individual zone card
     */
    renderZoneCard(zone) {
        // Check if zone has configuration errors
        if (zone.configurationStatus === 'invalid') {
            return this.renderZoneCardWithErrors(zone);
        }

        const lastAnalysis = zone.lastAnalysis ?
            this.formatRelativeTime(new Date(zone.lastAnalysis)) : 'Never';

        // Get zone icon or use default
        const zoneIcon = this.getZoneIcon(zone.name);

        // Use completion rate from zone data or calculate if not available
        const completionRate = zone.completionRate !== undefined ?
            Math.round(zone.completionRate * 100) :
            (() => {
                const totalTasks = zone.activeTasks + zone.completedTasks;
                return totalTasks > 0 ? Math.round((zone.completedTasks / totalTasks) * 100) : 0;
            })();

        return `
            <div class="zone-card" data-zone="${zone.name}">
                <div class="zone-name">
                    <span class="zone-icon">${zoneIcon}</span>
                    ${zone.displayName}
                </div>
                <div class="zone-stats">
                    <div class="stat-item active">
                        <div class="stat-number">${zone.activeTasks}</div>
                        <div class="stat-label">Active</div>
                    </div>
                    <div class="stat-item completed">
                        <div class="stat-number">${zone.completedTasks}</div>
                        <div class="stat-label">Completed</div>
                    </div>
                </div>
                <div class="zone-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${completionRate}%"></div>
                    </div>
                    <div class="progress-text">${completionRate}% completion rate</div>
                    ${zone.efficiencyScore !== undefined ? `
                        <div class="efficiency-score">
                            <span class="efficiency-icon">⚡</span>
                            ${Math.round(zone.efficiencyScore * 100)}% efficiency
                        </div>
                    ` : ''}
                    ${this.renderCleanlinessScore(zone)}
                </div>
                <div class="last-analysis">
                    <span class="analysis-icon">🕒</span>
                    Last analysis: ${lastAnalysis}
                </div>
                <div class="quick-actions">
                    <button class="action-button" data-action="analyze" data-zone="${zone.name}">
                        <span class="button-icon">🔍</span>
                        Analyze Now
                    </button>
                    <button class="action-button secondary" data-action="view" data-zone="${zone.name}">
                        <span class="button-icon">👁️</span>
                        View Details
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render zone card with configuration errors
     */
    renderZoneCardWithErrors(zone) {
        const zoneIcon = this.getZoneIcon(zone.name);
        const errorCount = zone.configurationErrors ? zone.configurationErrors.length : 0;

        return `
            <div class="zone-card zone-card-error" data-zone="${zone.name}">
                <div class="zone-name">
                    <span class="zone-icon">${zoneIcon}</span>
                    ${zone.displayName}
                    <span class="error-badge">⚠️ ${errorCount} issue${errorCount !== 1 ? 's' : ''}</span>
                </div>
                <div class="zone-error-content">
                    <div class="error-message">
                        <strong>Configuration Issues:</strong>
                        <ul class="error-list">
                            ${zone.configurationErrors.map(error => `<li>${error}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="zone-error-actions">
                        <button class="action-button error" data-action="fix-config" data-zone="${zone.name}">
                            Fix Configuration
                        </button>
                        <button class="action-button secondary" data-action="hide-zone" data-zone="${zone.name}">
                            Hide Zone
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render cleanliness score section for zone card
     */
    renderCleanlinessScore(zone) {
        // Check if zone has live cleanliness analysis data
        const cleanlinessEntity = `sensor.aicleaner_${zone.name.toLowerCase().replace(' ', '_')}_cleanliness`;
        const cleanlinessData = this._hass.states && this._hass.states[cleanlinessEntity];

        if (!cleanlinessData || !cleanlinessData.attributes) {
            return '';
        }

        const overallScore = cleanlinessData.attributes.overall_score || 0;
        const state = cleanlinessData.state || 'Unknown';
        const confidence = cleanlinessData.attributes.confidence_level || 0;

        // Get color based on score
        const getScoreColor = (score) => {
            if (score >= 9) return '#4caf50'; // Green
            if (score >= 7) return '#8bc34a'; // Light green
            if (score >= 5) return '#ffc107'; // Yellow
            if (score >= 3) return '#ff9800'; // Orange
            return '#f44336'; // Red
        };

        const scoreColor = getScoreColor(overallScore);

        return `
            <div class="cleanliness-score">
                <div class="cleanliness-header">
                    <span class="cleanliness-icon">🏠</span>
                    <span class="cleanliness-label">Room Condition</span>
                </div>
                <div class="cleanliness-details">
                    <div class="score-display">
                        <div class="score-number" style="color: ${scoreColor}">
                            ${overallScore.toFixed(1)}
                        </div>
                        <div class="score-max">/10</div>
                    </div>
                    <div class="score-state">${state}</div>
                    <div class="confidence-level">
                        ${Math.round(confidence * 100)}% confidence
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render zone detail view
     */
    renderZoneDetail() {
        if (!this.selectedZone) {
            return this.renderDashboard();
        }

        const zone = this.zones.find(z => z.name === this.selectedZone);
        if (!zone) {
            return this.renderDashboard();
        }

        const zoneIcon = this.getZoneIcon(zone.name);
        const lastAnalysis = zone.lastAnalysis ?
            this.formatRelativeTime(new Date(zone.lastAnalysis)) : 'Never';

        return `
            <div class="content">
                <div class="zone-detail-header">
                    <button class="back-button" data-action="back">
                        <span>←</span> Back to Dashboard
                    </button>
                    <div class="zone-detail-title">
                        <span class="zone-detail-icon">${zoneIcon}</span>
                        <div>
                            <h2>${zone.displayName}</h2>
                            <p class="zone-purpose">${zone.purpose || 'Keep everything tidy and clean'}</p>
                        </div>
                    </div>
                </div>

                <div class="zone-detail-grid">
                    <div class="zone-stats-panel">
                        <h3>📊 Zone Statistics</h3>
                        <div class="stats-grid">
                            <div class="stat-card">
                                <div class="stat-value">${zone.activeTasks}</div>
                                <div class="stat-label">Active Tasks</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${zone.completedTasks}</div>
                                <div class="stat-label">Completed</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${Math.round((zone.completionRate || 0) * 100)}%</div>
                                <div class="stat-label">Completion Rate</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-value">${Math.round((zone.efficiencyScore || 0) * 100)}%</div>
                                <div class="stat-label">Efficiency</div>
                            </div>
                        </div>
                        <div class="last-analysis-info">
                            <span class="analysis-icon">🕒</span>
                            Last analysis: ${lastAnalysis}
                        </div>
                    </div>

                    <div class="zone-tasks-panel">
                        <h3>📋 Active Tasks</h3>
                        ${this.renderTaskList(zone)}
                    </div>

                    <div class="zone-controls-panel">
                        <h3>⚙️ Zone Controls</h3>
                        ${this.renderZoneControls(zone)}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render task list for zone detail view
     */
    renderTaskList(zone) {
        const tasks = zone.tasks || [];

        if (tasks.length === 0) {
            return `
                <div class="no-tasks">
                    <div class="no-tasks-icon">✨</div>
                    <div class="no-tasks-text">No active tasks</div>
                    <div class="no-tasks-desc">This zone is all clean!</div>
                </div>
            `;
        }

        return `
            <div class="task-list">
                ${tasks.map(task => this.renderTaskItem(task, zone.name)).join('')}
            </div>
        `;
    }

    /**
     * Render individual task item
     */
    renderTaskItem(task, zoneName) {
        const priority = task.priority || 'normal';
        const priorityIcon = {
            'high': '🔴',
            'normal': '🟡',
            'low': '🟢'
        }[priority] || '🟡';

        const createdAt = task.created_at ?
            this.formatRelativeTime(new Date(task.created_at)) : 'Unknown';

        return `
            <div class="task-item" data-task-id="${task.id}">
                <div class="task-content">
                    <div class="task-header">
                        <span class="task-priority">${priorityIcon}</span>
                        <span class="task-description">${task.description}</span>
                    </div>
                    <div class="task-meta">
                        <span class="task-created">Created ${createdAt}</span>
                    </div>
                </div>
                <div class="task-actions">
                    <button class="task-action-btn complete" data-action="complete-task" data-task-id="${task.id}" data-zone="${zoneName}">
                        ✅ Complete
                    </button>
                    <button class="task-action-btn dismiss" data-action="dismiss-task" data-task-id="${task.id}" data-zone="${zoneName}">
                        ❌ Dismiss
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render zone controls panel
     */
    renderZoneControls(zone) {
        return `
            <div class="zone-controls">
                <button class="control-btn primary" data-action="analyze" data-zone="${zone.name}">
                    <span class="control-icon">🔍</span>
                    <div class="control-content">
                        <div class="control-label">Analyze Zone</div>
                        <div class="control-desc">Run AI analysis now</div>
                    </div>
                </button>

                <button class="control-btn" data-action="view-camera" data-zone="${zone.name}">
                    <span class="control-icon">📷</span>
                    <div class="control-content">
                        <div class="control-label">View Camera</div>
                        <div class="control-desc">See current snapshot</div>
                    </div>
                </button>

                <button class="control-btn" data-action="zone-settings" data-zone="${zone.name}">
                    <span class="control-icon">⚙️</span>
                    <div class="control-content">
                        <div class="control-label">Zone Settings</div>
                        <div class="control-desc">Configure this zone</div>
                    </div>
                </button>
            </div>
        `;
    }

    /**
     * Render analytics view with real charts
     */
    renderAnalytics() {
        return `
            <div class="content">
                <div class="analytics-grid">
                    <div class="analytics-section">
                        <h3>📈 Task Completion Trends</h3>
                        <div class="chart-container">
                            <canvas id="completion-trend-chart"></canvas>
                        </div>
                    </div>

                    <div class="analytics-section">
                        <h3>🏆 Zone Performance</h3>
                        <div class="chart-container">
                            <canvas id="zone-performance-chart"></canvas>
                        </div>
                    </div>

                    <div class="analytics-section">
                        <h3>📊 System Insights</h3>
                        ${this.renderSystemInsights()}
                    </div>

                    <div class="analytics-section">
                        <h3>⏱️ Activity Timeline</h3>
                        <div class="chart-container">
                            <canvas id="activity-timeline-chart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render configuration view
     */
    renderConfig() {
        return `
            <div class="content">
                <div class="config-grid">
                    <div class="config-section">
                        <h3>🔔 Notification Settings</h3>
                        ${this.renderNotificationSettings()}
                    </div>

                    <div class="config-section">
                        <h3>🚫 Ignore Rules</h3>
                        ${this.renderIgnoreRules()}
                    </div>

                    <div class="config-section">
                        <h3>⏰ Analysis Schedule</h3>
                        ${this.renderScheduleSettings()}
                    </div>

                    <div class="config-section">
                        <h3>🔧 System Settings</h3>
                        ${this.renderSystemSettings()}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render notification personality selector
     */
    renderNotificationSettings() {
        const personalities = [
            { id: 'default', name: 'Default', icon: '🤖', desc: 'Standard notifications' },
            { id: 'snarky', name: 'Snarky', icon: '😏', desc: 'Witty and sarcastic' },
            { id: 'jarvis', name: 'Jarvis', icon: '🎩', desc: 'Professional assistant' },
            { id: 'roaster', name: 'Roaster', icon: '🔥', desc: 'Playfully critical' },
            { id: 'butler', name: 'Butler', icon: '🤵', desc: 'Formal and polite' },
            { id: 'coach', name: 'Coach', icon: '💪', desc: 'Motivational' },
            { id: 'zen', name: 'Zen', icon: '🧘', desc: 'Calm and mindful' }
        ];

        const currentPersonality = this.getCurrentPersonality();

        return `
            <div class="personality-grid">
                ${personalities.map(p => `
                    <div class="personality-card ${p.id === currentPersonality ? 'selected' : ''}"
                         data-personality="${p.id}">
                        <div class="personality-icon">${p.icon}</div>
                        <div class="personality-name">${p.name}</div>
                        <div class="personality-desc">${p.desc}</div>
                    </div>
                `).join('')}
            </div>
            <div class="config-checkbox">
                <input type="checkbox" id="notifications-enabled" checked>
                <label for="notifications-enabled">Enable notifications</label>
            </div>
        `;
    }

    /**
     * Render ignore rules management
     */
    renderIgnoreRules() {
        const ignoreRules = this.getIgnoreRules();

        return `
            <div class="ignore-rules-list">
                ${ignoreRules.map((rule, index) => `
                    <div class="ignore-rule-item">
                        <span class="ignore-rule-text">${rule}</span>
                        <button class="remove-rule-btn" data-rule-index="${index}">Remove</button>
                    </div>
                `).join('')}
                ${ignoreRules.length === 0 ? '<div style="color: var(--secondary-text-color); font-style: italic;">No ignore rules configured</div>' : ''}
            </div>
            <div class="add-rule-form">
                <input type="text" class="config-input add-rule-input" placeholder="Enter item to ignore (e.g., 'pet toys', 'decorative items')">
                <button class="add-rule-btn">Add Rule</button>
            </div>
        `;
    }

    /**
     * Render schedule settings
     */
    renderScheduleSettings() {
        return `
            <div class="config-input-group">
                <label class="config-label">Analysis Frequency</label>
                <select class="config-input" id="analysis-frequency">
                    <option value="15">Every 15 minutes</option>
                    <option value="30" selected>Every 30 minutes</option>
                    <option value="60">Every hour</option>
                    <option value="120">Every 2 hours</option>
                    <option value="240">Every 4 hours</option>
                </select>
            </div>
            <div class="config-checkbox">
                <input type="checkbox" id="auto-analysis" checked>
                <label for="auto-analysis">Enable automatic analysis</label>
            </div>
            <div class="config-checkbox">
                <input type="checkbox" id="quiet-hours">
                <label for="quiet-hours">Enable quiet hours (10 PM - 7 AM)</label>
            </div>
        `;
    }

    /**
     * Render system settings
     */
    renderSystemSettings() {
        return `
            <div class="config-input-group">
                <label class="config-label">AI Confidence Threshold</label>
                <input type="range" class="config-input" min="0.1" max="1.0" step="0.1" value="0.7" id="confidence-threshold">
                <div style="font-size: 0.8em; color: var(--secondary-text-color);">Current: 70%</div>
            </div>
            <div class="config-input-group">
                <label class="config-label">Max Tasks Per Zone</label>
                <input type="number" class="config-input" min="1" max="20" value="10" id="max-tasks">
            </div>
            <div class="config-checkbox">
                <input type="checkbox" id="debug-mode">
                <label for="debug-mode">Enable debug logging</label>
            </div>
            <div style="margin-top: 16px;">
                <button class="control-btn primary" data-action="save-settings">
                    <span class="control-icon">💾</span>
                    <div class="control-content">
                        <div class="control-label">Save Settings</div>
                        <div class="control-desc">Apply configuration changes</div>
                    </div>
                </button>
            </div>
        `;
    }

    /**
     * Get current notification personality
     */
    getCurrentPersonality() {
        // In a real implementation, this would read from the system state
        return 'default';
    }

    /**
     * Get current ignore rules
     */
    getIgnoreRules() {
        // In a real implementation, this would read from the system state
        return ['pet toys', 'decorative plants', 'artwork'];
    }

    /**
     * Render system insights panel
     */
    renderSystemInsights() {
        const totalTasks = this.systemStatus.totalActiveTasks + this.systemStatus.totalCompletedTasks;
        const completionRate = totalTasks > 0 ? Math.round((this.systemStatus.totalCompletedTasks / totalTasks) * 100) : 0;
        const avgEfficiency = Math.round((this.systemStatus.averageEfficiencyScore || 0) * 100);

        // Calculate uptime (mock data for now)
        const uptimeHours = 24 * 7; // Mock 7 days uptime
        const analysisCount = this.zones.length * 48; // Mock analysis count

        return `
            <div class="insights-grid">
                <div class="insight-card">
                    <div class="insight-value">${completionRate}%</div>
                    <div class="insight-label">Completion Rate</div>
                    <div class="insight-trend up">↗ +5% this week</div>
                </div>
                <div class="insight-card">
                    <div class="insight-value">${avgEfficiency}%</div>
                    <div class="insight-label">Avg Efficiency</div>
                    <div class="insight-trend neutral">→ Stable</div>
                </div>
                <div class="insight-card">
                    <div class="insight-value">${uptimeHours}h</div>
                    <div class="insight-label">System Uptime</div>
                    <div class="insight-trend up">↗ 99.9%</div>
                </div>
                <div class="insight-card">
                    <div class="insight-value">${analysisCount}</div>
                    <div class="insight-label">Analyses Run</div>
                    <div class="insight-trend up">↗ +12 today</div>
                </div>
            </div>
        `;
    }

    /**
     * Initialize charts after render
     */
    initializeCharts() {
        // Load Chart.js if not already loaded
        if (typeof Chart === 'undefined') {
            this.loadChartJS().then(() => {
                this.createCharts();
            });
        } else {
            this.createCharts();
        }
    }

    /**
     * Load Chart.js library
     */
    loadChartJS() {
        return new Promise((resolve, reject) => {
            if (typeof Chart !== 'undefined') {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * Create all charts
     */
    createCharts() {
        try {
            if (typeof Chart === 'undefined') {
                // Chart.js not loaded, skip chart creation
                return;
            }

            this.createCompletionTrendChart();
            this.createZonePerformanceChart();
            this.createActivityTimelineChart();
        } catch (error) {
            // Chart creation failed - continue without charts
            this.shadowRoot.querySelector('.charts-container').style.display = 'none';
        }
    }

    /**
     * Create task completion trend chart
     */
    createCompletionTrendChart() {
        try {
            const canvas = this.shadowRoot.getElementById('completion-trend-chart');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');

        // Generate mock data for the last 7 days
        const labels = [];
        const completedData = [];
        const activeData = [];

        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { weekday: 'short' }));

            // Mock data with some variation
            completedData.push(Math.floor(Math.random() * 10) + 5);
            activeData.push(Math.floor(Math.random() * 8) + 2);
        }

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Tasks Completed',
                    data: completedData,
                    borderColor: 'rgb(76, 175, 80)',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'New Tasks',
                    data: activeData,
                    borderColor: 'rgb(255, 152, 0)',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                }
            }
        });
        } catch (error) {
            // Completion trend chart creation failed - continue without chart
        }
    }

    /**
     * Create zone performance chart
     */
    createZonePerformanceChart() {
        const canvas = this.shadowRoot.getElementById('zone-performance-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Use real zone data
        const zoneNames = this.zones.map(zone => zone.displayName);
        const completionRates = this.zones.map(zone => Math.round((zone.completionRate || 0) * 100));
        const efficiencyScores = this.zones.map(zone => Math.round((zone.efficiencyScore || 0) * 100));

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: zoneNames,
                datasets: [{
                    label: 'Completion Rate (%)',
                    data: completionRates,
                    backgroundColor: 'rgba(76, 175, 80, 0.8)',
                    borderColor: 'rgb(76, 175, 80)',
                    borderWidth: 1
                }, {
                    label: 'Efficiency Score (%)',
                    data: efficiencyScores,
                    backgroundColor: 'rgba(33, 150, 243, 0.8)',
                    borderColor: 'rgb(33, 150, 243)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                }
            }
        });
    }

    /**
     * Create activity timeline chart
     */
    createActivityTimelineChart() {
        const canvas = this.shadowRoot.getElementById('activity-timeline-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Generate hourly activity data for today
        const hours = [];
        const activityData = [];

        for (let i = 0; i < 24; i++) {
            hours.push(`${i.toString().padStart(2, '0')}:00`);
            // Mock activity data with peaks during typical cleaning times
            let activity = Math.random() * 3;
            if (i >= 8 && i <= 10) activity += 5; // Morning cleaning
            if (i >= 14 && i <= 16) activity += 3; // Afternoon cleaning
            if (i >= 18 && i <= 20) activity += 4; // Evening cleaning
            activityData.push(Math.round(activity));
        }

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [{
                    label: 'Analysis Activity',
                    data: activityData,
                    borderColor: 'rgb(156, 39, 176)',
                    backgroundColor: 'rgba(156, 39, 176, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    }
                }
            }
        });
    }

    /**
     * Attach event listeners for user interactions with enhanced debugging
     */
    attachEventListeners() {
        // Use event delegation from shadow root for better reliability
        this.shadowRoot.addEventListener('click', (e) => {
            // Check if clicked element is an empty action button
            if (e.target.classList.contains('empty-action-button')) {
                e.preventDefault();
                e.stopPropagation();

                console.log('🔧 Empty action button clicked via event delegation');
                console.log('🔧 Button details:', {
                    id: e.target.id,
                    dataAction: e.target.dataset.action,
                    dataMethod: e.target.dataset.method,
                    textContent: e.target.textContent
                });

                const buttonId = e.target.id;
                const action = e.target.dataset.action;
                const method = e.target.dataset.method;

                // Multiple fallback mechanisms for method resolution
                let methodToCall = null;
                let callMethod = null;

                // Try pending callbacks first
                if (this._pendingButtonCallbacks && this._pendingButtonCallbacks[buttonId]) {
                    const callback = this._pendingButtonCallbacks[buttonId];
                    console.log('🔧 Found callback in pendingButtonCallbacks:', callback);

                    if (typeof callback === 'string' && this[callback]) {
                        methodToCall = callback;
                        callMethod = this[callback].bind(this);
                    } else if (typeof callback === 'function') {
                        callMethod = callback.bind(this);
                    }
                }

                // Fallback: try class-based lookup
                if (!callMethod && this._pendingButtonCallbacks && this._pendingButtonCallbacks['empty-action-button']) {
                    const callback = this._pendingButtonCallbacks['empty-action-button'];
                    console.log('🔧 Found callback via class lookup:', callback);

                    if (typeof callback === 'string' && this[callback]) {
                        methodToCall = callback;
                        callMethod = this[callback].bind(this);
                    }
                }

                // Fallback: try data attributes
                if (!callMethod && (action || method)) {
                    const methodName = method || action;
                    console.log('🔧 Trying method from data attribute:', methodName);

                    if (this[methodName] && typeof this[methodName] === 'function') {
                        methodToCall = methodName;
                        callMethod = this[methodName].bind(this);
                    }
                }

                // Execute the method
                if (callMethod) {
                    console.log(`✅ Executing method: ${methodToCall || 'anonymous'}`);
                    try {
                        callMethod();
                    } catch (error) {
                        console.error('❌ Method execution failed:', error);
                    }
                } else {
                    console.error('❌ No method found to execute for button click');
                    console.log('🔧 Available methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(this))
                        .filter(name => typeof this[name] === 'function'));
                }
            }
        });

        // Legacy support: also attach to individual buttons as backup
        this.shadowRoot.querySelectorAll('.empty-action-button').forEach(button => {
            button.addEventListener('click', (e) => {
                console.log('🔧 Button clicked via individual listener (backup)');
                // This will bubble up to the delegation handler above
            });
        });

        // Navigation buttons with enhanced accessibility
        this.shadowRoot.querySelectorAll('.nav-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.currentView = e.target.dataset.view;
                this.render();
            });

            // Keyboard navigation support
            button.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    this.currentView = e.currentTarget.dataset.view;
                    this.render();
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                    e.preventDefault();
                    this.handleNavigationKeyboard(e.key, e.currentTarget);
                }
            });
        });

        // Zone cards
        this.shadowRoot.querySelectorAll('.zone-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.closest('.action-button')) {
                    this.selectedZone = e.currentTarget.dataset.zone;
                    this.currentView = 'zone';
                    this.render();
                }
            });
        });

        // Action buttons
        this.shadowRoot.querySelectorAll('.action-button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.currentTarget.dataset.action;
                const zone = e.currentTarget.dataset.zone;
                this.handleAction(action, zone);
            });
        });

        // Quick action buttons
        this.shadowRoot.querySelectorAll('.quick-action-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.currentTarget.dataset.action;
                if (!e.currentTarget.disabled) {
                    this.handleQuickAction(action);
                }
            });
        });

        // Back button
        this.shadowRoot.querySelectorAll('.back-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.currentView = 'dashboard';
                this.selectedZone = null;
                this.render();
            });
        });

        // Task action buttons
        this.shadowRoot.querySelectorAll('.task-action-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.currentTarget.dataset.action;
                const taskId = e.currentTarget.dataset.taskId;
                const zone = e.currentTarget.dataset.zone;
                this.handleTaskAction(action, taskId, zone);
            });
        });

        // Control buttons
        this.shadowRoot.querySelectorAll('.control-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.currentTarget.dataset.action;
                const zone = e.currentTarget.dataset.zone;
                this.handleControlAction(action, zone);
            });
        });

        // Personality cards
        this.shadowRoot.querySelectorAll('.personality-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const personality = e.currentTarget.dataset.personality;
                this.selectPersonality(personality);
            });
        });

        // Add ignore rule button
        this.shadowRoot.querySelectorAll('.add-rule-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const input = this.shadowRoot.querySelector('.add-rule-input');
                if (input && input.value.trim()) {
                    this.addIgnoreRule(input.value.trim());
                    input.value = '';
                }
            });
        });

        // Remove ignore rule buttons
        this.shadowRoot.querySelectorAll('.remove-rule-btn').forEach(button => {
            button.addEventListener('click', (e) => {
                const ruleIndex = parseInt(e.target.dataset.ruleIndex);
                this.removeIgnoreRule(ruleIndex);
            });
        });

        // Enhanced mobile touch events
        if (this.isMobile) {
            const cardElement = this.shadowRoot.querySelector('.aicleaner-card');
            if (cardElement) {
                // Enhanced touch event handling
                cardElement.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: false });
                cardElement.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
                cardElement.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: false });

                // Add swipe indicators
                this.addSwipeIndicators(cardElement);

                // Add pull-to-refresh indicator
                this.addPullToRefreshIndicator(cardElement);
            }

            // Add mobile-specific classes
            this.shadowRoot.querySelector('.aicleaner-card')?.classList.add('mobile-optimized');

            // Enhanced button interactions for mobile
            this.shadowRoot.querySelectorAll('button, .nav-button, .zone-card, .action-button').forEach(element => {
                // Prevent default touch behavior that might interfere
                element.addEventListener('touchstart', (e) => {
                    if (element.disabled) {
                        e.preventDefault();
                        return;
                    }
                    this.addTouchFeedback(element);
                }, { passive: false });

                element.addEventListener('touchend', (e) => {
                    if (element.disabled) {
                        e.preventDefault();
                        return;
                    }

                    this.removeTouchFeedback();

                    // Prevent zoom on double-tap
                    e.preventDefault();

                    // Add haptic feedback for button presses
                    this.triggerHapticFeedback('light');

                    // Trigger click with slight delay for visual feedback
                    setTimeout(() => {
                        if (!this.touchMoved) {
                            element.click();
                        }
                    }, 50);
                }, { passive: false });

                element.addEventListener('touchcancel', () => {
                    this.removeTouchFeedback();
                });
            });

            // Optimize scrolling for mobile
            this.optimizeMobileScrolling();
        }

        // Window resize handler for responsive updates
        window.addEventListener('resize', () => {
            this.isMobile = this.detectMobile();
            // Re-render if mobile state changed
            setTimeout(() => this.render(), 100);
        });

        // Orientation change handler for mobile devices
        window.addEventListener('orientationchange', () => {
            if (this.isMobile) {
                setTimeout(() => this.handleOrientationChange(), 100);
            }
        });

        // Optimize images for mobile after render
        if (this.isMobile) {
            setTimeout(() => this.optimizeImagesForMobile(), 500);
        }

        // Setup wizard event handlers
        this.attachSetupWizardEventListeners();
    }

    /**
     * Attach setup wizard specific event listeners
     */
    attachSetupWizardEventListeners() {
        // Setup wizard navigation buttons
        this.shadowRoot.querySelectorAll('.setup-button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.currentTarget.dataset.action;
                this.handleSetupAction(action);
            });
        });

        // Entity selection in setup wizard
        this.shadowRoot.querySelectorAll('.entity-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = e.currentTarget.dataset.action;
                const entity = e.currentTarget.dataset.entity;
                this.handleEntitySelection(action, entity);
            });
        });

        // Form input changes in setup wizard
        this.shadowRoot.querySelectorAll('.setup-form input, .setup-form textarea').forEach(input => {
            input.addEventListener('input', (e) => {
                const field = e.target.dataset.field;
                if (field) {
                    this.updateSetupField(field, e.target.value);
                }
            });
        });

        // Empty state action buttons
        this.shadowRoot.querySelectorAll('.empty-action-button').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const onclick = button.getAttribute('onclick');
                if (onclick) {
                    // Execute the onclick function
                    eval(onclick);
                }
            });
        });
    }

    /**
     * Add swipe indicators for mobile navigation
     */
    addSwipeIndicators(container) {
        if (!this.isMobile) return;

        // Remove existing indicators
        container.querySelectorAll('.swipe-indicator').forEach(indicator => indicator.remove());

        // Add left swipe indicator
        const leftIndicator = document.createElement('div');
        leftIndicator.className = 'swipe-indicator left';
        leftIndicator.innerHTML = '‹';
        leftIndicator.title = 'Swipe right for previous view';
        container.appendChild(leftIndicator);

        // Add right swipe indicator
        const rightIndicator = document.createElement('div');
        rightIndicator.className = 'swipe-indicator right';
        rightIndicator.innerHTML = '›';
        rightIndicator.title = 'Swipe left for next view';
        container.appendChild(rightIndicator);
    }

    /**
     * Add pull-to-refresh indicator
     */
    addPullToRefreshIndicator(container) {
        const indicator = document.createElement('div');
        indicator.className = 'pull-to-refresh';
        indicator.innerHTML = '↓ Pull to refresh';
        container.appendChild(indicator);
    }

    /**
     * Optimize mobile scrolling performance
     */
    optimizeMobileScrolling() {
        // Add momentum scrolling to scrollable elements
        const scrollableElements = this.shadowRoot.querySelectorAll('.navigation, .zone-grid, .analytics-grid');
        scrollableElements.forEach(element => {
            element.style.webkitOverflowScrolling = 'touch';
            element.style.scrollBehavior = 'smooth';
        });

        // Optimize scroll performance
        let scrollTimeout;
        const optimizeScroll = () => {
            document.body.style.pointerEvents = 'none';
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                document.body.style.pointerEvents = '';
            }, 150);
        };

        this.shadowRoot.addEventListener('scroll', optimizeScroll, { passive: true });
    }

    /**
     * Handle orientation change for mobile devices
     */
    handleOrientationChange() {
        // Update device detection
        this.detectMobile();

        // Re-render with new orientation
        setTimeout(() => {
            this.render();
            this.showToast(`Orientation changed to ${this.isPortrait ? 'portrait' : 'landscape'}`, 'info', 1500);
        }, 100);
    }

    /**
     * Add responsive image loading for mobile
     */
    optimizeImagesForMobile() {
        const images = this.shadowRoot.querySelectorAll('img');
        images.forEach(img => {
            // Add loading="lazy" for better performance
            img.loading = 'lazy';

            // Add error handling
            img.onerror = () => {
                img.style.display = 'none';
                const placeholder = document.createElement('div');
                placeholder.className = 'image-placeholder';
                placeholder.innerHTML = '📷 Image unavailable';
                img.parentNode.insertBefore(placeholder, img.nextSibling);
            };
        });
    }

    /**
     * Handle keyboard navigation for nav buttons
     */
    handleNavigationKeyboard(key, currentButton) {
        const navButtons = Array.from(this.shadowRoot.querySelectorAll('.nav-button'));
        const currentIndex = navButtons.indexOf(currentButton);
        let nextIndex;

        if (key === 'ArrowLeft') {
            nextIndex = currentIndex > 0 ? currentIndex - 1 : navButtons.length - 1;
        } else if (key === 'ArrowRight') {
            nextIndex = currentIndex < navButtons.length - 1 ? currentIndex + 1 : 0;
        }

        if (nextIndex !== undefined) {
            // Update tabindex for proper tab order
            navButtons.forEach((btn, index) => {
                btn.setAttribute('tabindex', index === nextIndex ? '0' : '-1');
                btn.setAttribute('aria-selected', index === nextIndex ? 'true' : 'false');
            });

            // Focus the next button
            navButtons[nextIndex].focus();
        }
    }

    /**
     * Handle user actions
     */
    handleAction(action, zone) {
        switch (action) {
            case 'analyze':
                this.triggerAnalysis(zone);
                break;
            case 'view':
                this.selectedZone = zone;
                this.currentView = 'zone';
                this.render();
                break;
            case 'fix-config':
                this.showConfigurationHelp(zone);
                break;
            case 'hide-zone':
                this.hideZone(zone);
                break;
        }
    }

    /**
     * Handle setup wizard actions
     */
    handleSetupAction(action) {
        switch (action) {
            case 'setup-next':
                this.nextSetupStep();
                break;
            case 'setup-back':
                this.previousSetupStep();
                break;
            case 'setup-skip':
                this.skipSetupWizard();
                break;
            case 'setup-complete':
                this.completeSetupWizard();
                break;
            case 'refresh-entities':
                this.refreshEntities();
                break;
            case 'create-todo-guide':
                this.showTodoGuide();
                break;
        }
    }

    /**
     * Handle entity selection in setup wizard
     */
    handleEntitySelection(action, entityId) {
        switch (action) {
            case 'select-camera':
                this.setupWizardData.currentZone.camera_entity = entityId;
                this.render();
                this.showToast(`Camera selected: ${entityId}`, 'success');
                break;
            case 'select-todo':
                this.setupWizardData.currentZone.todo_list_entity = entityId;
                this.render();
                this.showToast(`Todo list selected: ${entityId}`, 'success');
                break;
        }
    }

    /**
     * Update setup wizard form field
     */
    updateSetupField(field, value) {
        this.setupWizardData.currentZone[field] = value;

        // Auto-generate display name from name if not manually set
        if (field === 'name' && !this.setupWizardData.currentZone.displayName) {
            this.setupWizardData.currentZone.displayName = value
                .split(/[-_]/)
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');

            // Update the display name input
            const displayNameInput = this.shadowRoot.querySelector('#zone-display-name');
            if (displayNameInput) {
                displayNameInput.value = this.setupWizardData.currentZone.displayName;
            }
        }

        // Re-render validation messages
        setTimeout(() => {
            const validationContainer = this.shadowRoot.querySelector('.validation-messages');
            if (validationContainer) {
                const newValidation = this.renderValidationMessages();
                validationContainer.outerHTML = newValidation;
            }
        }, 100);
    }

    /**
     * Move to next setup step
     */
    nextSetupStep() {
        const validation = this.validateCurrentStep();
        if (!validation.isValid) {
            this.showToast('Please fix the validation errors before continuing', 'warning');
            return;
        }

        if (this.setupWizardStep < 5) {
            this.setupWizardStep++;
            this.render();
            this.showToast(`Step ${this.setupWizardStep} of 5`, 'info');
        }
    }

    /**
     * Move to previous setup step
     */
    previousSetupStep() {
        if (this.setupWizardStep > 1) {
            this.setupWizardStep--;
            this.render();
            this.showToast(`Step ${this.setupWizardStep} of 5`, 'info');
        }
    }

    /**
     * Refresh available entities
     */
    refreshEntities() {
        this.showToast('Refreshing available entities...', 'loading', 2000);
        setTimeout(() => {
            this.render();
            this.showToast('Entities refreshed', 'success');
        }, 1000);
    }

    /**
     * Show todo list creation guide
     */
    showTodoGuide() {
        const guide = `
How to create Todo Lists in Home Assistant:

1. Go to Settings → Integrations
2. Click "Add Integration"
3. Search for "Local To-do"
4. Click "Local To-do" and configure
5. Create a new todo list for your zone
6. Come back to this setup wizard

Alternative methods:
- Use Google Tasks integration
- Use Todoist integration
- Use any other todo list integration

The todo list will help AICleaner manage cleaning tasks for your zone.
        `.trim();

        alert(guide);
    }

    /**
     * Show configuration help for a zone with errors
     */
    showConfigurationHelp(zoneName) {
        const zone = this.zones.find(z => z.name === zoneName);
        if (!zone || !zone.configurationErrors) {
            return;
        }

        let helpMessage = `Configuration help for zone "${zone.displayName}":\n\n`;

        zone.configurationErrors.forEach((error, index) => {
            helpMessage += `${index + 1}. ${error}\n`;

            // Provide specific help for common errors
            if (error.includes('Camera entity')) {
                helpMessage += `   → Check that the camera entity exists and is available in Home Assistant\n`;
                helpMessage += `   → Verify the camera is properly configured and accessible\n`;
            } else if (error.includes('Todo list entity')) {
                helpMessage += `   → Ensure the todo list integration is set up in Home Assistant\n`;
                helpMessage += `   → Create a todo list entity for this zone\n`;
            } else if (error.includes('Missing camera_entity')) {
                helpMessage += `   → Add a camera_entity to the zone configuration\n`;
                helpMessage += `   → Example: camera_entity: "camera.${zoneName}"\n`;
            }
            helpMessage += '\n';
        });

        helpMessage += 'To fix these issues:\n';
        helpMessage += '1. Go to AICleaner addon configuration\n';
        helpMessage += '2. Update the zone settings\n';
        helpMessage += '3. Restart the addon\n';
        helpMessage += '4. Refresh this dashboard\n';

        alert(helpMessage);
    }

    /**
     * Hide a zone with configuration errors
     */
    hideZone(zoneName) {
        if (confirm(`Hide zone "${zoneName}" from the dashboard?\n\nThis will not delete the zone configuration, just hide it from view until the configuration issues are resolved.`)) {
            // Store hidden zones in localStorage
            const hiddenZones = JSON.parse(localStorage.getItem('aicleaner_hidden_zones') || '[]');
            if (!hiddenZones.includes(zoneName)) {
                hiddenZones.push(zoneName);
                localStorage.setItem('aicleaner_hidden_zones', JSON.stringify(hiddenZones));
            }

            // Refresh the display
            this.updateData();
            this.render();
            this.showToast(`Zone "${zoneName}" hidden from dashboard`);
        }
    }

    /**
     * Check if a zone should be hidden
     */
    isZoneHidden(zoneName) {
        const hiddenZones = JSON.parse(localStorage.getItem('aicleaner_hidden_zones') || '[]');
        return hiddenZones.includes(zoneName);
    }

    /**
     * Handle quick action buttons
     */
    handleQuickAction(action) {
        switch (action) {
            case 'analyze-all':
                this.triggerAnalysisAll();
                break;
            case 'refresh':
                this.refreshData();
                break;
            case 'complete-all':
                this.completeAllTasks();
                break;
            case 'system-info':
                this.showSystemInfo();
                break;
        }
    }

    /**
     * Trigger zone analysis via Home Assistant service call (MQTT-based)
     */
    triggerAnalysis(zoneName) {
        console.log('Triggering analysis for zone:', zoneName);

        // Show loading state
        const loadingMessage = `Starting analysis for ${zoneName}...`;
        const loadingToast = this.showToast(loadingMessage, 'loading', 0);

        // Disable the analyze button
        const analyzeButtons = this.shadowRoot.querySelectorAll(`[data-action="analyze"][data-zone="${zoneName}"]`);
        analyzeButtons.forEach(btn => {
            btn.classList.add('button-loading');
            btn.disabled = true;
        });

        // Call Home Assistant service directly (MQTT handles the backend)
        this.hass.callService('aicleaner', 'run_analysis', {
            zone_name: zoneName
        })
        .then(() => {
            console.log('Analysis triggered successfully via HA service');

            // Dismiss loading toast and show success
            loadingToast.dismiss();
            this.showToast(`Analysis started for ${zoneName}`, 'success');

            // Update loading message for data refresh
            const refreshToast = this.showToast('Refreshing zone data...', 'loading', 0);

            // Refresh data after a short delay
            setTimeout(() => {
                this.refreshData();
                refreshToast.dismiss();
                this.showToast('Zone data updated', 'info', 2000);
            }, 2000);
        })
        .catch(error => {
            console.error('Failed to trigger analysis:', error);

            // Dismiss loading toast and show error
            loadingToast.dismiss();

            // Determine error message based on error type
            let errorMessage = 'Failed to start analysis';
            if (error.message) {
                if (error.message.includes('not found')) {
                    errorMessage = 'AICleaner service not available. Check addon status.';
                } else if (error.message.includes('timeout')) {
                    errorMessage = 'Analysis request timed out. Try again.';
                } else {
                    errorMessage = `Analysis failed: ${error.message}`;
                }
            }

            this.showToast(errorMessage, 'error', 5000);
        })
        .finally(() => {
            // Re-enable analyze buttons
            analyzeButtons.forEach(btn => {
                btn.classList.remove('button-loading');
                btn.disabled = false;
            });
        });
    }

    /**
     * Trigger analysis for all zones
     */
    triggerAnalysisAll() {
        console.log('Triggering analysis for all zones');

        // Call the webhook service handler
        fetch('http://192.168.88.125:8098/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'run_analysis',
                zone: ''  // Empty zone means all zones
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Analysis triggered successfully for all zones:', data);
                this.showToast(`Analysis started for all zones`);
                // Refresh data after a short delay
                setTimeout(() => this.refreshData(), 2000);
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Failed to trigger analysis for all zones:', error);
            this.showToast('Failed to start analysis', 'error');
        });
    }

    /**
     * Refresh data from Home Assistant with enhanced error handling
     */
    refreshData() {
        try {
            // Check if Home Assistant is available
            if (!this._hass || !this._hass.states) {
                throw new Error('Home Assistant connection not available');
            }

            // Store previous zone count for comparison
            const previousZoneCount = this.zones ? this.zones.length : 0;

            // Update data
            this.updateData();

            // Check if data was successfully updated
            const currentZoneCount = this.zones ? this.zones.length : 0;
            const hasSystemStatus = this.systemStatus && Object.keys(this.systemStatus).length > 0;

            // Update last refresh time
            this.lastUpdateTime = new Date();

            // Re-render the UI
            this.render();

            // Provide feedback based on what was updated
            if (currentZoneCount === 0 && !hasSystemStatus) {
                this.showToast('No AICleaner data found. Check addon status.', 'warning', 4000);
            } else if (currentZoneCount !== previousZoneCount) {
                this.showToast(`Data refreshed - ${currentZoneCount} zones loaded`, 'success', 2000);
            } else {
                this.showToast('Data refreshed', 'info', 2000);
            }

        } catch (error) {
            console.error('Error refreshing data:', error);

            // Show appropriate error message
            let errorMessage = 'Failed to refresh data';
            if (error.message.includes('connection')) {
                errorMessage = 'Home Assistant connection lost. Check network.';
            } else if (error.message.includes('timeout')) {
                errorMessage = 'Data refresh timed out. Try again.';
            }

            this.showToast(errorMessage, 'error', 5000);

            // Show error state if no data is available
            if (!this.zones || this.zones.length === 0) {
                this.showErrorState = true;
                this.render();
            }
        }
    }

    /**
     * Complete all active tasks via Home Assistant service call (MQTT-based)
     */
    completeAllTasks() {
        console.log('Completing all tasks');

        // Call Home Assistant service directly (MQTT handles the backend)
        this.hass.callService('aicleaner', 'complete_all_tasks', {})
        .then(() => {
            console.log('All tasks completed successfully via HA service');
            this.showToast('Marking all tasks as completed');
            // Refresh data after a short delay
            setTimeout(() => this.refreshData(), 2000);
        })
        .catch(error => {
            console.error('Failed to complete all tasks:', error);
            this.showToast('Failed to complete tasks', 'error');
        });
    }

    /**
     * Show system information dialog
     */
    showSystemInfo() {
        const info = `
AICleaner v${this.systemStatus.version || '2.0'}
Total Zones: ${this.systemStatus.totalZones || 0}
Active Tasks: ${this.systemStatus.totalActiveTasks || 0}
Completed Tasks: ${this.systemStatus.totalCompletedTasks || 0}
Completion Rate: ${Math.round((this.systemStatus.globalCompletionRate || 0) * 100)}%
Last Analysis: ${this.systemStatus.lastGlobalAnalysis ?
    new Date(this.systemStatus.lastGlobalAnalysis).toLocaleString() : 'Never'}
        `.trim();

        alert(info); // Simple implementation - could be enhanced with a modal
    }

    /**
     * Handle task actions (complete, dismiss)
     */
    handleTaskAction(action, taskId, zoneName) {
        console.log('Handling task action:', action, 'for task:', taskId, 'in zone:', zoneName);

        let actionType = '';
        let toastMessage = '';

        switch (action) {
            case 'complete-task':
                actionType = 'complete_task';
                toastMessage = 'Task marked as completed';
                break;
            case 'dismiss-task':
                actionType = 'dismiss_task';
                toastMessage = 'Task dismissed';
                break;
            default:
                console.error('Unknown task action:', action);
                return;
        }

        // Call the webhook service handler
        fetch('http://192.168.88.125:8098/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: actionType,
                zone: zoneName,
                task_id: taskId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Task action completed successfully:', data);
                this.showToast(toastMessage);
                // Refresh data after a short delay
                setTimeout(() => this.refreshData(), 2000);
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('Failed to handle task action:', error);
            this.showToast('Failed to update task', 'error');
        });
    }

    /**
     * Handle control actions (camera, settings, etc.)
     */
    handleControlAction(action, zoneName) {
        switch (action) {
            case 'analyze':
                this.triggerAnalysis(zoneName);
                break;
            case 'view-camera':
                this.showCameraSnapshot(zoneName);
                break;
            case 'zone-settings':
                this.showZoneSettings(zoneName);
                break;
        }
    }

    /**
     * Show camera snapshot
     */
    showCameraSnapshot(zoneName) {
        const zone = this.zones.find(z => z.name === zoneName);
        if (zone && zone.camera) {
            this.showCameraModal(zone);
        } else {
            this.showToast(`No camera configured for ${zoneName}`);
        }
    }

    /**
     * Show camera modal with live feed
     */
    showCameraModal(zone) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: var(--card-background-color, white);
            border-radius: 12px;
            padding: 20px;
            max-width: 90vw;
            max-height: 90vh;
            position: relative;
        `;

        const title = document.createElement('h3');
        title.textContent = `${zone.displayName || zone.name} Camera`;
        title.style.cssText = `
            margin: 0 0 16px 0;
            color: var(--primary-text-color);
        `;

        const img = document.createElement('img');
        img.style.cssText = `
            max-width: 100%;
            max-height: 70vh;
            border-radius: 8px;
        `;

        // Use Home Assistant camera proxy URL
        const cameraUrl = `/api/camera_proxy/${zone.camera}`;
        img.src = cameraUrl;
        img.alt = `${zone.name} camera view`;

        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--primary-text-color);
        `;

        closeBtn.onclick = () => document.body.removeChild(modal);
        modal.onclick = (e) => {
            if (e.target === modal) document.body.removeChild(modal);
        };

        content.appendChild(title);
        content.appendChild(img);
        content.appendChild(closeBtn);
        modal.appendChild(content);
        document.body.appendChild(modal);

        this.showToast(`Loading camera view for ${zone.displayName || zone.name}`);
    }

    /**
     * Show zone settings modal
     */
    showZoneSettings(zoneName) {
        const zone = this.zones.find(z => z.name === zoneName);
        if (!zone) {
            this.showToast(`Zone ${zoneName} not found`);
            return;
        }

        this.showZoneSettingsModal(zone);
    }

    /**
     * Show zone settings modal
     */
    showZoneSettingsModal(zone) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: var(--card-background-color, white);
            border-radius: 12px;
            padding: 20px;
            max-width: 500px;
            max-height: 90vh;
            overflow-y: auto;
            position: relative;
        `;

        content.innerHTML = `
            <h3 style="margin: 0 0 16px 0; color: var(--primary-text-color);">
                ${zone.displayName || zone.name} Settings
            </h3>

            <div style="margin-bottom: 16px;">
                <label style="display: block; margin-bottom: 8px; color: var(--primary-text-color);">
                    Zone Name:
                </label>
                <input type="text" value="${zone.displayName || zone.name}"
                       style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
            </div>

            <div style="margin-bottom: 16px;">
                <label style="display: block; margin-bottom: 8px; color: var(--primary-text-color);">
                    Camera Entity:
                </label>
                <input type="text" value="${zone.camera || ''}"
                       style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
            </div>

            <div style="margin-bottom: 16px;">
                <label style="display: block; margin-bottom: 8px; color: var(--primary-text-color);">
                    Update Frequency (hours):
                </label>
                <input type="number" value="${zone.updateFrequency || 24}" min="1" max="168"
                       style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
            </div>

            <div style="margin-bottom: 16px;">
                <label style="display: flex; align-items: center; color: var(--primary-text-color);">
                    <input type="checkbox" ${zone.notificationsEnabled ? 'checked' : ''}
                           style="margin-right: 8px;">
                    Enable Notifications
                </label>
            </div>

            <div style="display: flex; gap: 12px; margin-top: 20px;">
                <button class="save-settings-btn" style="
                    flex: 1;
                    padding: 12px;
                    background: var(--primary-color);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                ">Save Changes</button>
                <button class="cancel-settings-btn" style="
                    flex: 1;
                    padding: 12px;
                    background: #ccc;
                    color: #333;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                ">Cancel</button>
            </div>

            <button style="
                position: absolute;
                top: 10px;
                right: 10px;
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: var(--primary-text-color);
            " class="close-modal-btn">✕</button>
        `;

        const closeModal = () => document.body.removeChild(modal);

        content.querySelector('.close-modal-btn').onclick = closeModal;
        content.querySelector('.cancel-settings-btn').onclick = closeModal;
        content.querySelector('.save-settings-btn').onclick = () => {
            this.showToast('Zone settings saved (feature in development)');
            closeModal();
        };

        modal.onclick = (e) => {
            if (e.target === modal) closeModal();
        };

        modal.appendChild(content);
        document.body.appendChild(modal);
    }

    /**
     * Select notification personality
     */
    selectPersonality(personality) {
        if (this._hass && this._hass.callService) {
            this._hass.callService('aicleaner', 'set_notification_personality', {
                personality: personality
            });
            this.showToast(`Notification personality changed to ${personality}`);

            // Update UI
            this.shadowRoot.querySelectorAll('.personality-card').forEach(card => {
                card.classList.remove('selected');
            });
            this.shadowRoot.querySelector(`[data-personality="${personality}"]`)?.classList.add('selected');
        }
    }

    /**
     * Add ignore rule
     */
    addIgnoreRule(rule) {
        if (this._hass && this._hass.callService) {
            this._hass.callService('aicleaner', 'add_ignore_rule', {
                rule: rule
            });
            this.showToast(`Added ignore rule: ${rule}`);

            // Re-render the config section
            setTimeout(() => this.render(), 500);
        }
    }

    /**
     * Remove ignore rule
     */
    removeIgnoreRule(ruleIndex) {
        const rules = this.getIgnoreRules();
        const rule = rules[ruleIndex];

        if (this._hass && this._hass.callService && rule) {
            this._hass.callService('aicleaner', 'remove_ignore_rule', {
                rule: rule
            });
            this.showToast(`Removed ignore rule: ${rule}`);

            // Re-render the config section
            setTimeout(() => this.render(), 500);
        }
    }

    /**
     * Get appropriate icon for zone
     */
    getZoneIcon(zoneName) {
        const zoneIcons = {
            'kitchen': '🍳',
            'living_room': '🛋️',
            'bedroom': '🛏️',
            'bathroom': '🚿',
            'office': '💼',
            'garage': '🚗',
            'laundry': '🧺',
            'dining_room': '🍽️',
            'basement': '🏠',
            'attic': '📦'
        };

        const normalizedName = zoneName.toLowerCase().replace(/\s+/g, '_');
        return zoneIcons[normalizedName] || '🏠';
    }

    /**
     * Format time relative to now
     */
    formatRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    /**
     * Show enhanced toast notification with different types and icons
     * @param {string} message - The message to display
     * @param {string} type - Type of toast: 'success', 'error', 'warning', 'info', 'loading'
     * @param {number} duration - Duration in milliseconds (default: 3000)
     * @returns {Object} Toast object with dismiss method
     */
    showToast(message, type = 'info', duration = 3000) {
        // Remove any existing toasts of the same type
        const existingToasts = document.querySelectorAll(`.aicleaner-toast[data-type="${type}"]`);
        existingToasts.forEach(toast => toast.remove());

        const toast = document.createElement('div');
        toast.className = 'aicleaner-toast';
        toast.setAttribute('data-type', type);

        // Get icon and colors based on type
        const toastConfig = this.getToastConfig(type);

        toast.innerHTML = `
            <div class="toast-content">
                <span class="toast-icon">${toastConfig.icon}</span>
                <span class="toast-message">${message}</span>
                ${type !== 'loading' ? '<button class="toast-close">×</button>' : ''}
            </div>
        `;

        // Apply styles
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${toastConfig.background};
            color: ${toastConfig.color};
            padding: 12px 16px;
            border-radius: 8px;
            z-index: 1000;
            font-size: 0.9em;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border: 1px solid ${toastConfig.border};
            min-width: 300px;
            max-width: 500px;
            animation: slideUp 0.3s ease-out;
        `;

        // Add animation styles
        if (!document.querySelector('#aicleaner-toast-styles')) {
            const styles = document.createElement('style');
            styles.id = 'aicleaner-toast-styles';
            styles.textContent = `
                @keyframes slideUp {
                    from { transform: translate(-50%, 100%); opacity: 0; }
                    to { transform: translate(-50%, 0); opacity: 1; }
                }
                @keyframes slideDown {
                    from { transform: translate(-50%, 0); opacity: 1; }
                    to { transform: translate(-50%, 100%); opacity: 0; }
                }
                .aicleaner-toast .toast-content {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .aicleaner-toast .toast-icon {
                    font-size: 1.1em;
                    flex-shrink: 0;
                }
                .aicleaner-toast .toast-message {
                    flex: 1;
                    line-height: 1.4;
                }
                .aicleaner-toast .toast-close {
                    background: none;
                    border: none;
                    color: inherit;
                    font-size: 1.2em;
                    cursor: pointer;
                    padding: 0;
                    margin-left: 8px;
                    opacity: 0.7;
                    flex-shrink: 0;
                }
                .aicleaner-toast .toast-close:hover {
                    opacity: 1;
                }
                .aicleaner-toast[data-type="loading"] .toast-icon {
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(styles);
        }

        document.body.appendChild(toast);

        // Add close button functionality
        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.onclick = () => this.dismissToast(toast);
        }

        // Auto-dismiss for non-loading toasts
        let timeoutId;
        if (type !== 'loading' && duration > 0) {
            timeoutId = setTimeout(() => {
                this.dismissToast(toast);
            }, duration);
        }

        // Return toast object with dismiss method
        return {
            element: toast,
            dismiss: () => {
                if (timeoutId) clearTimeout(timeoutId);
                this.dismissToast(toast);
            },
            updateMessage: (newMessage) => {
                const messageEl = toast.querySelector('.toast-message');
                if (messageEl) messageEl.textContent = newMessage;
            }
        };
    }

    /**
     * Get toast configuration based on type
     */
    getToastConfig(type) {
        const configs = {
            success: {
                icon: '✅',
                background: 'var(--success-color, #4caf50)',
                color: 'white',
                border: 'var(--success-color, #4caf50)'
            },
            error: {
                icon: '❌',
                background: 'var(--error-color, #f44336)',
                color: 'white',
                border: 'var(--error-color, #f44336)'
            },
            warning: {
                icon: '⚠️',
                background: 'var(--warning-color, #ff9800)',
                color: 'white',
                border: 'var(--warning-color, #ff9800)'
            },
            info: {
                icon: 'ℹ️',
                background: 'var(--info-color, #2196f3)',
                color: 'white',
                border: 'var(--info-color, #2196f3)'
            },
            loading: {
                icon: '⏳',
                background: 'var(--primary-color, #1976d2)',
                color: 'white',
                border: 'var(--primary-color, #1976d2)'
            }
        };

        return configs[type] || configs.info;
    }

    /**
     * Dismiss a toast with animation
     */
    dismissToast(toast) {
        if (!toast || !document.body.contains(toast)) return;

        toast.style.animation = 'slideDown 0.3s ease-out';
        setTimeout(() => {
            if (document.body.contains(toast)) {
                document.body.removeChild(toast);
            }
        }, 300);
    }

    /**
     * Show loading state
     */
    showLoading(message = 'Loading...') {
        this.isLoading = true;
        this.loadingMessage = message;
        this.loadingToast = this.showToast(message, 'loading', 0);
        this.render();
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        this.isLoading = false;
        this.loadingMessage = null;
        if (this.loadingToast) {
            this.loadingToast.dismiss();
            this.loadingToast = null;
        }
        this.render();
    }

    /**
     * Update loading message
     */
    updateLoadingMessage(message) {
        this.loadingMessage = message;
        if (this.loadingToast) {
            this.loadingToast.updateMessage(message);
        }
    }

    /**
     * Show error state with retry option
     */
    showError(message, retryCallback = null) {
        const errorContent = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <div class="error-title">Something went wrong</div>
                <div class="error-message">${message}</div>
                ${retryCallback ? `
                    <button class="retry-button" onclick="${retryCallback}">
                        <span class="retry-icon">🔄</span>
                        Try Again
                    </button>
                ` : ''}
            </div>
        `;

        return errorContent;
    }

    /**
     * Show empty state with guidance
     */
    showEmptyState(title, message, actionText = null, actionCallback = null) {
        const buttonId = actionCallback ? `empty-action-button-${Date.now()}` : null;

        const html = `
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <div class="empty-title">${title}</div>
                <div class="empty-message">${message}</div>
                ${actionText && actionCallback ? `
                    <button id="${buttonId}" class="empty-action-button" data-action="${actionCallback}" data-method="${actionCallback}">
                        ${actionText}
                    </button>
                ` : ''}
            </div>
        `;

        // Store the callback for later use with multiple fallback mechanisms
        if (buttonId && actionCallback) {
            this._pendingButtonCallbacks = this._pendingButtonCallbacks || {};
            this._pendingButtonCallbacks[buttonId] = actionCallback;

            // Also store by class for easier lookup
            this._pendingButtonCallbacks['empty-action-button'] = actionCallback;
        }

        return html;
    }

    /**
     * Fix setup wizard button event handling with comprehensive debugging and fallbacks
     */
    fixSetupWizardButton() {
        // Use setTimeout to ensure DOM is fully rendered
        setTimeout(() => {
            const button = this.shadowRoot.querySelector('.empty-action-button');
            console.log('🔧 fixSetupWizardButton: Looking for button...', button);

            if (button) {
                console.log('🔧 Found button:', {
                    id: button.id,
                    dataAction: button.dataset.action,
                    dataMethod: button.dataset.method,
                    textContent: button.textContent,
                    onclick: button.onclick
                });

                // Remove any existing onclick attribute
                button.removeAttribute('onclick');

                // Add comprehensive event listener with multiple fallback mechanisms
                const clickHandler = (e) => {
                    e.preventDefault();
                    e.stopPropagation();

                    console.log('🔧 Setup wizard button clicked via fixSetupWizardButton');
                    console.log('🔧 Card instance:', this);
                    console.log('🔧 startSetupWizard method type:', typeof this.startSetupWizard);
                    console.log('🔧 Available methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(this))
                        .filter(name => typeof this[name] === 'function' && name.includes('setup')));

                    // Multiple fallback attempts
                    try {
                        if (typeof this.startSetupWizard === 'function') {
                            console.log('✅ Calling startSetupWizard method directly');
                            this.startSetupWizard();
                            return;
                        }
                    } catch (error) {
                        console.error('❌ Direct method call failed:', error);
                    }

                    // Fallback: try to find method on prototype
                    try {
                        const proto = Object.getPrototypeOf(this);
                        if (proto.startSetupWizard && typeof proto.startSetupWizard === 'function') {
                            console.log('✅ Calling startSetupWizard via prototype');
                            proto.startSetupWizard.call(this);
                            return;
                        }
                    } catch (error) {
                        console.error('❌ Prototype method call failed:', error);
                    }

                    // Fallback: try to find method by name
                    try {
                        const methodName = button.dataset.method || button.dataset.action;
                        if (methodName && this[methodName] && typeof this[methodName] === 'function') {
                            console.log(`✅ Calling ${methodName} via dataset`);
                            this[methodName]();
                            return;
                        }
                    } catch (error) {
                        console.error('❌ Dataset method call failed:', error);
                    }

                    console.error('❌ All fallback methods failed - startSetupWizard not accessible');
                };

                // Remove existing listeners and add new one
                button.removeEventListener('click', clickHandler);
                button.addEventListener('click', clickHandler);

                console.log('🔧 Setup wizard button event listener attached');
            } else {
                console.warn('🔧 No .empty-action-button found in shadow DOM');
                console.log('🔧 Available buttons:', this.shadowRoot.querySelectorAll('button'));
            }
        }, 50); // Small delay to ensure DOM is ready
    }

    /**
     * Return card size for Lovelace layout
     */
    getCardSize() {
        return 3;
    }

    /**
     * Return configuration schema for card editor
     */
    static getConfigElement() {
        return document.createElement('aicleaner-card-editor');
    }

    /**
     * Return stub configuration for card picker
     */
    static getStubConfig() {
        return {
            type: 'custom:aicleaner-card',
            title: 'AICleaner'
        };
    }
}

// Register the custom card
console.log('AICleaner Card: Registering custom element...');
customElements.define('aicleaner-card', AICleanerCard);

// Register with card picker
console.log('AICleaner Card: Registering with card picker...');
window.customCards = window.customCards || [];
window.customCards.push({
    type: 'aicleaner-card',
    name: 'AICleaner Card',
    description: 'A comprehensive card for managing AICleaner zones and tasks',
    preview: true
});

// Add global debug helper
window.debugAICleanerCard = function() {
    const cards = document.querySelectorAll('aicleaner-card');
    if (cards.length === 0) {
        console.log('❌ No AICleaner cards found');
        return null;
    }

    const card = cards[0]; // Use first card found
    if (card.debugSetupWizardButton) {
        return card.debugSetupWizardButton();
    } else {
        console.log('❌ Debug method not available on card');
        return card;
    }
};

console.log('AICleaner Card v2.0 loaded successfully!');
console.log('🔧 Debug helper available: window.debugAICleanerCard()');
// AICleaner Card v2.0 loaded
