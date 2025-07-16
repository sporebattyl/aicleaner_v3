import { test, expect } from '@playwright/test';

test.describe('Analytics Dashboard', () => {
    test.beforeEach(async ({ page }) => {
        // Mock API responses
        await page.route('**/api/analytics*', async route => {
            const mockData = {
                metrics: {
                    uptime: 99.5,
                    avg_response_time: 42,
                    active_devices: 15,
                    error_count: 2,
                    response_time_trend: '+3%',
                    device_trend: '+4'
                },
                performance: {
                    timestamps: ['2024-01-01T10:00:00Z', '2024-01-01T10:05:00Z'],
                    cpu: [25, 30],
                    memory: [65, 70],
                    network: [12, 15]
                },
                usage: {
                    ai_requests: 150,
                    mqtt_messages: 3200,
                    device_updates: 850,
                    zone_triggers: 95,
                    api_calls: 1250
                },
                health: {
                    database: true,
                    mqtt: true,
                    ai_provider: false
                },
                errors: [
                    {
                        timestamp: '2024-01-01T10:00:00Z',
                        message: 'Connection timeout',
                        source: 'API',
                        severity: 'High'
                    }
                ]
            };
            await route.fulfill({ json: mockData });
        });

        // Navigate to analytics page
        await page.goto('/analytics');
    });

    test('loads analytics dashboard successfully', async ({ page }) => {
        // Wait for the dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check key metrics are displayed
        await expect(page.getByText('99.5%')).toBeVisible(); // Uptime
        await expect(page.getByText('42ms')).toBeVisible(); // Response time
        await expect(page.getByText('15')).toBeVisible(); // Active devices
        await expect(page.getByText('2')).toBeVisible(); // Error count
    });

    test('displays performance charts', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check that chart containers are present
        await expect(page.getByText('Performance Metrics')).toBeVisible();
        await expect(page.getByText('Feature Usage')).toBeVisible();
        
        // Check that canvas elements for charts are present
        await expect(page.locator('canvas').first()).toBeVisible();
    });

    test('changes time range and updates data', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Change time range
        await page.selectOption('[aria-label="Select time range"]', '7d');
        
        // Verify the selection changed
        await expect(page.locator('[aria-label="Select time range"]')).toHaveValue('7d');
        
        // Check that announcement was made (accessibility)
        await expect(page.getByText('Time range changed to 7d')).toBeVisible({ timeout: 1000 });
    });

    test('toggles auto refresh functionality', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check initial state shows "Live"
        await expect(page.getByText('Live')).toBeVisible();
        
        // Toggle auto refresh off
        await page.click('[aria-label="Auto Refresh"]');
        
        // Check state changed to "Paused"
        await expect(page.getByText('Paused')).toBeVisible();
    });

    test('exports analytics data as JSON', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Set up download promise before clicking
        const downloadPromise = page.waitForEvent('download');
        
        // Click export dropdown
        await page.click('[aria-label="Export analytics data"]');
        
        // Click JSON export
        await page.click('text=JSON');
        
        // Wait for download to start
        const download = await downloadPromise;
        
        // Verify download filename
        expect(download.suggestedFilename()).toMatch(/analytics_24h\.json/);
    });

    test('exports analytics data as PDF', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Set up download promise before clicking
        const downloadPromise = page.waitForEvent('download');
        
        // Click export dropdown
        await page.click('[aria-label="Export analytics data"]');
        
        // Click PDF export
        await page.click('text=PDF Report');
        
        // Wait for download to start
        const download = await downloadPromise;
        
        // Verify download filename
        expect(download.suggestedFilename()).toMatch(/analytics_24h\.pdf/);
    });

    test('displays system health status correctly', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check system health section
        await expect(page.getByText('System Health Status')).toBeVisible();
        
        // Check health indicators
        await expect(page.getByText('Database Connection')).toBeVisible();
        await expect(page.getByText('MQTT Broker')).toBeVisible();
        await expect(page.getByText('AI Provider')).toBeVisible();
        
        // Check status badges - should show OK for database and MQTT, Error for AI
        const okBadges = page.locator('text=OK');
        const errorBadges = page.locator('text=Error');
        
        await expect(okBadges).toHaveCount(2);
        await expect(errorBadges).toHaveCount(1);
    });

    test('displays recent errors table', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check errors section
        await expect(page.getByText('Recent Errors')).toBeVisible();
        
        // Check error details
        await expect(page.getByText('Connection timeout')).toBeVisible();
        await expect(page.getByText('API')).toBeVisible();
        await expect(page.getByText('High')).toBeVisible();
    });

    test('manually refreshes data', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Click refresh button
        await page.click('[aria-label="Manually refresh analytics data"]');
        
        // Check that announcement was made (accessibility)
        await expect(page.getByText('Analytics data updated')).toBeVisible({ timeout: 1000 });
    });

    test('changes refresh interval', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Change refresh interval
        await page.selectOption('[aria-label="Refresh Interval"]', '60');
        
        // Check that announcement was made (accessibility)
        await expect(page.getByText('Refresh interval set to 60 seconds')).toBeVisible({ timeout: 1000 });
    });

    test('accessibility features work correctly', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check ARIA labels are present
        await expect(page.locator('[aria-label="System uptime percentage"]')).toBeVisible();
        await expect(page.locator('[aria-label="Average response time"]')).toBeVisible();
        await expect(page.locator('[aria-label="Active devices count"]')).toBeVisible();
        await expect(page.locator('[aria-label="Error count"]')).toBeVisible();
        
        // Check chart accessibility
        await expect(page.locator('[aria-label*="Performance metrics chart"]')).toBeVisible();
        await expect(page.locator('[aria-label*="Usage statistics bar chart"]')).toBeVisible();
    });

    test('responsive design works on mobile', async ({ page }) => {
        // Set mobile viewport
        await page.setViewportSize({ width: 375, height: 667 });
        
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Check that key elements are still visible and properly arranged
        await expect(page.getByText('System Uptime')).toBeVisible();
        await expect(page.getByText('Performance Metrics')).toBeVisible();
        await expect(page.getByText('System Health Status')).toBeVisible();
        
        // Check that dropdowns and buttons are still functional
        await page.selectOption('[aria-label="Select time range"]', '7d');
        await expect(page.locator('[aria-label="Select time range"]')).toHaveValue('7d');
    });

    test('handles API errors gracefully', async ({ page }) => {
        // Mock API error response
        await page.route('**/api/analytics*', async route => {
            await route.fulfill({ status: 500, body: 'Internal Server Error' });
        });
        
        // Navigate to analytics page
        await page.goto('/analytics');
        
        // Check error state is displayed
        await expect(page.getByText('Failed to load analytics data')).toBeVisible();
    });

    test('keyboard navigation works correctly', async ({ page }) => {
        // Wait for dashboard to load
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
        
        // Test tab navigation through interactive elements
        await page.keyboard.press('Tab');
        await page.keyboard.press('Tab');
        
        // Check that focus indicators are visible (if CSS is properly loaded)
        const focusedElement = page.locator(':focus');
        await expect(focusedElement).toBeVisible();
        
        // Test that enter key activates buttons
        await page.keyboard.press('Enter');
        
        // Should work for accessible elements
        await expect(page.getByText('Analytics Dashboard')).toBeVisible();
    });
});