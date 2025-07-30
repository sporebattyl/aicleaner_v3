const { chromium } = require('playwright');

async function installAddonProperly() {
    console.log('Installing AICleaner addon properly...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate to supervisor dashboard
        console.log('Navigating to supervisor...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        
        // Login if needed
        const loginForm = await page.$('input[name="username"]');
        if (loginForm) {
            console.log('Logging in...');
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            await page.keyboard.press('Enter');
            await page.waitForLoadState('networkidle');
        }
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/supervisor_dashboard.png' });
        
        // Go to Add-on Store
        console.log('Going to Add-on Store...');
        await page.click('text=Add-on Store');
        await page.waitForLoadState('networkidle');
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_store.png' });
        
        // Add repository first
        console.log('Adding repository...');
        const repoButton = await page.$('text=Repositories');
        if (repoButton) {
            await repoButton.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repositories_page.png' });
            
            // Add new repository
            const addRepoButton = await page.$('text=Add Repository, button[title="Add Repository"], .add-repository');
            if (addRepoButton) {
                await addRepoButton.click();
                await page.waitForTimeout(1000);
                
                // Enter repository URL
                const urlInput = await page.$('input[type="url"], input[placeholder*="repository"], input[name="repository"]');
                if (urlInput) {
                    await urlInput.fill('https://github.com/sporebattyl/aicleaner_v3');
                    await page.keyboard.press('Enter');
                    await page.waitForTimeout(3000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repository_added.png' });
                }
            }
        }
        
        // Go back to Add-on Store
        await page.click('text=Add-on Store');
        await page.waitForLoadState('networkidle');
        
        // Search for AICleaner
        console.log('Searching for AICleaner...');
        const searchBox = await page.$('input[type="search"]');
        if (searchBox) {
            await searchBox.fill('aicleaner');
            await page.keyboard.press('Enter');
            await page.waitForTimeout(2000);
        }
        
        // Look for AICleaner addon
        const aicleanerCards = await page.$$('text=/.*aicleaner.*/i');
        console.log(`Found ${aicleanerCards.length} AICleaner elements`);
        
        if (aicleanerCards.length > 0) {
            console.log('Found AICleaner addon, clicking to install...');
            await aicleanerCards[0].click();
            await page.waitForLoadState('networkidle');
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_addon_page.png' });
            
            // Click Install button
            const installButton = await page.$('text=Install, button:has-text("Install"), mwc-button:has-text("Install")');
            if (installButton) {
                console.log('Clicking Install button...');
                await installButton.click();
                
                // Wait for installation to complete
                console.log('Waiting for installation...');
                await page.waitForTimeout(30000); // 30 seconds for installation
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/installation_complete.png' });
                
                // Check if Configuration tab appears
                const configTab = await page.$('text=Configuration');
                if (configTab) {
                    console.log('Installation successful! Configuration tab available.');
                    await configTab.click();
                    await page.waitForTimeout(2000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/final_configuration_page.png' });
                    
                    // Check for dropdown selectors
                    const entityPickers = await page.$$('ha-entity-picker');
                    const dropdowns = await page.$$('mwc-select, paper-dropdown-menu');
                    console.log(`Found ${entityPickers.length} entity pickers and ${dropdowns.length} dropdowns`);
                    
                    // Look for camera and todo fields specifically
                    const cameraField = await page.$('[label*="camera"], [name*="camera"]');
                    const todoField = await page.$('[label*="todo"], [name*="todo"]');
                    
                    if (cameraField) {
                        console.log('Camera field found!');
                        await cameraField.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/camera_dropdown.png' });
                    }
                    
                    if (todoField) {
                        console.log('Todo field found!');
                        await todoField.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/todo_dropdown.png' });
                    }
                } else {
                    console.log('Configuration tab not found after installation');
                }
            } else {
                console.log('Install button not found');
            }
        } else {
            console.log('AICleaner addon not found in store');
        }
        
    } catch (error) {
        console.error('Error during addon installation:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/installation_error.png' });
    } finally {
        await browser.close();
    }
}

installAddonProperly().catch(console.error);