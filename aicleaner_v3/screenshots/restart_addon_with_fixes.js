const { chromium } = require('playwright');

async function restartAddonWithFixes() {
    console.log('Restarting addon with fixes...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate to AICleaner addon
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
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_before_restart.png' });
        
        // Stop the addon first
        console.log('Stopping addon...');
        const stopButton = await page.$('mwc-button:has-text("Stop"), button:has-text("Stop")');
        if (stopButton) {
            await stopButton.click();
            await page.waitForTimeout(5000);
            console.log('Addon stopped');
        }
        
        // Update the addon to pull latest changes
        console.log('Checking for updates...');
        const updateButton = await page.$('mwc-button:has-text("Update"), button:has-text("Update")');
        if (updateButton) {
            await updateButton.click();
            await page.waitForTimeout(10000);
            console.log('Addon updated');
        }
        
        // Start the addon
        console.log('Starting addon...');
        const startButton = await page.$('mwc-button:has-text("Start"), button:has-text("Start")');
        if (startButton) {
            await startButton.click();
            await page.waitForTimeout(10000);
            console.log('Addon started');
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_restarted.png' });
        }
        
        // Check logs for errors
        console.log('Checking logs...');
        const logsTab = await page.$('text=Logs');
        if (logsTab) {
            await logsTab.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/logs_after_restart.png' });
            
            // Get log content
            const logContent = await page.textContent('.log-content, .logs, pre');
            if (logContent) {
                console.log('Recent logs:');
                console.log(logContent.substring(-1000)); // Last 1000 characters
            }
        }
        
        // Try accessing Configuration tab
        console.log('Testing Configuration tab...');
        const configTab = await page.$('text=Configuration');
        if (configTab) {
            await configTab.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/config_tab_working.png' });
            
            // Check for dropdown elements
            const entityPickers = await page.$$('ha-entity-picker');
            const dropdowns = await page.$$('mwc-select, ha-select');
            
            console.log(`Configuration loaded successfully!`);
            console.log(`Found ${entityPickers.length} entity pickers`);
            console.log(`Found ${dropdowns.length} dropdown selectors`);
            
            if (entityPickers.length > 0 || dropdowns.length > 0) {
                console.log('✅ DROPDOWN SELECTORS ARE NOW WORKING!');
                
                // Try to configure the entities
                const formElements = await page.$$('input, select, ha-entity-picker');
                console.log(`Found ${formElements.length} form elements`);
                
                // Look for specific fields
                for (let i = 0; i < formElements.length; i++) {
                    const element = formElements[i];
                    const name = await element.getAttribute('name');
                    const label = await element.getAttribute('label');
                    const type = await element.getAttribute('type');
                    
                    console.log(`Form element ${i}: name="${name}" label="${label}" type="${type}"`);
                    
                    // If this looks like camera field, configure it
                    if (name?.includes('camera') || label?.includes('camera')) {
                        try {
                            await element.click();
                            await page.waitForTimeout(500);
                            
                            const cameraOption = await page.$('text=camera.rowan_room_fluent');
                            if (cameraOption) {
                                await cameraOption.click();
                                console.log('✅ Camera entity configured!');
                            }
                        } catch (e) {
                            console.log('Could not configure camera:', e.message);
                        }
                    }
                    
                    // If this looks like todo field, configure it
                    if (name?.includes('todo') || label?.includes('todo')) {
                        try {
                            await element.click();
                            await page.waitForTimeout(500);
                            
                            const todoOption = await page.$('text=todo.rowan_room_cleaning_to_do');
                            if (todoOption) {
                                await todoOption.click();
                                console.log('✅ Todo entity configured!');
                            }
                        } catch (e) {
                            console.log('Could not configure todo:', e.message);
                        }
                    }
                }
                
                // Save configuration
                const saveButton = await page.$('mwc-button:has-text("Save"), button:has-text("Save")');
                if (saveButton) {
                    await saveButton.click();
                    console.log('✅ Configuration saved!');
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/final_success.png' });
                }
            } else {
                console.log('❌ No dropdown selectors found - may need further troubleshooting');
            }
        } else {
            console.log('❌ Configuration tab still not available');
        }
        
    } catch (error) {
        console.error('Error during addon restart:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/restart_error.png' });
    } finally {
        await browser.close();
    }
}

restartAddonWithFixes().catch(console.error);