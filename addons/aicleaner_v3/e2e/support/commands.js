// AICleaner v3 Custom Cypress Commands

// Login command for authenticated tests
Cypress.Commands.add('login', (token = 'test-supervisor-token') => {
  cy.window().then((win) => {
    win.localStorage.setItem('supervisor_token', token)
  })
})

// Navigate to a specific tab in the main interface
Cypress.Commands.add('navigateToTab', (tabName) => {
  cy.get(`[data-cy="tab-${tabName}"]`).click()
  cy.url().should('include', `#${tabName}`)
})

// Wait for component to load with loading spinner
Cypress.Commands.add('waitForLoad', () => {
  cy.get('[data-cy="loading-spinner"]').should('not.exist')
})

// Check security status
Cypress.Commands.add('checkSecurityStatus', (expectedLevel = 'high') => {
  cy.get('[data-cy="security-level-badge"]').should('contain', expectedLevel.toUpperCase())
})

// Save configuration
Cypress.Commands.add('saveConfiguration', () => {
  cy.get('[data-cy="save-config-btn"]').click()
  cy.get('[data-cy="save-success-toast"]').should('be.visible')
})

// Test MQTT connection
Cypress.Commands.add('testMqttConnection', () => {
  cy.get('[data-cy="test-mqtt-connection-btn"]').click()
  cy.get('[data-cy="mqtt-test-result"]', { timeout: 10000 }).should('be.visible')
})

// Validate security token
Cypress.Commands.add('validateToken', (token) => {
  cy.get('[data-cy="validate-token-btn"]').click()
  cy.get('[data-cy="token-modal"]').should('be.visible')
  cy.get('[data-cy="token-input"]').type(token)
  cy.get('[data-cy="validate-token-submit"]').click()
})

// Create a new zone
Cypress.Commands.add('createZone', (zoneName, description = '') => {
  cy.get('[data-cy="add-zone-btn"]').click()
  cy.get('[data-cy="zone-modal"]').should('be.visible')
  cy.get('[data-cy="zone-name-input"]').type(zoneName)
  if (description) {
    cy.get('[data-cy="zone-description-input"]').type(description)
  }
  cy.get('[data-cy="create-zone-submit"]').click()
})

// Check for error messages
Cypress.Commands.add('checkForErrors', () => {
  cy.get('[data-cy="error-alert"]').should('not.exist')
  cy.get('[data-cy="validation-error"]').should('not.exist')
})

// Mock API responses for testing
Cypress.Commands.add('mockApiResponses', () => {
  cy.intercept('GET', '/api/health', { body: { status: 'healthy' } })
  cy.intercept('GET', '/api/security', { fixture: 'security-status.json' })
  cy.intercept('GET', '/api/config', { fixture: 'config.json' })
  cy.intercept('GET', '/api/mqtt/status', { fixture: 'mqtt-status.json' })
  cy.intercept('GET', '/api/zones', { fixture: 'zones.json' })
  cy.intercept('GET', '/api/devices', { fixture: 'devices.json' })
})