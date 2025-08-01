const { chromium } = require('playwright');

async function clickAICleanerSidebar() {
    console.log('Starting AICleaner sidebar click test...');
    
    const browser = await chromium.launch({ 
        headless: false,
        slowMo: 500
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Navigate to Home Assistant
        console.log('Navigating to Home Assistant...');
        await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
        
        // Check if already logged in
        const sidebar = await page.$('ha-sidebar, .sidebar, mwc-drawer');
        if (!sidebar) {
            console.log('Logging in...');
            await page.waitForSelector('input[name="username"]', { timeout: 5000 });
            await page.fill('input[name="username"]', 'drewcifer');
            await page.fill('input[name="password"]', 'Minds63qq!');
            await page.keyboard.press('Enter');
            await page.waitForLoadState('networkidle');
        }
        
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/main_dashboard.png' });
        
        // Look for AICleaner in sidebar - try multiple selectors
        console.log('Looking for AICleaner in sidebar...');
        
        // Check if it's "AICleaner" or "AI Cleaner v3"
        const aicleanerSelectors = [
            'text=AICleaner',
            'text="AI Cleaner v3"',
            'text="AICleaner"',
            '[href*="aicleaner"]',
            'a:has-text("AICleaner")',
            'a:has-text("AI Cleaner")'
        ];
        
        let aicleanerLink = null;
        for (const selector of aicleanerSelectors) {
            try {
                aicleanerLink = await page.$(selector);
                if (aicleanerLink) {
                    console.log(`Found AICleaner link with selector: ${selector}`);
                    break;
                }
            } catch (e) {
                continue;
            }
        }
        
        if (aicleanerLink) {
            console.log('Clicking AICleaner link...');
            await aicleanerLink.click();
            
            // Wait for navigation or content to load
            await page.waitForTimeout(3000);
            await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_clicked.png' });
            
            // Check what URL we ended up at
            const currentUrl = page.url();
            console.log(`Current URL after clicking: ${currentUrl}`);
            
            // Check page content
            const pageTitle = await page.title();
            console.log(`Page title: ${pageTitle}`);
            
            // Look for any error messages or content
            const bodyText = await page.textContent('body');
            if (bodyText.includes('404') || bodyText.includes('Not Found')) {
                console.log('404 error detected');
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_404.png' });
            } else if (bodyText.includes('configuration') || bodyText.includes('Configuration')) {
                console.log('Configuration page detected');
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_config.png' });
            } else {
                console.log('Unknown page content - taking general screenshot');
                await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/aicleaner_content.png' });
            }
            
        } else {
            console.log('AICleaner link not found in sidebar');
            
            // Let's examine the sidebar content
            const sidebarLinks = await page.$$('ha-sidebar a, .sidebar a, mwc-drawer a');
            console.log(`Found ${sidebarLinks.length} sidebar links`);
            
            for (let i = 0; i < Math.min(sidebarLinks.length, 20); i++) {
                const link = sidebarLinks[i];
                const text = await link.textContent();
                const href = await link.getAttribute('href');
                console.log(`Sidebar link ${i}: "${text}" -> ${href}`);
            }
        }
        
    } catch (error) {
        console.error('Error during AICleaner sidebar test:', error);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/sidebar_error.png' });
    } finally {
        await browser.close();
    }
}

clickAICleanerSidebar().catch(console.error);