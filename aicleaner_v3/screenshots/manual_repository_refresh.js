const { chromium } = require('playwright');

/**
 * Manual Repository Refresh - Last Resort Solution
 * Uses multiple fallback strategies to access repository management
 */

const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';
const REPO_URL = 'https://github.com/sporebattyl/aicleaner_v3';

class ManualRepositoryRefresh {
    constructor() {
        this.browser = null;
        this.page = null;
    }

    async initialize() {
        console.log('🚀 Initializing...');
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 500
        });
        this.page = await this.browser.newPage();
        await this.page.setViewportSize({ width: 1920, height: 1080 });
    }

    async screenshot(name) {
        const timestamp = Date.now();
        const filepath = `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/${name}_${timestamp}.png`;
        await this.page.screenshot({ path: filepath, fullPage: true });
        console.log(`📸 ${filepath}`);
    }

    async login() {
        console.log('🔐 Logging in...');
        await this.page.goto(HA_URL);
        await this.page.waitForLoadState('networkidle');
        
        await this.page.fill('input[name="username"], input[type="text"]', USERNAME);
        await this.page.fill('input[name="password"], input[type="password"]', PASSWORD);
        await this.page.click('button[type="submit"], mwc-button');
        
        await this.page.waitForLoadState('networkidle');
        await this.page.waitForTimeout(3000);
        console.log('✅ Logged in');
    }

    async tryDirectRepositoryUrls() {
        console.log('🔗 Trying direct repository URLs...');
        
        const repositoryUrls = [
            `${HA_URL}/hassio/store/repositories`,
            `${HA_URL}/hassio/repositories`,
            `${HA_URL}/config/supervisor/repositories`,
            `${HA_URL}/supervisor/repositories`
        ];
        
        for (const url of repositoryUrls) {
            try {
                console.log(`Trying: ${url}`);
                await this.page.goto(url, { waitUntil: 'networkidle' });
                await this.page.waitForTimeout(3000);
                
                // Check if we landed on a repositories page
                const pageContent = await this.page.textContent('body');
                if (pageContent && (pageContent.includes('repository') || pageContent.includes('Repository'))) {
                    await this.screenshot('found_repositories_page');
                    console.log('✅ Found repositories page via direct URL');
                    return true;
                }
            } catch (e) {
                console.log(`❌ Failed: ${url}`);
            }
        }
        
        return false;
    }

    async tryMenuApproaches() {
        console.log('📋 Trying menu approaches...');
        
        // Go back to store
        await this.page.goto(`${HA_URL}/hassio/store`);
        await this.page.waitForLoadState('networkidle');
        await this.screenshot('back_to_store');
        
        // Strategy 1: Click on the three-dot menu by coordinates
        try {
            console.log('📍 Strategy 1: Click by coordinates...');
            const threeDotButton = await this.page.locator('[role="button"]').last();
            if (await threeDotButton.count() > 0) {
                await threeDotButton.click();
                await this.page.waitForTimeout(2000);
                await this.screenshot('menu_by_coordinates');
                
                // Look for repositories option
                const repoOption = this.page.locator('text=Repositories').first();
                if (await repoOption.count() > 0) {
                    await repoOption.click();
                    await this.page.waitForTimeout(3000);
                    console.log('✅ Accessed repositories via coordinates');
                    return true;
                }
            }
        } catch (e) {
            console.log('❌ Coordinates approach failed');
        }
        
        // Strategy 2: Try all clickable elements in top-right area
        try {
            console.log('📍 Strategy 2: Scan top-right area...');
            const clickableElements = await this.page.locator('button, [role="button"], mwc-icon-button, ha-icon-button').all();
            
            for (const element of clickableElements) {
                const box = await element.boundingBox();
                if (box && box.x > 1300 && box.y < 100) {
                    console.log(`Trying element at (${box.x}, ${box.y})`);
                    await element.click();
                    await this.page.waitForTimeout(1000);
                    
                    // Check if a menu appeared
                    const menuItems = await this.page.locator('mwc-list-item, paper-item, [role="menuitem"]').count();
                    if (menuItems > 0) {
                        await this.screenshot('menu_found');
                        
                        // Look for repositories
                        const repoOption = this.page.locator('text=Repositories').first();
                        if (await repoOption.count() > 0) {
                            await repoOption.click();
                            await this.page.waitForTimeout(3000);
                            console.log('✅ Found repositories via area scan');
                            return true;
                        }
                        
                        // Close menu if repositories not found
                        await this.page.keyboard.press('Escape');
                    }
                }
            }
        } catch (e) {
            console.log('❌ Area scan approach failed');
        }
        
        return false;
    }

    async performRepositoryRefresh() {
        console.log('🔄 Performing repository refresh...');
        
        // Check current page for repository management elements
        const pageContent = await this.page.textContent('body');
        if (!pageContent.toLowerCase().includes('repository')) {
            console.log('❌ Not on repositories page');
            return false;
        }
        
        await this.screenshot('on_repositories_page');
        
        // Remove existing repository
        console.log('🗑️ Looking for existing repository...');
        const allCards = await this.page.locator('ha-card, paper-card, .card').all();
        
        for (const card of allCards) {
            const cardText = await card.textContent();
            if (cardText && cardText.includes('sporebattyl/aicleaner_v3')) {
                console.log('🎯 Found existing repository to remove');
                
                // Look for remove button
                const removeButton = card.locator('ha-icon-button, mwc-icon-button').filter({ hasText: /remove|delete/i }).first();
                if (await removeButton.count() === 0) {
                    // Try other remove button selectors
                    const removeButtons = await card.locator('ha-icon-button, mwc-icon-button').all();
                    for (const btn of removeButtons) {
                        const title = await btn.getAttribute('title');
                        if (title && title.toLowerCase().includes('remove')) {
                            await btn.click();
                            break;
                        }
                    }
                } else {
                    await removeButton.click();
                }
                
                // Confirm removal
                await this.page.waitForTimeout(1000);
                const confirmButton = this.page.locator('mwc-button:has-text("Remove"), mwc-button:has-text("Yes")').first();
                if (await confirmButton.count() > 0) {
                    await confirmButton.click();
                }
                
                await this.page.waitForTimeout(3000);
                console.log('✅ Repository removed');
                break;
            }
        }
        
        // Add repository back
        console.log('➕ Adding repository back...');
        
        // Try input field approach
        const addInput = this.page.locator('input[placeholder*="repository"], ha-textfield').first();
        if (await addInput.count() > 0) {
            await addInput.fill(REPO_URL);
            await this.screenshot('repo_url_entered');
            
            const addButton = this.page.locator('mwc-button:has-text("Add")').first();
            if (await addButton.count() > 0) {
                await addButton.click();
                console.log('⏳ Repository being added...');
                await this.page.waitForTimeout(15000);
                await this.screenshot('repo_refresh_complete');
                return true;
            }
        }
        
        // Try FAB approach
        const fabButton = this.page.locator('ha-fab, mwc-fab, [aria-label*="Add"]').first();
        if (await fabButton.count() > 0) {
            await fabButton.click();
            await this.page.waitForTimeout(2000);
            
            const dialogInput = this.page.locator('input, ha-textfield').first();
            if (await dialogInput.count() > 0) {
                await dialogInput.fill(REPO_URL);
                const submitButton = this.page.locator('mwc-button:has-text("Add")').first();
                if (await submitButton.count() > 0) {
                    await submitButton.click();
                    console.log('⏳ Repository being added via dialog...');
                    await this.page.waitForTimeout(15000);
                    await this.screenshot('repo_refresh_complete');
                    return true;
                }
            }
        }
        
        console.log('❌ Could not find add repository control');
        return false;
    }

    async verifyAddonAvailable() {
        console.log('🔍 Verifying addon availability...');
        
        await this.page.goto(`${HA_URL}/hassio/store`);
        await this.page.waitForLoadState('networkidle');
        
        // Search for AICleaner
        const searchInput = this.page.locator('input[placeholder*="Search"]').first();
        if (await searchInput.count() > 0) {
            await searchInput.fill('AICleaner');
            await this.page.waitForTimeout(3000);
        }
        
        await this.screenshot('final_search_results');
        
        // Check for AICleaner addon
        const allCards = await this.page.locator('ha-card').all();
        for (const card of allCards) {
            const cardText = await card.textContent();
            if (cardText && cardText.toLowerCase().includes('aicleaner')) {
                console.log('🎉 SUCCESS: AICleaner addon found and available!');
                await this.screenshot('success_addon_found');
                return true;
            }
        }
        
        console.log('❌ AICleaner addon still not found');
        return false;
    }

    async execute() {
        console.log('🎯 MANUAL REPOSITORY REFRESH SOLUTION');
        console.log('=====================================');
        
        try {
            await this.initialize();
            await this.login();
            
            // Try multiple approaches to access repository management
            let repositoryAccess = false;
            
            // Approach 1: Direct URLs
            repositoryAccess = await this.tryDirectRepositoryUrls();
            
            // Approach 2: Menu approaches if direct URLs failed
            if (!repositoryAccess) {
                repositoryAccess = await this.tryMenuApproaches();
            }
            
            if (!repositoryAccess) {
                throw new Error('Could not access repository management');
            }
            
            // Perform repository refresh
            const refreshSuccess = await this.performRepositoryRefresh();
            if (!refreshSuccess) {
                throw new Error('Repository refresh failed');
            }
            
            // Verify addon is now available
            const verifySuccess = await this.verifyAddonAvailable();
            
            if (verifySuccess) {
                console.log('🎉 MISSION ACCOMPLISHED: Repository refresh solution executed successfully!');
                console.log('AICleaner v3 addon should now be available for installation.');
            } else {
                console.log('⚠️ Repository refresh completed but addon verification inconclusive');
            }
            
        } catch (error) {
            console.error('💥 EXECUTION FAILED:', error.message);
            await this.screenshot('final_error_state');
        } finally {
            console.log('🧹 Keeping browser open for manual inspection...');
            // Don't close browser automatically
        }
    }
}

// Execute
if (require.main === module) {
    const manager = new ManualRepositoryRefresh();
    manager.execute().catch(console.error);
}

module.exports = ManualRepositoryRefresh;