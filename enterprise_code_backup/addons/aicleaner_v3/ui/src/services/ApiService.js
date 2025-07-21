
/**
 * API Service for HTTP requests
 * Phase 4A: Enhanced Home Assistant Integration - Ingress Compatible
 */

import { getApiBaseUrl } from '../utils/ingress';

class ApiService {
    constructor() {
        this.baseURL = getApiBaseUrl(); // Use ingress-aware base URL
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}/api${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // Configuration API
    async getConfiguration() {
        return this.request('/config');
    }

    async updateConfiguration(config) {
        return this.request('/config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
    }

    // Tiered Configuration API
    async getTieredConfig(tier) {
        return this.request(`/config/tiered/${tier}`);
    }

    async updateTieredConfig(tier, config) {
        return this.request(`/config/tiered/${tier}`, {
            method: 'PUT',
            body: JSON.stringify(config)
        });
    }

    async getMergedConfiguration() {
        return this.request('/config/merged');
    }

    async getTierCapabilities() {
        return this.request('/config/tiers');
    }

    async getConfigurationHealth() {
        return this.request('/config/health');
    }

    // Device API
    async getDevices() {
        return this.request('/devices');
    }

    async controlDevice(deviceId, action) {
        return this.request(`/devices/${deviceId}/control`, {
            method: 'POST',
            body: JSON.stringify(action)
        });
    }

    // Zone API
    async getZones() {
        return this.request('/zones');
    }

    async createZone(zone) {
        return this.request('/zones', {
            method: 'POST',
            body: JSON.stringify(zone)
        });
    }

    async updateZone(zoneId, zone) {
        return this.request(`/zones/${zoneId}`, {
            method: 'PUT',
            body: JSON.stringify(zone)
        });
    }

    async deleteZone(zoneId) {
        return this.request(`/zones/${zoneId}`, {
            method: 'DELETE'
        });
    }

    async toggleZone(zoneId, active) {
        return this.request(`/zones/${zoneId}/toggle`, {
            method: 'POST',
            body: JSON.stringify({ active })
        });
    }

    // Metrics API
    async getMetrics() {
        return this.request('/metrics');
    }

    // Health Check
    async getHealth() {
        return this.request('/health');
    }
}

export default new ApiService();
