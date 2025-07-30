const { chromium } = require('playwright');

async function installViaDirectURL() {
    console.log('Installing via direct URL access...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate directly to supervisor addon store
        console.log('Navigating to addon store...');
        await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'networkidle' });
        
        // Login if needed
        const loginForm = await page.$('input[name="username"]');
        if (loginForm) {
            console.log('Logging in...');
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            await page.keyboard.press('Enter');
            await page.waitForLoadState('networkidle');
        }
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/store_direct.png' });
        
        // Try to access repositories page directly
        console.log('Going to repositories...');
        await page.goto('http://192.168.88.125:8123/hassio/store/repositories', { waitUntil: 'networkidle' });
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repositories_direct.png' });
        
        // Look for add repository functionality
        const addButtons = await page.$$('mwc-button, button, .add-repo, [aria-label*="add"]');
        console.log(`Found ${addButtons.length} potential add buttons`);
        
        for (let i = 0; i < addButtons.length; i++) {
            const button = addButtons[i];
            const text = await button.textContent();
            const ariaLabel = await button.getAttribute('aria-label');
            console.log(`Button ${i}: text="${text}" aria-label="${ariaLabel}"`);
            
            if (text?.toLowerCase().includes('add') || ariaLabel?.toLowerCase().includes('add')) {
                console.log(`Clicking button ${i}...`);
                await button.click();
                await page.waitForTimeout(2000);
                await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/after_add_click_${i}.png` });
                
                // Look for URL input
                const urlInput = await page.$('input[type="url"], input[placeholder*="repository"], input[name="repository"], mwc-textfield');
                if (urlInput) {
                    console.log('Found URL input, entering repository...');
                    await urlInput.fill('https://github.com/sporebattyl/aicleaner_v3');
                    await page.keyboard.press('Enter');
                    await page.waitForTimeout(5000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repository_submitted.png' });
                    break;
                }
            }
        }
        
        // Go back to store and look for AICleaner
        console.log('Going back to store...');
        await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/store_after_repo.png' });
        
        // Search for all addon cards
        const addonCards = await page.$$('.addon-card, ha-card, mwc-card');
        console.log(`Found ${addonCards.length} addon cards`);
        
        // Look through cards for AICleaner
        for (let i = 0; i < addonCards.length; i++) {
            const card = addonCards[i];
            const cardText = await card.textContent();
            console.log(`Card ${i}: ${cardText.substring(0, 100)}...`);
            
            if (cardText.toLowerCase().includes('aicleaner') || cardText.toLowerCase().includes('ai cleaner')) {
                console.log(`Found AICleaner in card ${i}, clicking...`);
                await card.click();
                await page.waitForLoadState('networkidle');
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_addon_details.png' });
                
                // Look for install button
                const installButton = await page.$('mwc-button:has-text("Install"), button:has-text("Install")');
                if (installButton) {
                    console.log('Found install button, clicking...');
                    await installButton.click();
                    
                    // Wait for installation
                    await page.waitForTimeout(30000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/installation_progress.png' });
                    
                    // Check for success
                    const successIndicators = await page.$$('text=/installed/i, text=/success/i, .success');
                    if (successIndicators.length > 0) {
                        console.log('Installation appears successful!');
                        
                        // Try to access configuration
                        const configTab = await page.$('text=Configuration');
                        if (configTab) {
                            await configTab.click();
                            await page.waitForTimeout(2000);
                            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/success_config_page.png' });
                        }
                    }
                }
                break;
            }
        }
        
    } catch (error) {
        console.error('Error during direct URL installation:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/direct_url_error.png' });
    } finally {
        await browser.close();
    }
}

installViaDirectURL().catch(console.error);