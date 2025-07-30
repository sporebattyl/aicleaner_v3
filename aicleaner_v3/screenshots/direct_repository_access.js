const { chromium } = require('playwright');

/**
 * Direct Repository Access Solution
 * Simplified approach to access repositories via the three-dot menu
 */

const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';
const REPO_URL = 'https://github.com/sporebattyl/aicleaner_v3';

class DirectRepositoryAccess {
    constructor() {
        this.browser = null;
        this.page = null;
    }

    async initialize() {
        console.log('🚀 Starting browser...');
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 1000
        });
        this.page = await this.browser.newPage();
        await this.page.setViewportSize({ width: 1920, height: 1080 });
        this.page.setDefaultTimeout(30000);
    }

    async screenshot(name) {
        const timestamp = Date.now();
        const filepath = `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/${name}_${timestamp}.png`;
        await this.page.screenshot({ path: filepath, fullPage: true });
        console.log(`📸 ${name}: ${filepath}`);
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
        await this.screenshot('01_logged_in');
        console.log('✅ Logged in successfully');
    }

    async navigateToStore() {
        console.log('🏪 Going to Add-on Store...');
        await this.page.goto(`${HA_URL}/hassio/store`);
        await this.page.waitForLoadState('networkidle');
        await this.screenshot('02_addon_store');
        console.log('✅ Add-on Store loaded');
    }

    async clickThreeDotMenu() {
        console.log('📋 Clicking three-dot menu...');
        
        // Target the specific three-dot menu button
        const menuButton = await this.page.locator('ha-icon-button[slot="toolbar-icon"]').last();
        
        if (await menuButton.count() > 0) {
            await this.screenshot('03_before_menu_click');
            await menuButton.click();
            await this.page.waitForTimeout(2000);
            await this.screenshot('04_menu_opened');
            console.log('✅ Three-dot menu clicked');
            return true;
        } else {
            console.log('❌ Three-dot menu not found');
            return false;
        }
    }

    async selectRepositories() {
        console.log('📂 Selecting Repositories...');
        
        // Look for Repositories option in the dropdown menu
        const repositoriesOption = this.page.locator('text=Repositories').first();
        
        if (await repositoriesOption.count() > 0) {
            await repositoriesOption.click();
            await this.page.waitForTimeout(3000);
            await this.screenshot('05_repositories_page');
            console.log('✅ Repositories page loaded');
            return true;
        } else {
            console.log('❌ Repositories option not found');
            // List all available menu options
            const menuOptions = await this.page.locator('mwc-list-item, paper-item').allTextContents();
            console.log('Available menu options:', menuOptions);
            return false;
        }
    }

    async removeRepository() {
        console.log('🗑️ Looking for existing repository to remove...');
        
        // Look for repository cards containing our repo URL
        const repoCards = await this.page.locator('ha-card, paper-card').all();
        
        for (const card of repoCards) {
            const cardText = await card.textContent();
            if (cardText && cardText.includes('sporebattyl/aicleaner_v3')) {
                console.log('🎯 Found existing repository');
                await this.screenshot('06_found_existing_repo');
                
                // Look for remove button within this card
                const removeButton = card.locator('ha-icon-button[title*="Remove"], mwc-icon-button[title*="Remove"]').first();
                
                if (await removeButton.count() > 0) {
                    await removeButton.click();
                    await this.page.waitForTimeout(1000);
                    
                    // Confirm removal if dialog appears
                    const confirmButton = this.page.locator('mwc-button:has-text("Remove"), mwc-button:has-text("Yes")').first();
                    if (await confirmButton.count() > 0) {
                        await confirmButton.click();
                    }
                    
                    await this.page.waitForTimeout(3000);
                    await this.screenshot('07_repository_removed');
                    console.log('✅ Repository removed');
                    return true;
                }
            }
        }
        
        console.log('⚠️ No existing repository found to remove');
        return true; // Not an error if repo doesn't exist
    }

    async addRepository() {
        console.log('➕ Adding repository...');
        
        // Look for add repository input field
        const addInput = this.page.locator('input[placeholder*="repository"], ha-textfield[label*="repository"]').first();
        
        if (await addInput.count() > 0) {
            await addInput.fill(REPO_URL);
            await this.screenshot('08_repo_url_entered');
            
            // Look for add button
            const addButton = this.page.locator('mwc-button:has-text("Add"), ha-button:has-text("Add")').first();
            if (await addButton.count() > 0) {
                await addButton.click();
                console.log('⏳ Adding repository and waiting for scan...');
                await this.page.waitForTimeout(15000); // Wait for repo scan
                await this.screenshot('09_repository_added');
                console.log('✅ Repository added');
                return true;
            }
        }
        
        // Alternative: Look for FAB button
        const fabButton = this.page.locator('ha-fab, mwc-fab').first();
        if (await fabButton.count() > 0) {
            await fabButton.click();
            await this.page.waitForTimeout(2000);
            
            // Fill dialog
            const dialogInput = this.page.locator('ha-textfield input, mwc-textfield input').first();
            if (await dialogInput.count() > 0) {
                await dialogInput.fill(REPO_URL);
                const submitButton = this.page.locator('mwc-button:has-text("Add")').first();
                if (await submitButton.count() > 0) {
                    await submitButton.click();
                    await this.page.waitForTimeout(15000);
                    await this.screenshot('09_repository_added_via_dialog');
                    console.log('✅ Repository added via dialog');
                    return true;
                }
            }
        }
        
        console.log('❌ Could not find add repository control');
        return false;
    }

    async verifyAddon() {
        console.log('🔍 Verifying addon is now available...');
        
        // Go back to store
        await this.page.goto(`${HA_URL}/hassio/store`);
        await this.page.waitForLoadState('networkidle');
        await this.screenshot('10_store_after_refresh');
        
        // Search for AICleaner
        const searchInput = this.page.locator('input[placeholder*="Search"]').first();
        if (await searchInput.count() > 0) {
            await searchInput.fill('AICleaner');
            await this.page.waitForTimeout(3000);
            await this.screenshot('11_search_results');
        }
        
        // Look for AICleaner addon
        const addonCards = await this.page.locator('ha-card').all();
        for (const card of addonCards) {
            const cardText = await card.textContent();
            if (cardText && cardText.toLowerCase().includes('aicleaner')) {
                console.log('🎯 AICleaner addon found!');
                await this.screenshot('12_addon_found');
                
                // Click to open addon details
                await card.click();
                await this.page.waitForTimeout(3000);
                await this.screenshot('13_addon_details');
                
                // Check for install button
                const installButton = this.page.locator('mwc-button:has-text("Install")').first();
                if (await installButton.count() > 0) {
                    console.log('✅ Install button available - addon ready for installation');
                    return true;
                } else {
                    console.log('⚠️ No install button found');
                    return false;
                }
            }
        }
        
        console.log('❌ AICleaner addon not found after repository refresh');
        return false;
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    async execute() {
        console.log('🎯 DIRECT REPOSITORY ACCESS SOLUTION');
        console.log('========================================');
        
        try {
            await this.initialize();
            
            // Step 1: Login
            await this.login();
            
            // Step 2: Navigate to store
            await this.navigateToStore();
            
            // Step 3: Click three-dot menu
            const menuSuccess = await this.clickThreeDotMenu();
            if (!menuSuccess) {
                throw new Error('Failed to access three-dot menu');
            }
            
            // Step 4: Select repositories
            const repoPageSuccess = await this.selectRepositories();
            if (!repoPageSuccess) {
                throw new Error('Failed to access repositories page');
            }
            
            // Step 5: Remove existing repository
            await this.removeRepository();
            
            // Step 6: Add repository back
            const addSuccess = await this.addRepository();
            if (!addSuccess) {
                throw new Error('Failed to add repository');
            }
            
            // Step 7: Verify addon is now available
            const verifySuccess = await this.verifyAddon();
            if (verifySuccess) {
                console.log('🎉 SUCCESS: Repository refresh completed - AICleaner v3 is now available for installation!');
            } else {
                console.log('⚠️ Repository refresh completed but addon verification failed');
            }
            
        } catch (error) {
            console.error('💥 EXECUTION FAILED:', error.message);
            await this.screenshot('error_final');
        } finally {
            console.log('🧹 Cleaning up...');
            // Keep browser open for manual inspection
            // await this.cleanup();
        }
    }
}

// Execute the solution
if (require.main === module) {
    const manager = new DirectRepositoryAccess();
    manager.execute().catch(console.error);
}

module.exports = DirectRepositoryAccess;