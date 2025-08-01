const { chromium } = require('playwright');
const path = require('path');

async function accessAICleanerDirectly() {
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
        
        // First, let's go back to the main addons page to see what AICleaner shows
        console.log('Navigating to Add-ons page...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(__dirname, 'addons_main_page.png'), 
            fullPage: true 
        });
        console.log('Main addons page screenshot taken');
        
        // Now try to find and click specifically on the AICleaner V3 card
        console.log('Looking for AICleaner V3 card specifically...');
        
        // Use a more specific selector for the AICleaner card
        const aicleanerCard = await page.locator('div:has-text("AICleaner V3"):has-text("AI-powered cleaning task")').first();
        
        if (await aicleanerCard.isVisible()) {
            console.log('Found AICleaner V3 card! Clicking on it...');
            await aicleanerCard.click();
            await page.waitForTimeout(5000);
        } else {
            console.log('AICleaner card not found with specific selector, trying coordinate-based click...');
            // Based on the screenshot, AICleaner V3 appears to be in the middle-right position
            // Let's try clicking at approximate coordinates
            await page.click('[data-path="/hassio/addon/local_aicleaner_v3"]');
        }
        
        await page.screenshot({ 
            path: path.join(__dirname, 'after_aicleaner_click.png'), 
            fullPage: true 
        });
        console.log('After clicking AICleaner screenshot taken');
        
        // Check if we're on the right addon page
        const pageContent = await page.textContent('body');
        console.log('Current page title contains "AICleaner":', pageContent.includes('AICleaner'));
        console.log('Current page contains "Z-Wave":', pageContent.includes('Z-Wave'));
        
        // If we're still not on AICleaner, try the direct URL approach
        if (!pageContent.includes('AICleaner') || pageContent.includes('Z-Wave')) {
            console.log('Not on AICleaner page, trying direct URL...');
            await page.goto('http://192.168.88.125:8123/hassio/addon/local_aicleaner_v3', { waitUntil: 'networkidle' });
            await page.waitForTimeout(3000);
        }
        
        await page.screenshot({ 
            path: path.join(__dirname, 'aicleaner_addon_page.png'), 
            fullPage: true 
        });
        console.log('AICleaner addon page screenshot taken');
        
        // Check current state of the addon
        const finalContent = await page.textContent('body');
        console.log('\\n=== ADDON STATUS ===');
        console.log('Contains "Install":', finalContent.includes('Install'));
        console.log('Contains "INSTALL":', finalContent.includes('INSTALL'));
        console.log('Contains "Start":', finalContent.includes('Start'));
        console.log('Contains "STOP":', finalContent.includes('STOP'));
        console.log('Contains "Configuration":', finalContent.includes('Configuration'));
        console.log('Contains "Uninstall":', finalContent.includes('Uninstall'));
        console.log('Contains "UNINSTALL":', finalContent.includes('UNINSTALL'));
        
        // If the addon shows Start button, it's installed but not running
        const startButton = await page.locator('text="START"').first();
        if (await startButton.isVisible()) {
            console.log('\\nAddon is INSTALLED but NOT RUNNING - Start button available');
        }
        
        // If the addon shows Stop button, it's installed and running
        const stopButton = await page.locator('text="STOP"').first();
        if (await stopButton.isVisible()) {
            console.log('\\nAddon is INSTALLED and RUNNING - Stop button available');
        }
        
        // Try to access Configuration tab
        const configTab = await page.locator('text="Configuration"').first();
        if (await configTab.isVisible()) {
            console.log('\\nConfiguration tab available - clicking...');
            await configTab.click();
            await page.waitForTimeout(3000);
            
            await page.screenshot({ 
                path: path.join(__dirname, 'aicleaner_configuration_tab.png'), 
                fullPage: true 
            });
            console.log('Configuration tab screenshot taken');
            
            // Look for our target configuration fields
            const configContent = await page.textContent('body');
            console.log('\\n=== CONFIGURATION OPTIONS ===');
            console.log('Contains "default_camera":', configContent.includes('default_camera'));
            console.log('Contains "default_todo_list":', configContent.includes('default_todo_list'));
            console.log('Contains camera selector:', configContent.includes('camera.rowan_room_fluent'));
            console.log('Contains todo selector:', configContent.includes('todo.rowan_room_cleaning_to_do'));
        }
        
        console.log('\\nDirect AICleaner access completed');
        
    } catch (error) {
        console.error('Error during direct access:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'direct_access_error.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

accessAICleanerDirectly().catch(console.error);