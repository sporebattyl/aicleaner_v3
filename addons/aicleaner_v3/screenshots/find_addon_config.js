const { chromium } = require('playwright');

async function findAddonConfig() {
    console.log('Starting addon configuration search...');
    
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
        
        // Login if needed
        const sidebar = await page.$('ha-sidebar, .sidebar, mwc-drawer');
        if (!sidebar) {
            console.log('Logging in...');
            await page.waitForSelector('input[name="username"]', { timeout: 5000 });
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            await page.keyboard.press('Enter');
            await page.waitForLoadState('networkidle');
        }
        
        // Navigate to Settings
        console.log('Going to Settings...');
        await page.click('a[href="/config"]');
        await page.waitForLoadState('networkidle');
        
        // Go to Add-ons
        console.log('Going to Add-ons...');
        await page.click('a[href="/hassio"]');
        await page.waitForLoadState('networkidle');
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/supervisor_main.png' });
        
        // Look for AICleaner addon - check both installed and store
        console.log('Looking for AICleaner addon...');
        
        // First try the "Add-ons" section
        const addonsSection = await page.$('text=Add-ons');
        if (addonsSection) {
            await addonsSection.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addons_list.png' });
        }
        
        // Look for AICleaner cards/tiles
        const aicleanerElements = await page.$$('text=/.*aicleaner.*/i, text=/.*ai.*cleaner.*/i');
        console.log(`Found ${aicleanerElements.length} potential AICleaner elements`);
        
        for (let i = 0; i < aicleanerElements.length; i++) {
            const element = aicleanerElements[i];
            const text = await element.textContent();
            console.log(`Element ${i}: "${text}"`);
        }
        
        // Try clicking on the first AICleaner element
        if (aicleanerElements.length > 0) {
            console.log('Clicking on first AICleaner element...');
            await aicleanerElements[0].click();
            await page.waitForLoadState('networkidle');
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_addon_details.png' });
            
            // Look for Configuration tab
            const configTab = await page.$('text=Configuration');
            if (configTab) {
                console.log('Found Configuration tab, clicking...');
                await configTab.click();
                await page.waitForTimeout(2000);
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_configuration_interface.png' });
                
                // Now look for form fields
                console.log('Analyzing configuration form...');
                
                // Look for default_camera and default_todo_list fields
                const formElements = await page.$$('input, select, textarea, ha-entity-picker, mwc-textfield, paper-input');
                console.log(`Found ${formElements.length} form elements`);
                
                for (let i = 0; i < formElements.length; i++) {
                    const element = formElements[i];
                    try {
                        const tagName = await element.evaluate(el => el.tagName);
                        const type = await element.getAttribute('type');
                        const name = await element.getAttribute('name');
                        const label = await element.getAttribute('label');
                        const placeholder = await element.getAttribute('placeholder');
                        const value = await element.getAttribute('value') || await element.inputValue().catch(() => '');
                        
                        console.log(`Form element ${i}: ${tagName}, type: ${type}, name: ${name}, label: ${label}, placeholder: ${placeholder}, value: ${value}`);
                        
                        // Take screenshot if this looks like camera or todo field
                        if (name && (name.includes('camera') || name.includes('todo'))) {
                            await element.screenshot({ path: `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/field_${name}.png` });
                        }
                    } catch (e) {
                        console.log(`Error analyzing element ${i}: ${e.message}`);
                    }
                }
                
                // Check if this looks like YAML or if we have proper selectors
                const pageContent = await page.textContent('body');
                if (pageContent.includes('YAML') || pageContent.includes('yaml')) {
                    console.log('YAML configuration detected - this might be the issue');
                } else {
                    console.log('No YAML detected in configuration');
                }
                
            } else {
                console.log('Configuration tab not found, checking available tabs...');
                const tabs = await page.$$('mwc-tab, .tab, [role="tab"]');
                for (let tab of tabs) {
                    const text = await tab.textContent();
                    console.log(`Available tab: "${text}"`);
                }
            }
        } else {
            console.log('No AICleaner elements found - checking all addon cards...');
            const addonCards = await page.$$('.addon-card, ha-card, mwc-card');
            console.log(`Found ${addonCards.length} addon cards`);
            
            for (let i = 0; i < Math.min(addonCards.length, 10); i++) {
                const card = addonCards[i];
                const text = await card.textContent();
                console.log(`Addon card ${i}: "${text.substring(0, 100)}..."`);
            }
        }
        
    } catch (error) {
        console.error('Error during addon configuration search:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/config_search_error.png' });
    } finally {
        await browser.close();
    }
}

findAddonConfig().catch(console.error);