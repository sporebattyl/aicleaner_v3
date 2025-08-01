const { chromium } = require('playwright');

async function verifyRepoAccess() {
    console.log('Verifying repository access and adding correctly...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 1000
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // First, verify the repository URL is accessible
        console.log('Testing repository URL access...');
        const repoUrls = [
            'https://github.com/sporebattyl/aicleaner_v3',
            'https://github.com/sporebattyl/aicleaner_v3.git'
        ];
        
        for (const url of repoUrls) {
            try {
                await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
                const title = await page.title();
                console.log(`✅ ${url} is accessible - Title: ${title}`);
                
                if (title.includes('aicleaner') || title.includes('sporebattyl')) {
                    console.log(`✅ Repository confirmed working: ${url}`);
                    break;
                }
            } catch (e) {
                console.log(`❌ ${url} failed: ${e.message}`);
            }
        }
        
        // Navigate to Home Assistant supervisor
        console.log('Navigating to Home Assistant...');
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
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repositories_page.png' });
        
        // Remove any existing aicleaner repositories first
        console.log('Checking for existing repositories to remove...');
        const existingRepos = await page.$$('text=/.*aicleaner.*/ , text=/.*sporebattyl.*/');
        if (existingRepos.length > 0) {
            console.log(`Found ${existingRepos.length} existing repositories to remove`);
            
            for (let i = 0; i < existingRepos.length; i++) {
                try {
                    // Look for delete/remove button near this repo
                    const removeButton = await existingRepos[i].locator('xpath=following::*[contains(text(), "Remove") or contains(@aria-label, "Remove")]').first();
                    if (removeButton) {
                        await removeButton.click();
                        await page.waitForTimeout(2000);
                        console.log(`Removed existing repository ${i}`);
                    }
                } catch (e) {
                    console.log(`Could not remove repository ${i}: ${e.message}`);
                }
            }
        }
        
        // Add repository with correct URL
        console.log('Adding repository with correct URL...');
        
        // Look for Add Repository button
        const addButtons = await page.$$('mwc-button, button, [role="button"]');
        let addButton = null;
        
        for (const button of addButtons) {
            const text = await button.textContent();
            const ariaLabel = await button.getAttribute('aria-label');
            
            if ((text && text.toLowerCase().includes('add')) || 
                (ariaLabel && ariaLabel.toLowerCase().includes('add'))) {
                addButton = button;
                console.log(`Found add button: "${text}" / "${ariaLabel}"`);
                break;
            }
        }
        
        if (addButton) {
            await addButton.click();
            await page.waitForTimeout(1000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/add_repo_dialog.png' });
            
            // Find URL input field
            const urlInput = await page.$('input[type="url"], input[placeholder*="repository"], input[name="repository"], mwc-textfield');
            if (urlInput) {
                console.log('Found URL input field');
                
                // Clear any existing content and enter correct URL
                await urlInput.fill('');
                await page.waitForTimeout(500);
                
                const correctUrl = 'https://github.com/sporebattyl/aicleaner_v3';
                console.log(`Entering URL: "${correctUrl}"`);
                await urlInput.type(correctUrl);
                
                await page.waitForTimeout(1000);
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/url_entered.png' });
                
                // Submit the form
                await page.keyboard.press('Enter');
                
                // Or look for submit/add button
                const submitButton = await page.$('mwc-button:has-text("Add"), button:has-text("Add"), mwc-button[type="submit"]');
                if (submitButton) {
                    await submitButton.click();
                }
                
                // Wait for repository to be added
                console.log('Waiting for repository to be processed...');
                await page.waitForTimeout(10000);
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repo_added.png' });
                
                // Check for success or error messages
                const errorMessage = await page.$('.error, [role="alert"], .warning');
                if (errorMessage) {
                    const errorText = await errorMessage.textContent();
                    console.log(`❌ Error adding repository: ${errorText}`);
                } else {
                    console.log('✅ Repository appears to have been added successfully');
                    
                    // Go to addon store to check if AICleaner is now available
                    await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'networkidle' });
                    await page.waitForTimeout(3000);
                    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/store_with_aicleaner.png' });
                    
                    // Search for AICleaner addon
                    const addonCards = await page.$$('.addon-card, ha-card, mwc-card');
                    let aicleanerFound = false;
                    
                    for (let i = 0; i < addonCards.length; i++) {
                        const cardText = await addonCards[i].textContent();
                        if (cardText.toLowerCase().includes('aicleaner') || cardText.toLowerCase().includes('ai cleaner')) {
                            console.log(`✅ AICleaner addon found in store!`);
                            aicleanerFound = true;
                            
                            // Click on it to see details
                            await addonCards[i].click();
                            await page.waitForLoadState('networkidle');
                            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_addon_ready.png' });
                            break;
                        }
                    }
                    
                    if (!aicleanerFound) {
                        console.log('❌ AICleaner addon not yet visible in store - may need more time');
                    }
                }
            } else {
                console.log('❌ Could not find URL input field');
            }
        } else {
            console.log('❌ Could not find Add Repository button');
        }
        
    } catch (error) {
        console.error('Error during repository verification:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/repo_verify_error.png' });
    } finally {
        await browser.close();
    }
}

verifyRepoAccess().catch(console.error);