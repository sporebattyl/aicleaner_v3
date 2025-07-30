const { chromium } = require('playwright');
const path = require('path');

async function installAICleanerAddon() {
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
        
        console.log('Login successful');
        
        // Navigate to Supervisor Add-ons
        console.log('Navigating to Add-ons...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(__dirname, 'addons_page_before_install.png'), 
            fullPage: true 
        });
        console.log('Add-ons page screenshot taken');
        
        // Look for AICleaner V3 and click on it
        console.log('Looking for AICleaner V3 addon...');
        const aicleanerCard = await page.locator('text="AICleaner V3"').first();
        
        if (await aicleanerCard.isVisible()) {
            console.log('AICleaner V3 found! Clicking to view details...');
            await aicleanerCard.click();
            await page.waitForTimeout(3000);
            
            await page.screenshot({ 
                path: path.join(__dirname, 'aicleaner_details.png'), 
                fullPage: true 
            });
            console.log('AICleaner details page screenshot taken');
            
            // Look for Install button
            const installButton = await page.locator('text="Install", text="INSTALL"').first();
            if (await installButton.isVisible()) {
                console.log('Install button found! Starting installation...');
                await installButton.click();
                await page.waitForTimeout(5000); // Give installation time to start
                
                await page.screenshot({ 
                    path: path.join(__dirname, 'installation_started.png'), 
                    fullPage: true 
                });
                console.log('Installation started');
                
                // Wait for installation to complete (this might take a while)
                console.log('Waiting for installation to complete...');
                await page.waitForTimeout(30000); // Wait 30 seconds for installation
                
                await page.screenshot({ 
                    path: path.join(__dirname, 'installation_progress.png'), 
                    fullPage: true 
                });
                
                // Check if we can see configuration or start options
                const configTab = await page.locator('text="Configuration"').first();
                const startButton = await page.locator('text="Start", text="START"').first();
                
                if (await configTab.isVisible()) {
                    console.log('Installation appears successful! Configuration tab is available.');
                    await configTab.click();
                    await page.waitForTimeout(2000);
                    
                    await page.screenshot({ 
                        path: path.join(__dirname, 'aicleaner_config_after_install.png'), 
                        fullPage: true 
                    });
                    console.log('Configuration page accessed after installation');
                }
                
                if (await startButton.isVisible()) {
                    console.log('Start button is available - addon is installed and ready!');
                }
                
            } else {
                console.log('No Install button found - addon may already be installed or there may be an issue');
                
                // Check if it shows as already installed
                const pageContent = await page.textContent('body');
                if (pageContent.includes('Start') || pageContent.includes('Configuration')) {
                    console.log('Addon appears to already be installed');
                }
            }
            
        } else {
            console.log('AICleaner V3 not found in the add-ons list');
        }
        
        await page.screenshot({ 
            path: path.join(__dirname, 'final_installation_state.png'), 
            fullPage: true 
        });
        console.log('Installation process completed');
        
    } catch (error) {
        console.error('Error during installation:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'installation_error.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

installAICleanerAddon().catch(console.error);