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
            path: path.join(__dirname, 'before_aicleaner_click.png'), 
            fullPage: true 
        });
        console.log('Add-ons page screenshot taken');
        
        // Look for AICleaner V3 using multiple methods
        console.log('Looking for AICleaner V3 addon with multiple selectors...');
        
        // Method 1: Look for text containing "AICleaner"
        let aicleanerCard = await page.locator(':has-text("AICleaner V3")').first();
        if (!(await aicleanerCard.isVisible())) {
            // Method 2: Look for text containing just "AICleaner"
            aicleanerCard = await page.locator(':has-text("AICleaner")').first();
        }
        if (!(await aicleanerCard.isVisible())) {
            // Method 3: Look for text containing "AI-powered cleaning"
            aicleanerCard = await page.locator(':has-text("AI-powered cleaning")').first();
        }
        
        if (await aicleanerCard.isVisible()) {
            console.log('AICleaner addon found! Clicking to view details...');
            
            // Highlight the element for debugging
            await aicleanerCard.highlight();
            await page.waitForTimeout(2000);
            
            await aicleanerCard.click();
            await page.waitForTimeout(5000);
            
            await page.screenshot({ 
                path: path.join(__dirname, 'aicleaner_details_page.png'), 
                fullPage: true 
            });
            console.log('AICleaner details page accessed');
            
            // Check the current page content to understand what we see
            const pageContent = await page.textContent('body');
            console.log('Page contains Install button:', pageContent.includes('Install'));
            console.log('Page contains INSTALL button:', pageContent.includes('INSTALL'));
            console.log('Page contains Start button:', pageContent.includes('Start'));
            console.log('Page contains Configuration:', pageContent.includes('Configuration'));
            
            // Look for Install button with multiple variations
            let installButton = await page.locator('text="Install"').first();
            if (!(await installButton.isVisible())) {
                installButton = await page.locator('text="INSTALL"').first();
            }
            if (!(await installButton.isVisible())) {
                installButton = await page.locator('button:has-text("Install")').first();
            }
            if (!(await installButton.isVisible())) {
                installButton = await page.locator('mwc-button:has-text("Install")').first();
            }
            
            if (await installButton.isVisible()) {
                console.log('Install button found! Starting installation...');
                await installButton.click();
                await page.waitForTimeout(5000);
                
                await page.screenshot({ 
                    path: path.join(__dirname, 'installation_initiated.png'), 
                    fullPage: true 
                });
                console.log('Installation initiated');
                
                // Wait for installation progress and monitor
                console.log('Monitoring installation progress...');
                for (let i = 0; i < 6; i++) { // Check every 10 seconds for 1 minute
                    await page.waitForTimeout(10000);
                    await page.screenshot({ 
                        path: path.join(__dirname, `installation_progress_${i + 1}.png`), 
                        fullPage: true 
                    });
                    console.log(`Installation progress check ${i + 1}/6`);
                    
                    // Check if installation completed
                    const currentContent = await page.textContent('body');
                    if (currentContent.includes('Start') || currentContent.includes('Configuration')) {
                        console.log('Installation appears to have completed!');
                        break;
                    }
                }
                
                // Final check after installation
                await page.screenshot({ 
                    path: path.join(__dirname, 'installation_final_state.png'), 
                    fullPage: true 
                });
                
                // Try to access configuration
                const configTab = await page.locator('text="Configuration"').first();
                if (await configTab.isVisible()) {
                    console.log('Configuration tab available - installation successful!');
                    await configTab.click();
                    await page.waitForTimeout(3000);
                    
                    await page.screenshot({ 
                        path: path.join(__dirname, 'aicleaner_configuration_page.png'), 
                        fullPage: true 
                    });
                    console.log('Configuration page accessed successfully');
                }
                
            } else {
                console.log('Install button not found. Checking current state...');
                
                // Take a screenshot to see current state
                await page.screenshot({ 
                    path: path.join(__dirname, 'no_install_button_state.png'), 
                    fullPage: true 
                });
                
                // Check if already installed
                const startButton = await page.locator('text="Start"').first();
                if (await startButton.isVisible()) {
                    console.log('Start button found - addon appears to already be installed');
                }
            }
            
        } else {
            console.log('AICleaner addon not found with any method');
            
            // Let's see what's actually on the page
            const allText = await page.textContent('body');
            console.log('Page contains these addon names:');
            const lines = allText.split('\n');
            lines.forEach(line => {
                if (line.includes('V3') || line.includes('AICleaner') || line.includes('AI')) {
                    console.log(`- ${line.trim()}`);
                }
            });
        }
        
        await page.screenshot({ 
            path: path.join(__dirname, 'final_addon_installation_state.png'), 
            fullPage: true 
        });
        console.log('Installation process completed');
        
    } catch (error) {
        console.error('Error during installation:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'installation_error_final.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

installAICleanerAddon().catch(console.error);