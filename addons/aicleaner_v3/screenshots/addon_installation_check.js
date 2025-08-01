const puppeteer = require('puppeteer');

async function checkAddonInstallation() {
    const browser = await puppeteer.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        
        console.log('Navigating to Home Assistant...');
        await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle2' });
        
        // Login
        await page.waitForSelector('input[name="username"]');
        await page.type('input[name="username"]', 'drewcifer');
        await page.type('input[name="password"]', 'Minds63qq!');
        
        // Click login button - try multiple selectors
        try {
            await page.click('mwc-button[type="submit"]');
        } catch {
            try {
                await page.click('button[type="submit"]');
            } catch {
                await page.click('.mdc-button');
            }
        }
        await page.waitForNavigation({ waitUntil: 'networkidle2' });
        
        await page.screenshot({ path: 'ha_logged_in.png', fullPage: true });
        console.log('Logged in successfully');
        
        // Navigate to Settings > Add-ons
        await page.click('ha-menu-button');
        await page.waitForTimeout(1000);
        await page.click('text=Settings');
        await page.waitForTimeout(1000);
        await page.click('text=Add-ons');
        await page.waitForNavigation({ waitUntil: 'networkidle2' });
        
        await page.screenshot({ path: 'addons_main_page.png', fullPage: true });
        console.log('On add-ons page');
        
        // Check for Add-on Store
        try {
            await page.click('text=Add-on Store');
            await page.waitForTimeout(2000);
            await page.screenshot({ path: 'addon_store_page.png', fullPage: true });
            console.log('Add-on Store accessed');
            
            // Look for repositories button
            const repoButton = await page.$('text=Repositories');
            if (repoButton) {
                await repoButton.click();
                await page.waitForTimeout(2000);
                await page.screenshot({ path: 'repositories_page.png', fullPage: true });
                console.log('Repositories page accessed');
            }
            
        } catch (error) {
            console.log('Add-on Store not found or error accessing:', error.message);
        }
        
        // Go back to main add-ons page and check installed add-ons
        await page.click('text=Add-ons');
        await page.waitForTimeout(2000);
        await page.screenshot({ path: 'installed_addons.png', fullPage: true });
        
        // Check for AICleaner specifically
        const pageContent = await page.content();
        if (pageContent.includes('AICleaner')) {
            console.log('AICleaner found on page');
        } else {
            console.log('AICleaner NOT found on page');
        }
        
        console.log('Addon installation check completed');
        
    } catch (error) {
        console.error('Error during check:', error);
        try {
            await page.screenshot({ path: 'error_addon_check.png', fullPage: true });
        } catch (screenshotError) {
            console.error('Could not take error screenshot:', screenshotError.message);
        }
    } finally {
        await browser.close();
    }
}

checkAddonInstallation();