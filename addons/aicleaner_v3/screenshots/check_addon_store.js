const { chromium } = require('playwright');
const path = require('path');

async function checkAddonStore() {
    const browser = await chromium.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-dev-shm-usage']
    });
    
    const context = await browser.newContext({
        ignoreHTTPSErrors: true
    });
    
    const page = await context.newPage();
    
    try {
        console.log('=== CHECKING ADDON STORE FOR AICLEANER ===');
        await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
        
        // Login
        await page.waitForSelector('input[name="username"]', { timeout: 10000 });
        await page.fill('input[name="username"]', 'drewcifer');
        await page.fill('input[name="password"]', 'Minds63qq!');
        
        const submitButton = await page.locator('button[type="submit"], input[type="submit"], .mdc-button, ha-progress-button').first();
        await submitButton.click();
        await page.waitForNavigation({ waitUntil: 'networkidle' });
        
        // Navigate to Settings -> Add-ons
        console.log('Navigating to Settings -> Add-ons...');
        await page.goto('http://192.168.88.125:8123/config/addons', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        // Take screenshot of addons page
        await page.screenshot({ 
            path: path.join(__dirname, 'addons_main_page.png'), 
            fullPage: true 
        });
        
        // Look for "Add-on Store" button/link
        const storeButton = await page.locator('text="Add-on Store", text="Store", [aria-label*="store"]').first();
        if (await storeButton.isVisible({ timeout: 5000 })) {
            console.log('Clicking Add-on Store...');
            await storeButton.click();
            await page.waitForTimeout(3000);
            
            await page.screenshot({ 
                path: path.join(__dirname, 'addon_store_page.png'), 
                fullPage: true 
            });
            
            // Look for AICleaner in the store
            console.log('Searching for AICleaner in store...');
            const searchSelectors = [
                'text*="AICleaner"',
                'text*="aicleaner"', 
                'text*="AI Cleaner"',
                '.addon-card:has-text("AICleaner")',
                '.addon-item:has-text("AICleaner")'
            ];
            
            let foundInStore = false;
            for (const selector of searchSelectors) {
                try {
                    const element = await page.locator(selector).first();
                    if (await element.isVisible({ timeout: 2000 })) {
                        console.log(`✅ Found AICleaner in store with selector: ${selector}`);
                        foundInStore = true;
                        
                        await element.click();
                        await page.waitForTimeout(2000);
                        
                        await page.screenshot({ 
                            path: path.join(__dirname, 'aicleaner_store_page.png'), 
                            fullPage: true 
                        });
                        break;
                    }
                } catch (e) {
                    console.log(`❌ Not found with selector: ${selector}`);
                }
            }
            
            if (!foundInStore) {
                console.log('❌ AICleaner not found in addon store');
                
                // Check repositories
                console.log('Checking repositories...');
                const repoButton = await page.locator('button:has-text("⋮"), [aria-label*="menu"]').first();
                if (await repoButton.isVisible({ timeout: 3000 })) {
                    await repoButton.click();
                    await page.waitForTimeout(1000);
                    
                    const repoOption = await page.locator('text="Repositories"').first();
                    if (await repoOption.isVisible({ timeout: 2000 })) {
                        await repoOption.click();
                        await page.waitForTimeout(2000);
                        
                        await page.screenshot({ 
                            path: path.join(__dirname, 'repositories_page.png'), 
                            fullPage: true 
                        });
                        
                        // Look for our repository
                        const repoUrl = 'https://github.com/sporebattyl/aicleaner_v3';
                        const repoPresent = await page.locator(`text*="${repoUrl}"`).isVisible().catch(() => false);
                        console.log(`Repository ${repoUrl} present: ${repoPresent}`);
                    }
                }
            }
        } else {
            console.log('❌ Add-on Store button not found');
            
            // Try alternative navigation
            await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'networkidle' });
            await page.waitForTimeout(3000);
            
            await page.screenshot({ 
                path: path.join(__dirname, 'direct_store_access.png'), 
                fullPage: true 
            });
        }
        
        // Finally, let's check installed addons
        console.log('Checking installed addons...');
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(__dirname, 'final_supervisor_check.png'), 
            fullPage: true 
        });
        
        // Get page content for text analysis
        const pageContent = await page.content();
        const hasAICleaner = pageContent.toLowerCase().includes('aicleaner') || pageContent.toLowerCase().includes('ai cleaner');
        console.log(`Page contains AICleaner references: ${hasAICleaner}`);
        
        if (hasAICleaner) {
            console.log('✅ AICleaner references found in page content');
        } else {
            console.log('❌ No AICleaner references found in page content');
        }
        
    } catch (error) {
        console.error('Error during addon store check:', error);
        await page.screenshot({ 
            path: path.join(__dirname, 'addon_store_error.png'), 
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

checkAddonStore().catch(console.error);