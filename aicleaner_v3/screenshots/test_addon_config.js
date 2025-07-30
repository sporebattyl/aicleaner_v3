const { chromium } = require('playwright');

async function testAddonConfig() {
    console.log('Testing addon configuration interface...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate directly to AICleaner addon
        console.log('Navigating to AICleaner addon...');
        await page.goto('http://192.168.88.125:8123/hassio/addon/aicleaner_v3', { waitUntil: 'networkidle' });
        
        // Login if needed
        const loginForm = await page.$('input[name="username"]');
        if (loginForm) {
            console.log('Logging in...');
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            await page.keyboard.press('Enter');
            await page.waitForLoadState('networkidle');
        }
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_installed.png' });
        
        // Go to Configuration tab
        console.log('Accessing Configuration tab...');
        const configTab = await page.$('text=Configuration');
        if (configTab) {
            await configTab.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/config_interface_working.png' });
            
            // Look for dropdown selectors
            console.log('Checking for dropdown selectors...');
            const entityPickers = await page.$$('ha-entity-picker');
            const selects = await page.$$('mwc-select, ha-select');
            const dropdowns = await page.$$('[role="combobox"], [role="listbox"]');
            
            console.log(`Found ${entityPickers.length} entity pickers`);
            console.log(`Found ${selects.length} select elements`);
            console.log(`Found ${dropdowns.length} dropdown elements`);
            
            // Look specifically for camera and todo fields
            const cameraElements = await page.$$('[label*="camera" i], [name*="camera" i], [data-field*="camera" i]');
            const todoElements = await page.$$('[label*="todo" i], [name*="todo" i], [data-field*="todo" i]');
            
            console.log(`Found ${cameraElements.length} camera-related fields`);
            console.log(`Found ${todoElements.length} todo-related fields`);
            
            // Test if we can interact with dropdowns
            if (entityPickers.length > 0) {
                console.log('Testing entity picker interaction...');
                try {
                    await entityPickers[0].click();
                    await page.waitForTimeout(1000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/dropdown_opened.png' });
                } catch (e) {
                    console.log('Could not interact with entity picker:', e.message);
                }
            }
            
            // Fill configuration if dropdowns are working
            if (entityPickers.length >= 2) {
                console.log('Attempting to configure camera and todo entities...');
                
                // Configure camera
                try {
                    await entityPickers[0].click();
                    await page.waitForTimeout(500);
                    
                    // Look for camera.rowan_room_fluent in dropdown
                    const cameraOption = await page.$('text=camera.rowan_room_fluent');
                    if (cameraOption) {
                        await cameraOption.click();
                        console.log('Camera entity selected successfully');
                    }
                } catch (e) {
                    console.log('Error configuring camera:', e.message);
                }
                
                // Configure todo list
                try {
                    await entityPickers[1].click();
                    await page.waitForTimeout(500);
                    
                    // Look for todo.rowan_room_cleaning_to_do in dropdown
                    const todoOption = await page.$('text=todo.rowan_room_cleaning_to_do');
                    if (todoOption) {
                        await todoOption.click();
                        console.log('Todo entity selected successfully');
                    }
                } catch (e) {
                    console.log('Error configuring todo:', e.message);
                }
                
                // Save configuration
                const saveButton = await page.$('mwc-button:has-text("Save"), button:has-text("Save")');
                if (saveButton) {
                    await saveButton.click();
                    console.log('Configuration saved');
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/config_saved.png' });
                }
            }
        } else {
            console.log('Configuration tab not found');
            
            // Check what tabs are available
            const tabs = await page.$$('mwc-tab, .tab, [role="tab"]');
            console.log(`Found ${tabs.length} tabs:`);
            for (let i = 0; i < tabs.length; i++) {
                const tabText = await tabs[i].textContent();
                console.log(`  Tab ${i}: "${tabText}"`);
            }
        }
        
        // Check Info tab for status
        const infoTab = await page.$('text=Info');
        if (infoTab) {
            await infoTab.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_info.png' });
        }
        
        // Check Logs tab for errors
        const logsTab = await page.$('text=Logs');
        if (logsTab) {
            await logsTab.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_logs.png' });
        }
        
    } catch (error) {
        console.error('Error testing addon configuration:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/config_test_error.png' });
    } finally {
        await browser.close();
    }
}

testAddonConfig().catch(console.error);