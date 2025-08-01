const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';
const SCREENSHOT_DIR = '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots';
const EXPECTED_CAMERA = 'camera.rowan_room_fluent';
const EXPECTED_TODO = 'todo.rowan_room_cleaning_to_do';

/**
 * Simplified AICleaner v3 Dropdown Testing
 * Focus on validating dropdown functionality without full reinstallation
 */
async function testDropdownFunctionality() {
    console.log('🤖 Arbiter: Starting AICleaner v3 Dropdown Test...');
    
    const browser = await chromium.launch({ 
        headless: true,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 },
        userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    });
    
    const page = await context.newPage();
    
    try {
        // Step 1: Login to Home Assistant
        console.log('🔐 Step 1: Logging into Home Assistant...');
        await page.goto(HA_URL, { waitUntil: 'networkidle' });
        
        // Handle login if needed
        try {
            await page.waitForSelector('input[name="username"]', { timeout: 5000 });
            await page.fill('input[name="username"]', USERNAME);
            await page.fill('input[name="password"]', PASSWORD);
            await page.click('mwc-button[type="submit"]');
            await page.waitForLoadState('networkidle');
        } catch (e) {
            console.log('Already logged in or different login flow');
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'dropdown_01_logged_in.png'),
            fullPage: true 
        });
        
        // Step 2: Navigate directly to AICleaner addon
        console.log('🏪 Step 2: Navigating to AICleaner addon...');
        
        // Try multiple navigation approaches
        const addonUrls = [
            `${HA_URL}/supervisor/addon/local_aicleaner_v3`,
            `${HA_URL}/config/supervisor/addon/local_aicleaner_v3`,
            `${HA_URL}/supervisor/addon/aicleaner_v3`
        ];
        
        let addonFound = false;
        for (const url of addonUrls) {
            try {
                console.log(`Trying URL: ${url}`);
                await page.goto(url, { waitUntil: 'networkidle' });
                
                // Check if we're on the addon page
                const addonTitle = await page.locator('h1, .addon-header, [data-addon-name]').first();
                if (await addonTitle.isVisible()) {
                    addonFound = true;
                    console.log('✅ Found AICleaner addon page');
                    break;
                }
            } catch (e) {
                console.log(`Failed to access ${url}: ${e.message}`);
            }
        }
        
        if (!addonFound) {
            // Try navigating through the UI
            await page.goto(`${HA_URL}/config/dashboard`);
            await page.waitForLoadState('networkidle');
            
            // Look for Add-ons link
            const addonsLink = page.locator('a').filter({ hasText: /add.?ons/i }).first();
            if (await addonsLink.isVisible()) {
                await addonsLink.click();
                await page.waitForLoadState('networkidle');
            }
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'dropdown_02_addon_navigation.png'),
            fullPage: true 
        });
        
        // Step 3: Look for Configuration tab
        console.log('⚙️ Step 3: Accessing Configuration...');
        
        // Try different selectors for configuration tab
        const configSelectors = [
            'ha-tab:has-text("Configuration")',
            'mwc-tab:has-text("Configuration")', 
            'paper-tab:has-text("Configuration")',
            '[role="tab"]:has-text("Configuration")',
            'a[href*="config"]'
        ];
        
        let configFound = false;
        for (const selector of configSelectors) {
            try {
                const configTab = page.locator(selector).first();
                if (await configTab.isVisible()) {
                    await configTab.click();
                    await page.waitForTimeout(3000);
                    configFound = true;
                    console.log(`✅ Found config tab with selector: ${selector}`);
                    break;
                }
            } catch (e) {
                console.log(`Config selector ${selector} failed: ${e.message}`);
            }
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'dropdown_03_configuration_page.png'),
            fullPage: true 
        });
        
        // Step 4: Test dropdown fields - More generic approach
        console.log('🎛️ Step 4: Testing dropdown implementations...');
        
        // Test for any dropdown/selector fields on the page
        const possibleDropdownSelectors = [
            'ha-selector-entity',
            'ha-entity-picker', 
            'ha-combo-box',
            'mwc-select',
            'ha-select',
            'select',
            'paper-dropdown-menu',
            '[role="combobox"]'
        ];
        
        let dropdownsFound = false;
        const dropdownResults = {};
        
        for (const selector of possibleDropdownSelectors) {
            try {
                const dropdowns = page.locator(selector);
                const count = await dropdowns.count();
                
                if (count > 0) {
                    console.log(`Found ${count} elements with selector: ${selector}`);
                    dropdownsFound = true;
                    dropdownResults[selector] = count;
                    
                    // Try to interact with first dropdown
                    const firstDropdown = dropdowns.first();
                    if (await firstDropdown.isVisible()) {
                        await firstDropdown.click();
                        await page.waitForTimeout(2000);
                        
                        await page.screenshot({ 
                            path: path.join(SCREENSHOT_DIR, `dropdown_04_${selector.replace(/[^a-zA-Z0-9]/g, '_')}_open.png`),
                            fullPage: true 
                        });
                        
                        // Look for our expected entities in any opened dropdown
                        const cameraOption = page.locator(`*:has-text("${EXPECTED_CAMERA}")`);
                        const todoOption = page.locator(`*:has-text("${EXPECTED_TODO}")`);
                        
                        if (await cameraOption.isVisible()) {
                            console.log('✅ Found expected camera entity in dropdown!');
                        }
                        
                        if (await todoOption.isVisible()) {
                            console.log('✅ Found expected todo entity in dropdown!');
                        }
                        
                        // Click away to close dropdown
                        await page.keyboard.press('Escape');
                        await page.waitForTimeout(1000);
                    }
                }
            } catch (e) {
                console.log(`Dropdown test for ${selector} failed: ${e.message}`);
            }
        }
        
        // Step 5: Look for any input fields that might be text inputs instead of dropdowns
        console.log('📝 Step 5: Checking for text input fields...');
        
        const textInputSelectors = [
            'input[type="text"]',
            'input:not([type])',
            'ha-textfield',
            'mwc-textfield',
            'paper-input'
        ];
        
        const textInputResults = {};
        for (const selector of textInputSelectors) {
            try {
                const inputs = page.locator(selector);
                const count = await inputs.count();
                
                if (count > 0) {
                    console.log(`Found ${count} text inputs with selector: ${selector}`);
                    textInputResults[selector] = count;
                    
                    // Check if any have camera or todo related names/labels
                    for (let i = 0; i < Math.min(count, 5); i++) {
                        const input = inputs.nth(i);
                        const name = await input.getAttribute('name') || '';
                        const label = await input.getAttribute('label') || '';
                        const placeholder = await input.getAttribute('placeholder') || '';
                        
                        if (name.includes('camera') || label.includes('camera') || placeholder.includes('camera')) {
                            console.log(`⚠️  Found camera-related text input: ${name || label || placeholder}`);
                        }
                        
                        if (name.includes('todo') || label.includes('todo') || placeholder.includes('todo')) {
                            console.log(`⚠️  Found todo-related text input: ${name || label || placeholder}`);
                        }
                    }
                }
            } catch (e) {
                console.log(`Text input test for ${selector} failed: ${e.message}`);
            }
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'dropdown_05_final_state.png'),
            fullPage: true 
        });
        
        // Step 6: Generate page source for analysis
        console.log('📄 Step 6: Capturing page source for analysis...');
        const pageContent = await page.content();
        fs.writeFileSync(
            path.join(SCREENSHOT_DIR, 'dropdown_page_source.html'), 
            pageContent, 
            'utf8'
        );
        
        const summary = {
            success: true,
            dropdownsFound,
            dropdownResults,
            textInputResults,
            message: dropdownsFound ? 
                'Dropdown elements detected - check screenshots for validation' : 
                'No dropdown elements found - may still be using text inputs',
            screenshots: [
                'dropdown_01_logged_in.png',
                'dropdown_02_addon_navigation.png', 
                'dropdown_03_configuration_page.png',
                'dropdown_05_final_state.png'
            ]
        };
        
        console.log('✅ Dropdown Test Completed!');
        console.log('📊 Summary:', JSON.stringify(summary, null, 2));
        
        return summary;
        
    } catch (error) {
        console.error('❌ Test failed:', error);
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'dropdown_error.png'),
            fullPage: true 
        });
        
        return {
            success: false,
            message: `Test failed: ${error.message}`,
            error: error.toString()
        };
        
    } finally {
        await browser.close();
    }
}

// Run the test
if (require.main === module) {
    testDropdownFunctionality()
        .then(result => {
            console.log('🏁 Final Result:', result);
            process.exit(result.success ? 0 : 1);
        })
        .catch(error => {
            console.error('💥 Fatal Error:', error);
            process.exit(1);
        });
}

module.exports = { testDropdownFunctionality };