const { chromium } = require('playwright');

async function forceRepoRefresh() {
    console.log('Forcing repository refresh to get latest changes...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate to repositories page
        console.log('Navigating to repositories page...');
        await page.goto('http://192.168.88.125:8123/hassio/store/repositories', { waitUntil: 'networkidle' });
        
        // Login if needed
        const loginForm = await page.$('input[name="username"]');
        if (loginForm) {
            console.log('Logging in...');
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            await page.keyboard.press('Enter');
            await page.waitForLoadState('networkidle');
        }
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repositories_before_refresh.png' });
        
        // Method 1: Remove and re-add repository
        console.log('Method 1: Removing existing repository...');
        
        // Find AICleaner repository
        const repoElements = await page.$$('text=/.*aicleaner.*/, text=/.*sporebattyl.*/');
        console.log(`Found ${repoElements.length} repository elements`);
        
        if (repoElements.length > 0) {
            // Try to find remove button for this repo
            for (let i = 0; i < repoElements.length; i++) {
                const repoElement = repoElements[i];
                
                // Look for remove/delete button near this repository
                const removeButton = await page.locator('button, mwc-button, [role="button"]').filter({ hasText: /remove|delete/i }).first();
                
                if (await removeButton.isVisible().catch(() => false)) {
                    console.log(`Removing repository ${i}...`);
                    await removeButton.click();
                    await page.waitForTimeout(2000);
                    
                    // Confirm removal if dialog appears
                    const confirmButton = await page.$('mwc-button:has-text("Remove"), button:has-text("Remove"), mwc-button:has-text("Delete"), button:has-text("Delete")');
                    if (confirmButton) {
                        await confirmButton.click();
                        await page.waitForTimeout(2000);
                    }
                }
            }
        }
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/after_remove.png' });
        
        // Method 2: Add repository fresh
        console.log('Method 2: Adding repository fresh...');
        
        // Find Add Repository button
        const addButton = await page.$('mwc-button, button, [role="button"]').filter({ hasText: /add/i }).first();
        
        if (addButton) {
            await addButton.click();
            await page.waitForTimeout(1000);
            
            // Enter repository URL
            const urlInput = await page.$('input[type="url"], input[placeholder*="repository"], mwc-textfield');
            if (urlInput) {
                await urlInput.fill('https://github.com/sporebattyl/aicleaner_v3');
                await page.keyboard.press('Enter');
                
                console.log('Waiting for fresh repository clone...');
                await page.waitForTimeout(10000); // Wait for clone to complete
                
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/fresh_repo_added.png' });
            }
        }
        
        // Method 3: Force supervisor reload
        console.log('Method 3: Checking supervisor reload...');
        
        // Navigate to supervisor dashboard
        await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
        await page.waitForTimeout(2000);
        
        // Look for reload/refresh buttons
        const reloadButton = await page.$('mwc-button:has-text("Reload"), button:has-text("Reload"), mwc-button:has-text("Refresh"), button:has-text("Refresh")');
        if (reloadButton) {
            console.log('Found reload button, clicking...');
            await reloadButton.click();
            await page.waitForTimeout(5000);
        }
        
        // Check addon store for AICleaner
        console.log('Checking if AICleaner appears in store...');
        await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'networkidle' });
        await page.waitForTimeout(3000);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/store_after_refresh.png' });
        
        // Search for AICleaner addon
        const addonCards = await page.$$('.addon-card, ha-card, mwc-card, [class*="addon"]');
        console.log(`Found ${addonCards.length} addon cards`);
        
        let aicleanerFound = false;
        for (let i = 0; i < addonCards.length; i++) {
            const cardText = await addonCards[i].textContent();
            if (cardText.toLowerCase().includes('aicleaner') || cardText.toLowerCase().includes('ai cleaner')) {
                console.log(`✅ AICleaner found in store! Card text: ${cardText.substring(0, 100)}...`);
                aicleanerFound = true;
                
                // Click on it to test installation
                await addonCards[i].click();
                await page.waitForLoadState('networkidle');
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_addon_page_fresh.png' });
                break;
            }
        }
        
        if (!aicleanerFound) {
            console.log('❌ AICleaner not found in store yet - may need more time or manual intervention');
        }
        
    } catch (error) {
        console.error('Error during repository refresh:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/refresh_error.png' });
    } finally {
        await browser.close();
    }
}

forceRepoRefresh().catch(console.error);