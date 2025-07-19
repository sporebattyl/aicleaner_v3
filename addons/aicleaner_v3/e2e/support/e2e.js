// Cypress E2E Support File for AICleaner v3

// Import commands.js using ES2015 syntax:
import './commands'

// Alternatively you can use CommonJS syntax:
// require('./commands')

// Global before hook
beforeEach(() => {
  // Set up any global state or intercepts
  cy.intercept('GET', '/api/health', { fixture: 'health.json' }).as('healthCheck')
  cy.intercept('GET', '/api/security', { fixture: 'security-status.json' }).as('securityStatus')
  cy.intercept('GET', '/api/config', { fixture: 'config.json' }).as('getConfig')
})

// Handle uncaught exceptions
Cypress.on('uncaught:exception', (err, runnable) => {
  // Returning false here prevents Cypress from failing the test
  // on uncaught exceptions, which can happen with async operations
  return false
})