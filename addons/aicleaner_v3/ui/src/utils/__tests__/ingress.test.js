/**
 * Ingress Compatibility Tests
 * Phase 4A: Enhanced Home Assistant Integration Tests
 * 
 * Tests for ingress path detection and URL construction utilities.
 */

import {
  getIngressBasePath,
  getApiBaseUrl,
  isIngressMode,
  getIngressAwarePath,
  getIngressStatus
} from '../ingress';

// Mock window.location
const mockLocation = (pathname, origin = 'http://localhost:3000') => {
  delete window.location;
  window.location = {
    pathname,
    origin,
    href: `${origin}${pathname}`
  };
};

describe('Ingress Utilities', () => {
  beforeEach(() => {
    // Reset to default location before each test
    mockLocation('/');
  });

  describe('getIngressBasePath', () => {
    it('returns empty string for direct access', () => {
      mockLocation('/');
      expect(getIngressBasePath()).toBe('');
    });

    it('returns empty string for non-ingress paths', () => {
      mockLocation('/dashboard');
      expect(getIngressBasePath()).toBe('');
      
      mockLocation('/api/health');
      expect(getIngressBasePath()).toBe('');
    });

    it('returns ingress path for HA ingress URLs', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/');
      expect(getIngressBasePath()).toBe('/api/hassio_ingress/aicleaner_v3');
    });

    it('returns ingress path for HA ingress sub-paths', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/dashboard');
      expect(getIngressBasePath()).toBe('/api/hassio_ingress/aicleaner_v3');
    });
  });

  describe('getApiBaseUrl', () => {
    it('returns origin for direct access', () => {
      mockLocation('/', 'http://homeassistant:8000');
      expect(getApiBaseUrl()).toBe('http://homeassistant:8000');
    });

    it('returns origin with ingress path for HA ingress', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/', 'http://homeassistant:8123');
      expect(getApiBaseUrl()).toBe('http://homeassistant:8123/api/hassio_ingress/aicleaner_v3');
    });

    it('handles different origins correctly', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/', 'https://my-homeassistant.local:8123');
      expect(getApiBaseUrl()).toBe('https://my-homeassistant.local:8123/api/hassio_ingress/aicleaner_v3');
    });
  });

  describe('isIngressMode', () => {
    it('returns false for direct access', () => {
      mockLocation('/');
      expect(isIngressMode()).toBe(false);
    });

    it('returns false for non-ingress paths', () => {
      mockLocation('/dashboard');
      expect(isIngressMode()).toBe(false);
    });

    it('returns true for HA ingress paths', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/');
      expect(isIngressMode()).toBe(true);
    });

    it('returns true for HA ingress sub-paths', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/dashboard');
      expect(isIngressMode()).toBe(true);
    });
  });

  describe('getIngressAwarePath', () => {
    it('returns path unchanged for direct access', () => {
      mockLocation('/');
      expect(getIngressAwarePath('/api/status')).toBe('/api/status');
      expect(getIngressAwarePath('dashboard')).toBe('/dashboard');
    });

    it('prepends ingress base path for HA ingress', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/');
      expect(getIngressAwarePath('/api/status')).toBe('/api/hassio_ingress/aicleaner_v3/api/status');
      expect(getIngressAwarePath('/dashboard')).toBe('/api/hassio_ingress/aicleaner_v3/dashboard');
    });

    it('handles paths without leading slash', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/');
      expect(getIngressAwarePath('api/status')).toBe('/api/hassio_ingress/aicleaner_v3/api/status');
      expect(getIngressAwarePath('dashboard')).toBe('/api/hassio_ingress/aicleaner_v3/dashboard');
    });
  });

  describe('getIngressStatus', () => {
    it('returns correct status for direct access', () => {
      mockLocation('/', 'http://localhost:8000');
      const status = getIngressStatus();
      
      expect(status.isIngress).toBe(false);
      expect(status.basePath).toBe('');
      expect(status.apiBaseUrl).toBe('http://localhost:8000');
      expect(status.currentPath).toBe('/');
      expect(status.origin).toBe('http://localhost:8000');
    });

    it('returns correct status for HA ingress', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/dashboard', 'http://homeassistant:8123');
      const status = getIngressStatus();
      
      expect(status.isIngress).toBe(true);
      expect(status.basePath).toBe('/api/hassio_ingress/aicleaner_v3');
      expect(status.apiBaseUrl).toBe('http://homeassistant:8123/api/hassio_ingress/aicleaner_v3');
      expect(status.currentPath).toBe('/api/hassio_ingress/aicleaner_v3/dashboard');
      expect(status.origin).toBe('http://homeassistant:8123');
    });
  });

  describe('Edge Cases', () => {
    it('handles empty pathname', () => {
      mockLocation('');
      expect(getIngressBasePath()).toBe('');
      expect(isIngressMode()).toBe(false);
    });

    it('handles null/undefined pathname gracefully', () => {
      delete window.location;
      window.location = { pathname: null, origin: 'http://localhost' };
      
      // Should not throw errors
      expect(() => getIngressBasePath()).not.toThrow();
      expect(() => isIngressMode()).not.toThrow();
    });

    it('handles malformed ingress paths', () => {
      mockLocation('/api/hassio_ingress/');
      expect(getIngressBasePath()).toBe('');
      expect(isIngressMode()).toBe(false);
    });

    it('is case sensitive for ingress detection', () => {
      mockLocation('/API/HASSIO_INGRESS/aicleaner_v3/');
      expect(getIngressBasePath()).toBe('');
      expect(isIngressMode()).toBe(false);
    });
  });

  describe('Real-world Scenarios', () => {
    it('works with typical HA ingress setup', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/', 'http://homeassistant.local:8123');
      
      expect(isIngressMode()).toBe(true);
      expect(getApiBaseUrl()).toBe('http://homeassistant.local:8123/api/hassio_ingress/aicleaner_v3');
      expect(getIngressAwarePath('/api/zones')).toBe('/api/hassio_ingress/aicleaner_v3/api/zones');
    });

    it('works with HTTPS HA setup', () => {
      mockLocation('/api/hassio_ingress/aicleaner_v3/dashboard', 'https://homeassistant.local:8123');
      
      expect(isIngressMode()).toBe(true);
      expect(getApiBaseUrl()).toBe('https://homeassistant.local:8123/api/hassio_ingress/aicleaner_v3');
    });

    it('works with development setup', () => {
      mockLocation('/dashboard', 'http://localhost:3000');
      
      expect(isIngressMode()).toBe(false);
      expect(getApiBaseUrl()).toBe('http://localhost:3000');
      expect(getIngressAwarePath('/api/status')).toBe('/api/status');
    });
  });
});