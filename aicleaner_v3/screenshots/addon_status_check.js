const { chromium } = require('playwright');
const path = require('path');

async function checkAddonStatus() {
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
        
        // Login to Home Assistant
        console.log('Logging in...');
        await page.waitForSelector('input[name="username"]', { timeout: 10000 });
        await page.fill('input[name="username"]', 'drewcifer');
        await page.fill('input[name="password"]', 'Minds63qq!');
        
        const submitButton = await page.locator('button[type="submit"], input[type="submit"], .mdc-button, ha-progress-button').first();
        await submitButton.click();
        await page.waitForNavigation({ waitUntil: 'networkidle' });
        
        await page.screenshot({ 
            path: path.join(__dirname, 'logged_in_dashboard.png'), 
            fullPage: true 
        });
        console.log('Login successful');
        
        // Navigate to Supervisor
        console.log('Navigating to Supervisor dashboard...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(__dirname, 'supervisor_dashboard.png'), 
            fullPage: true 
        });
        console.log('Supervisor dashboard accessed');
        
        // Check Add-on Store
        console.log('Checking Add-on Store...');
        try {
            const storeButton = await page.locator('text="Add-on Store"').first();
            if (await storeButton.isVisible()) {
                await storeButton.click();
                await page.waitForTimeout(2000);
                
                await page.screenshot({ 
                    path: path.join(__dirname, 'addon_store.png'), 
                    fullPage: true 
                });
                console.log('Add-on Store accessed');
                
                // Check for repositories
                const repoButton = await page.locator('text="Repositories"').first();
                if (await repoButton.isVisible()) {
                    await repoButton.click();
                    await page.waitForTimeout(2000);
                    
                    await page.screenshot({ 
                        path: path.join(__dirname, 'repositories.png'), 
                        fullPage: true 
                    });
                    console.log('Repositories page accessed');
                }
            }
        } catch (error) {
            console.log('Add-on Store not accessible:', error.message);
        }
        
        // Check installed add-ons
        console.log('Checking installed add-ons...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);
        
        await page.screenshot({ 
            path: path.join(__dirname, 'installed_addons_view.png'), 
            fullPage: true 
        });
        
        // Try to access AICleaner v3 directly
        console.log('Attempting direct access to AICleaner v3...');
        try {
            await page.goto('http://192.168.88.125:8123/hassio/addon/aicleaner_v3', { waitUntil: 'networkidle' });
            await page.waitForTimeout(3000);
            
            await page.screenshot({ 
                path: path.join(__dirname, 'aicleaner_direct_access.png'), 
                fullPage: true 
            });
            console.log('Direct AICleaner access attempted');
            
            // Check if we're on an error page or the actual addon page
            const pageContent = await page.textContent('body');
            if (pageContent.includes('does not exist') || pageContent.includes('not found')) {
                console.log('CRITICAL: AICleaner v3 addon does NOT exist in Home Assistant');
            } else {
                console.log('AICleaner v3 addon found! Checking configuration...');
                
                // Try to access configuration
                const configTab = await page.locator('text="Configuration"').first();
                if (await configTab.isVisible()) {
                    await configTab.click();
                    await page.waitForTimeout(2000);
                    
                    await page.screenshot({ 
                        path: path.join(__dirname, 'aicleaner_config.png'), 
                        fullPage: true 
                    });
                    console.log('AICleaner configuration accessed');
                }
            }
        } catch (error) {
            console.log('Direct access failed:', error.message);
        }
        
        // Check the general addons page for any AICleaner reference
        console.log('Searching for AICleaner in addons list...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);
        
        const pageText = await page.textContent('body');
        if (pageText.toLowerCase().includes('aicleaner')) {
            console.log('AICleaner reference found on page');
        } else {
            console.log('NO AICleaner reference found on page');
        }
        
        await page.screenshot({ 
            path: path.join(__dirname, 'final_addon_status.png'), 
            fullPage: true 
        });
        console.log('Addon status check completed');
        
    } catch (error) {
        console.error('Error during addon status check:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'addon_status_error.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

checkAddonStatus().catch(console.error);