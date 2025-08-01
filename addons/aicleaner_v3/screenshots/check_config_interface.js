const { chromium } = require('playwright');
const fs = require('fs');

async function checkConfigInterface() {
    console.log('Starting configuration interface check...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate to Home Assistant
        console.log('Navigating to Home Assistant...');
        await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
        
        // Check if already logged in by looking for sidebar
        const sidebar = await page.$('mwc-drawer, .mdc-drawer, [slot="sidebar"]');
        if (sidebar) {
            console.log('Already logged in');
        } else {
            // Login
            console.log('Logging in...');
            await page.waitForSelector('input[name="username"]', { timeout: 5000 });
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            
            // Look for submit button with multiple selectors
            const submitButton = await page.$('button[type="submit"], mwc-button[type="submit"], .submit-btn');
            if (submitButton) {
                await submitButton.click();
            } else {
                await page.keyboard.press('Enter');
            }
        }
        
        await page.waitForLoadState('networkidle');
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/after_login.png' });
        
        // Direct navigation to AICleaner if it exists
        console.log('Checking for AICleaner directly...');
        try {
            await page.goto('http://192.168.88.125:8123/aicleaner_v3/webapp/', { waitUntil: 'networkidle', timeout: 10000 });
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_direct.png' });
        } catch (e) {
            console.log('Direct AICleaner access failed, checking addon store...');
            
            // Go back to main page
            await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
            
            // Go to Settings -> Add-ons
            await page.click('a[href="/config"]');
            await page.waitForLoadState('networkidle');
            await page.click('a[href="/hassio"]');
            await page.waitForLoadState('networkidle');
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addons_main_page.png' });
            
            // Look for AICleaner addon by searching
            const searchBox = await page.$('input[type="search"], mwc-textfield[type="search"]');
            if (searchBox) {
                await searchBox.fill('aicleaner');
                await page.keyboard.press('Enter');
                await page.waitForTimeout(2000);
            }
            
            // Look for any AICleaner addon
            const aicleanerElements = await page.$$('text=/.*aicleaner.*/i');
            console.log(`Found ${aicleanerElements.length} elements containing 'aicleaner'`);
            
            if (aicleanerElements.length > 0) {
                console.log('Found AICleaner addon, clicking first match...');
                await aicleanerElements[0].click();
                await page.waitForLoadState('networkidle');
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_addon_page.png' });
                
                // Check if Configuration tab exists
                const configTab = await page.$('text=Configuration');
                if (configTab) {
                    console.log('Found Configuration tab, clicking...');
                    await configTab.click();
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/config_interface.png' });
                    
                    // Analyze configuration interface
                    const configContent = await page.textContent('body');
                    console.log('Configuration page loaded');
                    
                    // Look for specific form elements
                    const formElements = await page.$$('form input, form select, form textarea, mwc-textfield, ha-entity-picker');
                    console.log(`Found ${formElements.length} form elements`);
                    
                    for (let i = 0; i < formElements.length; i++) {
                        const element = formElements[i];
                        const tagName = await element.evaluate(el => el.tagName);
                        const type = await element.getAttribute('type');
                        const name = await element.getAttribute('name');
                        const placeholder = await element.getAttribute('placeholder');
                        console.log(`Element ${i}: ${tagName}, type: ${type}, name: ${name}, placeholder: ${placeholder}`);
                    }
                } else {
                    console.log('Configuration tab not found - checking available tabs...');
                    const tabs = await page.$$('mwc-tab, .tab, [role="tab"]');
                    console.log(`Found ${tabs.length} tabs`);
                    for (let tab of tabs) {
                        const text = await tab.textContent();
                        console.log(`Tab: ${text}`);
                    }
                }
            } else {
                console.log('AICleaner addon not found in any form');
            }
        }
        
    } catch (error) {
        console.error('Error during configuration check:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/error_config_check.png' });
    } finally {
        await browser.close();
    }
}

checkConfigInterface().catch(console.error);