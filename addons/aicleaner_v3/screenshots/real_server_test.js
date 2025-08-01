const { chromium } = require('playwright');
const path = require('path');

async function testRealServer() {
    const browser = await chromium.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-dev-shm-usage']
    });
    
    const context = await browser.newContext({
        ignoreHTTPSErrors: true
    });
    
    const page = await context.newPage();
    
    try {
        console.log('=== ACCESSING REAL HOME ASSISTANT SERVER ===');
        await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
        
        // Login
        console.log('Logging in to real server...');
        await page.waitForSelector('input[name="username"]', { timeout: 10000 });
        await page.fill('input[name="username"]', 'drewcifer');
        await page.fill('input[name="password"]', 'Minds63qq!');
        
        const submitButton = await page.locator('button[type="submit"], input[type="submit"], .mdc-button, ha-progress-button').first();
        await submitButton.click();
        await page.waitForNavigation({ waitUntil: 'networkidle' });
        
        // Take screenshot of main dashboard
        await page.screenshot({ 
            path: path.join(__dirname, 'real_server_dashboard.png'), 
            fullPage: true 
        });
        console.log('✅ Successfully accessed real Home Assistant server');
        
        // Navigate to Add-on Store
        console.log('Navigating to Add-on Store...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(__dirname, 'real_supervisor_dashboard.png'), 
            fullPage: true 
        });
        
        // Look for AICleaner addon
        console.log('Looking for AICleaner v3 addon...');
        
        // Try multiple approaches to find the addon
        const addonSelectors = [
            'text="AICleaner V3"',
            'text*="AICleaner"',
            'text*="aicleaner"',
            '[aria-label*="AICleaner"]',
            '.addon-card:has-text("AICleaner")'
        ];
        
        let addonFound = false;
        let addonElement = null;
        
        for (const selector of addonSelectors) {
            try {
                addonElement = await page.locator(selector).first();
                if (await addonElement.isVisible({ timeout: 2000 })) {
                    console.log(`✅ Found addon with selector: ${selector}`);
                    addonFound = true;
                    break;
                }
            } catch (e) {
                console.log(`❌ Selector ${selector} not found`);
            }
        }
        
        if (addonFound && addonElement) {
            console.log('Clicking on AICleaner addon...');
            await addonElement.click();
            await page.waitForTimeout(2000);
            
            // Look for Configuration tab
            const configTab = await page.locator('text="Configuration"').first();
            if (await configTab.isVisible({ timeout: 5000 })) {
                console.log('Clicking Configuration tab...');
                await configTab.click();
                await page.waitForTimeout(3000);
                
                // Take screenshot of actual configuration page
                await page.screenshot({ 
                    path: path.join(__dirname, 'REAL_CONFIG_PAGE.png'), 
                    fullPage: true 
                });
                console.log('✅ Real configuration page screenshot saved');
                
                // Check for dropdown vs text fields
                console.log('=== ANALYZING ACTUAL CONFIGURATION INTERFACE ===');
                
                // Look for entity selector dropdowns
                const dropdownSelectors = [
                    'ha-entity-picker',
                    'ha-select',
                    'select',
                    '[role="combobox"]',
                    'mwc-select',
                    '.entity-picker'
                ];
                
                let dropdownsFound = [];
                for (const selector of dropdownSelectors) {
                    const elements = await page.locator(selector).all();
                    if (elements.length > 0) {
                        dropdownsFound.push(`${selector}: ${elements.length} found`);
                    }
                }
                
                // Look for text input fields
                const textInputs = await page.locator('input[type="text"], textarea').all();
                
                // Check for specific camera and todo fields
                const cameraField = await page.locator('label:has-text("camera"), label:has-text("Camera")').first();
                const todoField = await page.locator('label:has-text("todo"), label:has-text("Todo"), label:has-text("list")').first();
                
                console.log('=== CURRENT STATE ANALYSIS ===');
                console.log(`Dropdowns found: ${dropdownsFound.length > 0 ? dropdownsFound.join(', ') : 'NONE'}`);
                console.log(`Text inputs found: ${textInputs.length}`);
                console.log(`Camera field visible: ${await cameraField.isVisible().catch(() => false)}`);
                console.log(`Todo field visible: ${await todoField.isVisible().catch(() => false)}`);
                
                // Take focused screenshot of configuration area
                if (dropdownsFound.length > 0) {
                    console.log('✅ DROPDOWNS ARE PRESENT - Taking detailed screenshot');
                    await page.screenshot({ 
                        path: path.join(__dirname, 'DROPDOWNS_WORKING.png'), 
                        fullPage: true 
                    });
                } else {
                    console.log('❌ NO DROPDOWNS FOUND - Configuration shows text fields');
                    await page.screenshot({ 
                        path: path.join(__dirname, 'NO_DROPDOWNS_TEXT_FIELDS.png'), 
                        fullPage: true 
                    });
                }
                
            } else {
                console.log('❌ Configuration tab not found');
                await page.screenshot({ 
                    path: path.join(__dirname, 'addon_page_no_config.png'), 
                    fullPage: true 
                });
            }
        } else {
            console.log('❌ AICleaner addon not found on supervisor dashboard');
            
            // Try alternative approach - direct URL
            console.log('Trying direct addon URL...');
            const directUrls = [
                'http://192.168.88.125:8123/hassio/addon/aicleaner_v3/config',
                'http://192.168.88.125:8123/hassio/addon/local_aicleaner_v3/config',
                'http://192.168.88.125:8123/hassio/addon/aicleaner_v3/info'
            ];
            
            for (const url of directUrls) {
                try {
                    console.log(`Trying ${url}...`);
                    await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
                    await page.waitForTimeout(2000);
                    
                    await page.screenshot({ 
                        path: path.join(__dirname, `direct_url_${url.split('/').pop()}.png`), 
                        fullPage: true 
                    });
                    
                    // Check if we're on a valid addon page
                    const pageTitle = await page.title();
                    const hasAddonContent = await page.locator('text="Configuration", text="Info", text="Log"').first().isVisible().catch(() => false);
                    
                    if (hasAddonContent) {
                        console.log(`✅ Successfully accessed addon via ${url}`);
                        break;
                    }
                } catch (e) {
                    console.log(`❌ Failed to access ${url}: ${e.message}`);
                }
            }
        }
        
    } catch (error) {
        console.error('Error during real server testing:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'real_server_error.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

testRealServer().catch(console.error);