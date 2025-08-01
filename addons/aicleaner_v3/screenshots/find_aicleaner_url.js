const { chromium } = require('playwright');
const path = require('path');

async function findAICleanerURL() {
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
        
        // Try different URL patterns for AICleaner addon
        const urlsToTry = [
            'http://192.168.88.125:8123/hassio/addon/aicleaner_v3',
            'http://192.168.88.125:8123/hassio/addon/local_aicleaner_v3', 
            'http://192.168.88.125:8123/hassio/addon/aicleaner-v3',
            'http://192.168.88.125:8123/hassio/addon/local_aicleaner-v3',
            'http://192.168.88.125:8123/hassio/addon/sporebattyl_aicleaner_v3',
            'http://192.168.88.125:8123/hassio/addon/addon_aicleaner_v3'
        ];
        
        for (let i = 0; i < urlsToTry.length; i++) {
            const url = urlsToTry[i];
            console.log(`\\nTrying URL ${i + 1}/${urlsToTry.length}: ${url}`);
            
            try {
                await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
                await page.waitForTimeout(2000);
                
                const pageContent = await page.textContent('body');
                
                // Check if we successfully reached AICleaner addon page
                if (pageContent.includes('AICleaner') && !pageContent.includes('does not exist')) {
                    console.log('✅ SUCCESS! Found AICleaner addon at:', url);
                    
                    await page.screenshot({ 
                        path: path.join(__dirname, `aicleaner_found_${i + 1}.png`), 
                        fullPage: true 
                    });
                    
                    // Check addon status
                    console.log('\\n=== ADDON STATUS ===');
                    console.log('Contains "Install":', pageContent.includes('Install'));
                    console.log('Contains "INSTALL":', pageContent.includes('INSTALL'));
                    console.log('Contains "Start":', pageContent.includes('Start'));
                    console.log('Contains "START":', pageContent.includes('START'));
                    console.log('Contains "Stop":', pageContent.includes('Stop'));
                    console.log('Contains "STOP":', pageContent.includes('STOP'));
                    console.log('Contains "Configuration":', pageContent.includes('Configuration'));
                    console.log('Contains "Uninstall":', pageContent.includes('Uninstall'));
                    
                    // If Install button is present, try to install
                    const installButton = await page.locator('text="INSTALL"').first();
                    if (await installButton.isVisible()) {
                        console.log('\\n🔄 INSTALL button found - attempting installation...');
                        await installButton.click();
                        await page.waitForTimeout(5000);
                        
                        await page.screenshot({ 
                            path: path.join(__dirname, 'aicleaner_installation_started.png'), 
                            fullPage: true 
                        });
                        
                        // Wait for installation to complete
                        console.log('Waiting for installation to complete...');
                        for (let j = 0; j < 12; j++) { // Wait up to 2 minutes
                            await page.waitForTimeout(10000);
                            const currentContent = await page.textContent('body');
                            
                            if (currentContent.includes('START') || currentContent.includes('Configuration')) {
                                console.log('✅ Installation completed!');
                                break;
                            }
                            console.log(`Installation progress check ${j + 1}/12...`);
                        }
                        
                        await page.screenshot({ 
                            path: path.join(__dirname, 'aicleaner_after_installation.png'), 
                            fullPage: true 
                        });
                    }
                    
                    // Try to access Configuration
                    const configTab = await page.locator('text="Configuration"').first();
                    if (await configTab.isVisible()) {
                        console.log('\\n⚙️ Accessing Configuration tab...');
                        await configTab.click();
                        await page.waitForTimeout(3000);
                        
                        await page.screenshot({ 
                            path: path.join(__dirname, 'aicleaner_configuration_final.png'), 
                            fullPage: true 
                        });
                        console.log('Configuration page accessed successfully!');
                    }
                    
                    break; // Success - exit the loop
                    
                } else if (pageContent.includes('does not exist')) {
                    console.log('❌ Addon does not exist at this URL');
                } else {
                    console.log('❓ URL exists but may not be AICleaner addon');
                }
                
            } catch (error) {
                console.log('❌ Failed to access URL:', error.message);
            }
        }
        
        console.log('\\nURL testing completed');
        
    } catch (error) {
        console.error('Error during URL testing:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'url_testing_error.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

findAICleanerURL().catch(console.error);