/**
 * Ingress Compatibility Utilities
 * Phase 4A: Enhanced Home Assistant Integration
 * 
 * Utilities for detecting and handling Home Assistant ingress paths
 * for seamless UI integration.
 */

/**
 * Get the ingress base path if running under Home Assistant ingress
 * @returns {string} The ingress base path or empty string for direct access
 */
export function getIngressBasePath() {
  const ingressPrefix = '/api/hassio_ingress/aicleaner_v3';
  const path = window.location.pathname;

  // Handle null/undefined pathname gracefully
  if (!path || typeof path !== 'string') {
    return '';
  }

  if (path.startsWith(ingressPrefix)) {
    // If running under ingress, return the full ingress path
    // e.g., "/api/hassio_ingress/aicleaner_v3"
    return ingressPrefix;
  }
  
  // If not under ingress, return an empty string for direct access
  return '';
}

/**
 * Get the API base URL with ingress path handling
 * @returns {string} Complete base URL for API calls
 */
export function getApiBaseUrl() {
  const basePath = getIngressBasePath();
  // Append the base path to the origin for API calls
  // If basePath is empty, it will just be window.location.origin
  return window.location.origin + basePath;
}

/**
 * Check if the app is running in Home Assistant ingress mode
 * @returns {boolean} True if running under ingress, false for direct access
 */
export function isIngressMode() {
  return getIngressBasePath() !== '';
}

/**
 * Get a URL path with ingress base path prepended if needed
 * @param {string} path - The path to convert
 * @returns {string} Path with ingress base if in ingress mode
 */
export function getIngressAwarePath(path) {
  const basePath = getIngressBasePath();
  
  // Ensure path starts with /
  if (!path.startsWith('/')) {
    path = '/' + path;
  }
  
  return basePath + path;
}

/**
 * Get ingress status information for debugging
 * @returns {object} Ingress status object
 */
export function getIngressStatus() {
  return {
    isIngress: isIngressMode(),
    basePath: getIngressBasePath(),
    apiBaseUrl: getApiBaseUrl(),
    currentPath: window.location.pathname,
    origin: window.location.origin
  };
}

// Log ingress status for debugging (only in development)
if (process.env.NODE_ENV === 'development') {
  console.log('Ingress Status:', getIngressStatus());
}