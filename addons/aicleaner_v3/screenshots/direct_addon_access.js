const { chromium } = require('playwright');

async function directAddonAccess() {
    console.log('Direct addon access test...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 500
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate directly to supervisor
        console.log('Navigating directly to supervisor...');
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
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/supervisor_direct.png' });
        
        // Try to go directly to AICleaner addon if it exists
        const potentialUrls = [
            'http://192.168.88.125:8123/hassio/addon/aicleaner_v3',
            'http://192.168.88.125:8123/hassio/addon/local_aicleaner_v3',
            'http://192.168.88.125:8123/hassio/addon/aicleaner_v3/info',
            'http://192.168.88.125:8123/hassio/ingress/aicleaner_v3'
        ];
        
        for (const url of potentialUrls) {
            console.log(`Trying URL: ${url}`);
            try {
                await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
                const currentUrl = page.url();
                console.log(`Result URL: ${currentUrl}`);
                
                const pageContent = await page.textContent('body');
                if (!pageContent.includes('404') && !pageContent.includes('Not Found')) {
                    console.log('Successfully accessed addon page!');
                    await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/addon_found_${Date.now()}.png` });
                    
                    // Look for Configuration tab
                    const configTab = await page.$('text=Configuration');
                    if (configTab) {
                        console.log('Configuration tab found, clicking...');
                        await configTab.click();
                        await page.waitForTimeout(2000);
                        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/final_config_page.png' });
                        
                        // Analyze the configuration form
                        const yaml = await page.$('textarea, .yaml-editor, [data-mode="yaml"]');
                        if (yaml) {
                            console.log('YAML configuration found - this confirms the issue!');
                            const yamlContent = await yaml.textContent() || await yaml.inputValue();
                            console.log('YAML content preview:', yamlContent.substring(0, 200));
                        }
                        
                        const entityPickers = await page.$$('ha-entity-picker');
                        console.log(`Found ${entityPickers.length} entity picker elements`);
                        
                        break;
                    }
                }
            } catch (e) {
                console.log(`Failed to access ${url}: ${e.message}`);
            }
        }
        
    } catch (error) {
        console.error('Error during direct addon access:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/direct_error.png' });
    } finally {
        await browser.close();
    }
}

directAddonAccess().catch(console.error);