const { chromium } = require('playwright');
const path = require('path');

async function testConfigurationDropdowns() {
    const browser = await chromium.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-dev-shm-usage']
    });
    
    const context = await browser.newContext({
        ignoreHTTPSErrors: true
    });
    
    const page = await context.newPage();
    
    try {
        console.log('Navigating to Home Assistant...');
        await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
        
        // Take screenshot of login page
        await page.screenshot({ 
            path: path.join(__dirname, 'login_page.png'), 
            fullPage: true 
        });
        console.log('Login page screenshot saved');
        
        // Login to Home Assistant
        console.log('Logging in...');
        
        // Wait for login form and fill it
        await page.waitForSelector('input[name="username"]', { timeout: 10000 });
        await page.fill('input[name="username"]', 'drewcifer');
        await page.fill('input[name="password"]', 'Minds63qq!');
        
        // Look for the submit button with various selectors
        const submitButton = await page.locator('button[type="submit"], input[type="submit"], .mdc-button, ha-progress-button').first();
        await submitButton.click();
        await page.waitForNavigation({ waitUntil: 'networkidle' });
        
        // Take screenshot of main dashboard
        await page.screenshot({ 
            path: path.join(__dirname, 'main_dashboard.png'), 
            fullPage: true 
        });
        console.log('Main dashboard screenshot saved');
        
        // Navigate to Supervisor
        console.log('Navigating to Supervisor...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        // Take screenshot of supervisor dashboard
        await page.screenshot({ 
            path: path.join(__dirname, 'supervisor_dashboard.png'), 
            fullPage: true 
        });
        console.log('Supervisor dashboard screenshot saved');
        
        // Navigate to add-on store or installed add-ons
        console.log('Looking for AICleaner v3 addon...');
        
        // Try to find the addon - look for it in various ways
        try {
            // Method 1: Direct URL to addon config
            await page.goto('http://192.168.88.125:8123/hassio/addon/aicleaner_v3/config', { waitUntil: 'networkidle' });
            await page.waitForTimeout(3000);
        } catch (error) {
            console.log('Direct addon URL failed, trying to find it via interface...');
            
            // Method 2: Navigate through the interface
            await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
            
            // Look for Add-on Store or Local add-ons section
            const addonsLink = await page.locator('text="Add-ons"').first();
            if (await addonsLink.isVisible()) {
                await addonsLink.click();
                await page.waitForTimeout(2000);
            }
            
            // Look for AICleaner addon
            const aicleanerLink = await page.locator('text*="AICleaner"').first();
            if (await aicleanerLink.isVisible()) {
                await aicleanerLink.click();
                await page.waitForTimeout(2000);
                
                // Navigate to Configuration tab
                const configTab = await page.locator('text="Configuration"').first();
                if (await configTab.isVisible()) {
                    await configTab.click();
                    await page.waitForTimeout(2000);
                }
            }
        }
        
        // Take screenshot of addon configuration page
        await page.screenshot({ 
            path: path.join(__dirname, 'addon_config_page.png'), 
            fullPage: true 
        });
        console.log('Addon configuration page screenshot saved');
        
        // Look for and screenshot specific configuration elements
        console.log('Looking for entity selector dropdowns...');
        
        // Try to find dropdown selectors for camera and todo list
        const cameraSelector = page.locator('label:has-text("default_camera")').locator('..').locator('select, mwc-select, ha-entity-picker');
        const todoSelector = page.locator('label:has-text("default_todo_list")').locator('..').locator('select, mwc-select, ha-entity-picker');
        
        if (await cameraSelector.isVisible()) {
            console.log('Camera selector found!');
            await cameraSelector.screenshot({ 
                path: path.join(__dirname, 'camera_selector.png') 
            });
            
            // Try to open the dropdown
            await cameraSelector.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ 
                path: path.join(__dirname, 'camera_dropdown_open.png'), 
                fullPage: true 
            });
        }
        
        if (await todoSelector.isVisible()) {
            console.log('Todo selector found!');
            await todoSelector.screenshot({ 
                path: path.join(__dirname, 'todo_selector.png') 
            });
            
            // Try to open the dropdown
            await todoSelector.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ 
                path: path.join(__dirname, 'todo_dropdown_open.png'), 
                fullPage: true 
            });
        }
        
        // Take a final comprehensive screenshot of the configuration area
        await page.screenshot({ 
            path: path.join(__dirname, 'final_config_state.png'), 
            fullPage: true 
        });
        console.log('Final configuration state screenshot saved');
        
    } catch (error) {
        console.error('Error during testing:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'error_state.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

testConfigurationDropdowns().catch(console.error);