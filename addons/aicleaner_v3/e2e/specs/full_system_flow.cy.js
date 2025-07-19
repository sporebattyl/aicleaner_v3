/**
 * AICleaner v3 Full System Flow E2E Tests
 * 
 * These tests cover the critical user journeys and cross-phase integration
 * scenarios identified in the integration testing strategy.
 */

describe('AICleaner v3 Full System Flow', () => {
  beforeEach(() => {
    // Mock API responses
    cy.mockApiResponses()
    
    // Visit the application
    cy.visit('/')
    
    // Login with test credentials
    cy.login()
    
    // Wait for initial load
    cy.waitForLoad()
  })

  describe('Scenario 1: Full Device Onboarding and Operation', () => {
    it('should complete full device discovery and zone assignment flow', () => {
      // Step 1: Navigate to device management
      cy.navigateToTab('devices')
      
      // Step 2: Verify device discovery interface is available
      cy.get('[data-cy="device-list"]').should('be.visible')
      cy.get('[data-cy="mqtt-discovery-status"]').should('contain', 'Connected')
      
      // Step 3: Simulate new device discovery
      cy.intercept('POST', '/api/mqtt/discover', {
        body: {
          device_id: 'test_vacuum_001',
          name: 'Test Vacuum',
          type: 'vacuum',
          status: 'discovered'
        }
      }).as('deviceDiscovery')
      
      // Step 4: Check that device appears in unassigned list
      cy.get('[data-cy="unassigned-devices"]').should('contain', 'Test Vacuum')
      
      // Step 5: Navigate to zone configuration
      cy.navigateToTab('unified-config')
      cy.get('[data-cy="zones-tab"]').click()
      
      // Step 6: Assign device to a zone
      cy.createZone('Living Room', 'Main living area for automated cleaning')
      
      // Step 7: Verify zone was created and device can be assigned
      cy.get('[data-cy="zone-list"]').should('contain', 'Living Room')
      cy.get('[data-cy="assign-device-btn"]').click()
      cy.get('[data-cy="device-select"]').select('Test Vacuum')
      cy.get('[data-cy="zone-select"]').select('Living Room')
      cy.get('[data-cy="assign-device-submit"]').click()
      
      // Step 8: Verify assignment was successful
      cy.get('[data-cy="assignment-success-toast"]').should('be.visible')
      
      // Step 9: Check security dashboard for any alerts
      cy.navigateToTab('security')
      cy.checkSecurityStatus('high')
      cy.get('[data-cy="security-events"]').should('not.contain', 'Critical')
    })
  })

  describe('Scenario 2: Configuration Change and System-Wide Propagation', () => {
    it('should propagate configuration changes across all system components', () => {
      // Step 1: Navigate to unified configuration
      cy.navigateToTab('unified-config')
      
      // Step 2: Modify AI provider settings
      cy.get('[data-cy="ai-providers-section"]').should('be.visible')
      cy.get('[data-cy="primary-provider-select"]').select('anthropic')
      cy.get('[data-cy="secondary-provider-select"]').select('openai')
      
      // Step 3: Update security settings
      cy.get('[data-cy="security-tab"]').click()
      cy.get('[data-cy="threat-detection-toggle"]').click()
      cy.get('[data-cy="alert-threshold-select"]').select('high')
      
      // Step 4: Save configuration
      cy.saveConfiguration()
      
      // Step 5: Verify changes are reflected immediately
      cy.get('[data-cy="config-status"]').should('contain', 'Saved successfully')
      
      // Step 6: Check that AI provider change is active
      cy.intercept('GET', '/api/ai/active-provider', { 
        body: { name: 'anthropic', status: 'active' } 
      }).as('activeProvider')
      
      cy.get('[data-cy="active-provider-indicator"]').should('contain', 'anthropic')
      
      // Step 7: Verify security settings are active
      cy.navigateToTab('security')
      cy.get('[data-cy="threat-detection-status"]').should('contain', 'Enabled')
      cy.get('[data-cy="alert-threshold-display"]').should('contain', 'High')
      
      // Step 8: Test that new settings work
      cy.get('[data-cy="run-security-check"]').click()
      cy.get('[data-cy="security-check-result"]').should('contain', 'Check completed')
    })
  })

  describe('Scenario 3: AI Provider Failover and Recovery', () => {
    it('should handle AI provider failover gracefully', () => {
      // Step 1: Navigate to AI provider management
      cy.navigateToTab('unified-config')
      cy.get('[data-cy="ai-providers-section"]').should('be.visible')
      
      // Step 2: Configure failover settings
      cy.get('[data-cy="failover-enabled-toggle"]').should('be.checked')
      cy.get('[data-cy="primary-provider"]').should('contain', 'openai')
      cy.get('[data-cy="secondary-provider"]').should('contain', 'anthropic')
      
      // Step 3: Simulate primary provider failure
      cy.intercept('POST', '/api/ai/test-connection', {
        statusCode: 500,
        body: { error: 'Primary provider unavailable' }
      }).as('providerFailure')
      
      // Step 4: Trigger AI operation that should cause failover
      cy.navigateToTab('zones')
      cy.get('[data-cy="optimize-zone-btn"]').first().click()
      
      // Step 5: Verify failover occurred
      cy.intercept('GET', '/api/ai/status', {
        body: {
          active_provider: 'anthropic',
          failover_occurred: true,
          last_failover: new Date().toISOString()
        }
      }).as('failoverStatus')
      
      cy.get('[data-cy="optimization-result"]').should('contain', 'Optimization completed')
      cy.get('[data-cy="provider-status"]').should('contain', 'Failed over to anthropic')
      
      // Step 6: Check system logs for failover event
      cy.navigateToTab('security')
      cy.get('[data-cy="security-events"]').should('contain', 'Provider failover')
      
      // Step 7: Verify alert was generated
      cy.get('[data-cy="failover-alert"]').should('be.visible')
    })
  })

  describe('Critical UI Components Integration', () => {
    it('should load and interact with SecurityDashboard correctly', () => {
      cy.navigateToTab('security')
      
      // Verify main dashboard elements
      cy.get('[data-cy="security-overview"]').should('be.visible')
      cy.get('[data-cy="security-level-badge"]').should('exist')
      cy.get('[data-cy="supervisor-token-status"]').should('exist')
      cy.get('[data-cy="mqtt-encryption-status"]').should('exist')
      
      // Test token validation modal
      cy.validateToken('test-supervisor-token')
      cy.get('[data-cy="token-validation-result"]').should('contain', 'Valid')
      
      // Check security events display
      cy.get('[data-cy="security-events-list"]').should('be.visible')
      cy.get('[data-cy="refresh-security-btn"]').click()
      cy.get('[data-cy="security-last-updated"]').should('contain', 'seconds ago')
    })

    it('should handle UnifiedConfigurationPanel interactions', () => {
      cy.navigateToTab('unified-config')
      
      // Test MQTT configuration
      cy.get('[data-cy="mqtt-tab"]').click()
      cy.get('[data-cy="mqtt-broker-input"]').clear().type('mqtt.example.com')
      cy.get('[data-cy="mqtt-port-input"]').clear().type('8883')
      cy.get('[data-cy="mqtt-tls-toggle"]').click()
      
      // Test configuration validation
      cy.get('[data-cy="validation-status"]').should('contain', 'Validating')
      cy.wait(1000) // Wait for debounced validation
      cy.get('[data-cy="validation-status"]').should('contain', 'Valid')
      
      // Test MQTT connection
      cy.testMqttConnection()
      cy.get('[data-cy="mqtt-test-result"]').should('contain', 'success')
      
      // Test unsaved changes warning
      cy.get('[data-cy="unsaved-changes-alert"]').should('be.visible')
      
      // Save configuration
      cy.saveConfiguration()
      cy.get('[data-cy="unsaved-changes-alert"]').should('not.exist')
    })

    it('should handle zone management correctly', () => {
      cy.navigateToTab('unified-config')
      cy.get('[data-cy="zones-tab"]').click()
      
      // Create new zone
      cy.createZone('Kitchen', 'Kitchen cleaning area with sensor integration')
      
      // Verify zone appears in list
      cy.get('[data-cy="zone-list"]').should('contain', 'Kitchen')
      
      // Configure zone settings
      cy.get('[data-cy="zone-edit-btn"]').first().click()
      cy.get('[data-cy="zone-automation-toggle"]').should('be.checked')
      cy.get('[data-cy="zone-schedule-toggle"]').click()
      cy.get('[data-cy="zone-start-time"]').type('09:00')
      cy.get('[data-cy="zone-end-time"]').type('17:00')
      
      // Save zone configuration
      cy.get('[data-cy="save-zone-btn"]').click()
      cy.get('[data-cy="zone-save-success"]').should('be.visible')
      
      // Verify zone efficiency score
      cy.get('[data-cy="zone-efficiency"]').should('contain', '%')
    })
  })

  describe('Error Handling and Recovery', () => {
    it('should handle API errors gracefully', () => {
      // Simulate API errors
      cy.intercept('GET', '/api/config', { statusCode: 500 }).as('configError')
      cy.intercept('GET', '/api/security', { statusCode: 503 }).as('securityError')
      
      cy.navigateToTab('unified-config')
      
      // Verify error handling
      cy.get('[data-cy="config-error-alert"]').should('be.visible')
      cy.get('[data-cy="config-retry-btn"]').should('be.visible')
      
      // Test retry functionality
      cy.intercept('GET', '/api/config', { fixture: 'config.json' }).as('configSuccess')
      cy.get('[data-cy="config-retry-btn"]').click()
      cy.get('[data-cy="config-error-alert"]').should('not.exist')
    })

    it('should validate form inputs correctly', () => {
      cy.navigateToTab('unified-config')
      cy.get('[data-cy="mqtt-tab"]').click()
      
      // Test invalid inputs
      cy.get('[data-cy="mqtt-broker-input"]').clear()
      cy.get('[data-cy="mqtt-port-input"]').clear().type('99999')
      
      // Verify validation errors
      cy.get('[data-cy="mqtt-broker-error"]').should('contain', 'required')
      cy.get('[data-cy="mqtt-port-error"]').should('contain', 'Invalid port')
      
      // Verify save button is disabled
      cy.get('[data-cy="save-config-btn"]').should('be.disabled')
      
      // Fix inputs
      cy.get('[data-cy="mqtt-broker-input"]').type('localhost')
      cy.get('[data-cy="mqtt-port-input"]').clear().type('1883')
      
      // Verify errors are cleared
      cy.get('[data-cy="mqtt-broker-error"]').should('not.exist')
      cy.get('[data-cy="mqtt-port-error"]').should('not.exist')
      cy.get('[data-cy="save-config-btn"]').should('not.be.disabled')
    })
  })

  describe('Performance and Responsiveness', () => {
    it('should load components within acceptable time limits', () => {
      const loadStartTime = Date.now()
      
      cy.navigateToTab('security')
      cy.waitForLoad()
      
      cy.then(() => {
        const loadTime = Date.now() - loadStartTime
        expect(loadTime).to.be.lessThan(3000) // 3 second limit
      })
      
      // Test component switching performance
      const switchStartTime = Date.now()
      cy.navigateToTab('unified-config')
      cy.waitForLoad()
      
      cy.then(() => {
        const switchTime = Date.now() - switchStartTime
        expect(switchTime).to.be.lessThan(1000) // 1 second limit for tab switching
      })
    })

    it('should handle large datasets efficiently', () => {
      // Mock large dataset
      cy.intercept('GET', '/api/devices', { fixture: 'large-device-list.json' })
      cy.intercept('GET', '/api/zones', { fixture: 'large-zone-list.json' })
      
      cy.navigateToTab('devices')
      cy.waitForLoad()
      
      // Verify pagination or virtualization is working
      cy.get('[data-cy="device-list"]').should('be.visible')
      cy.get('[data-cy="device-count"]').should('contain', 'devices')
      
      // Test search functionality
      cy.get('[data-cy="device-search"]').type('vacuum')
      cy.get('[data-cy="filtered-devices"]').should('contain', 'vacuum')
    })
  })

  afterEach(() => {
    // Clean up any test data or state
    cy.checkForErrors()
  })
})