const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

/**
 * Improved Repository Refresh Solution for AICleaner v3 Addon Installation Paradox
 * 
 * This script focuses on the three-dot menu approach to access repositories
 */

const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';
const REPO_URL = 'https://github.com/sporebattyl/aicleaner_v3';

class ImprovedRepositoryManager {
    constructor() {
        this.browser = null;
        this.page = null;
        this.screenshots = [];
    }

    async initialize() {
        console.log('🚀 Initializing browser...');
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 500
        });
        this.page = await this.browser.newPage();
        await this.page.setViewportSize({ width: 1920, height: 1080 });
        this.page.setDefaultTimeout(30000);
    }

    async takeScreenshot(name, description = '') {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `${name}_${timestamp}.png`;
        const filepath = path.join(__dirname, filename);
        
        await this.page.screenshot({ 
            path: filepath, 
            fullPage: true 
        });
        
        console.log(`📸 Screenshot: ${filename} - ${description}`);
        return filepath;
    }

    async login() {
        console.log('🔐 Logging in...');
        
        await this.page.goto(HA_URL, { waitUntil: 'networkidle' });
        await this.takeScreenshot('login_page', 'Login page loaded');

        // Fill login form
        await this.page.fill('input[name="username"], input[type="text"]', USERNAME);
        await this.page.fill('input[name="password"], input[type="password"]', PASSWORD);
        
        await this.takeScreenshot('credentials_filled', 'Credentials entered');
        
        // Submit login
        await this.page.click('button[type="submit"], mwc-button');
        await this.page.waitForLoadState('networkidle');
        await this.page.waitForTimeout(3000);
        
        await this.takeScreenshot('logged_in', 'Successfully logged in');
        return true;
    }

    async navigateToAddonStore() {
        console.log('🧭 Navigating to Add-on Store...');
        
        await this.page.goto(`${HA_URL}/hassio/store`, { waitUntil: 'networkidle' });
        await this.takeScreenshot('addon_store', 'Add-on Store loaded');
        return true;
    }

    async accessRepositoriesMenu() {
        console.log('📋 Accessing repositories menu...');
        
        // Look for the three-dot menu button in the top-right corner
        const menuSelectors = [
            'ha-icon-button[slot="toolbar-icon"]',
            'mwc-icon-button[slot="toolbar-icon"]', 
            'ha-button-menu mwc-icon-button',
            'mwc-icon-button[aria-label*="menu"]',
            '[aria-label*="menu"]',
            'ha-icon-button[aria-label*="Show menu"]'
        ];

        let menuButton = null;
        for (const selector of menuSelectors) {
            try {
                const elements = await this.page.$$(selector);
                for (const element of elements) {
                    const boundingBox = await element.boundingBox();
                    if (boundingBox && boundingBox.x > 1400) { // Right side of screen
                        menuButton = element;
                        console.log(`✅ Found menu button with selector: ${selector}`);
                        break;
                    }
                }
                if (menuButton) break;
            } catch (e) {
                continue;
            }
        }

        if (!menuButton) {
            // Try to find any clickable element in the top-right area
            console.log('🔍 Searching for clickable elements in top-right area...');
            const allButtons = await this.page.$$('mwc-icon-button, ha-icon-button, paper-icon-button, button');
            
            for (const button of allButtons) {
                const boundingBox = await button.boundingBox();
                if (boundingBox && boundingBox.x > 1400 && boundingBox.y < 100) {
                    menuButton = button;
                    console.log('✅ Found potential menu button in top-right area');
                    break;
                }
            }
        }

        if (menuButton) {
            await this.takeScreenshot('before_menu_click', 'Before clicking menu');
            await menuButton.click();
            await this.page.waitForTimeout(2000);
            await this.takeScreenshot('menu_opened', 'Menu opened');
            
            // Look for "Repositories" option in the menu
            const repositoriesOption = await this.page.$('mwc-list-item:has-text("Repositories"), paper-item:has-text("Repositories"), [role="menuitem"]:has-text("Repositories")');
            
            if (repositoriesOption) {
                await repositoriesOption.click();
                await this.page.waitForTimeout(3000);
                await this.takeScreenshot('repositories_page', 'Repositories page loaded');
                return true;
            } else {
                console.log('❌ Repositories option not found in menu');
                // Try to inspect what options are available
                const menuItems = await this.page.$$('mwc-list-item, paper-item, [role="menuitem"]');
                console.log(`Found ${menuItems.length} menu items`);
                
                for (let i = 0; i < menuItems.length; i++) {
                    const text = await menuItems[i].textContent();
                    console.log(`Menu item ${i}: "${text}"`);
                }
                return false;
            }
        } else {
            console.log('❌ Could not find menu button');
            return false;
        }
    }

    async manageRepositories() {
        console.log('🔧 Managing repositories...');
        
        // Look for existing repository and remove it
        const repoCards = await this.page.$$('ha-card, paper-card, .card');
        let repoFound = false;
        
        for (const card of repoCards) {
            const text = await card.textContent();
            if (text && text.includes('sporebattyl/aicleaner_v3')) {
                console.log('🎯 Found existing repository');
                repoFound = true;
                
                // Look for remove/delete button
                const removeButton = await card.$('mwc-icon-button[title*="Remove"], ha-icon-button[title*="Remove"], [aria-label*="Remove"], [title*="Delete"]');
                if (removeButton) {
                    await this.takeScreenshot('before_remove_repo', 'Before removing repository');
                    await removeButton.click();
                    
                    // Confirm removal if dialog appears
                    await this.page.waitForTimeout(1000);
                    const confirmButtons = await this.page.$$('mwc-button:has-text("Remove"), mwc-button:has-text("Delete"), mwc-button:has-text("Yes"), mwc-button:has-text("OK")');
                    if (confirmButtons.length > 0) {
                        await confirmButtons[0].click();
                    }
                    
                    await this.page.waitForTimeout(3000);
                    await this.takeScreenshot('after_remove_repo', 'After removing repository');
                    console.log('✅ Repository removed');
                }
                break;
            }
        }
        
        if (!repoFound) {
            console.log('⚠️ Repository not found - may already be removed');
        }
        
        // Add repository back
        console.log('➕ Adding repository...');
        
        // Look for add repository input or button
        const addElements = await this.page.$$('input[placeholder*="repository"], ha-textfield[label*="repository"], mwc-textfield[label*="repository"]');
        
        if (addElements.length > 0) {
            await addElements[0].fill(REPO_URL);
            await this.takeScreenshot('repo_url_entered', 'Repository URL entered');
            
            // Look for add/submit button
            const addButton = await this.page.$('mwc-button:has-text("Add"), ha-button:has-text("Add"), button:has-text("Add")');
            if (addButton) {
                await addButton.click();
                console.log('⏳ Adding repository...');
                await this.page.waitForTimeout(10000); // Wait for repository scan
                await this.takeScreenshot('repo_added', 'Repository added');
                return true;
            }
        }
        
        // Alternative: Look for FAB (Floating Action Button) or plus button
        const fabButtons = await this.page.$$('ha-fab, mwc-fab, [aria-label*="Add"], .fab');
        if (fabButtons.length > 0) {
            await fabButtons[0].click();
            await this.page.waitForTimeout(1000);
            
            // Fill dialog input
            const dialogInput = await this.page.$('ha-dialog input, mwc-dialog input, paper-dialog input');
            if (dialogInput) {
                await dialogInput.fill(REPO_URL);
                const submitButton = await this.page.$('mwc-button:has-text("Add"), paper-button:has-text("Add")');
                if (submitButton) {
                    await submitButton.click();
                    console.log('⏳ Adding repository via dialog...');
                    await this.page.waitForTimeout(10000);
                    await this.takeScreenshot('repo_added_via_dialog', 'Repository added via dialog');
                    return true;
                }
            }
        }
        
        console.log('❌ Could not find add repository control');
        return false;
    }

    async verifyAndInstallAddon() {
        console.log('🔍 Verifying addon availability...');
        
        // Navigate back to store
        await this.page.goto(`${HA_URL}/hassio/store`, { waitUntil: 'networkidle' });
        await this.takeScreenshot('store_after_refresh', 'Store after repository refresh');
        
        // Search for AICleaner
        const searchInput = await this.page.$('input[placeholder*="Search"], ha-textfield[label*="Search"]');
        if (searchInput) {
            await searchInput.fill('AICleaner');
            await this.page.waitForTimeout(3000);
            await this.takeScreenshot('search_results', 'Search results for AICleaner');
        }
        
        // Look for AICleaner addon
        const addonCards = await this.page.$$('ha-card, paper-card');
        for (const card of addonCards) {
            const text = await card.textContent();
            if (text && text.toLowerCase().includes('aicleaner')) {
                console.log('🎯 Found AICleaner addon!');
                await this.takeScreenshot('addon_found', 'AICleaner addon found');
                
                // Click on addon
                await card.click();
                await this.page.waitForTimeout(3000);
                await this.takeScreenshot('addon_details', 'Addon details page');
                
                // Try to install
                const installButton = await this.page.$('mwc-button:has-text("Install"), ha-button:has-text("Install")');
                if (installButton) {
                    console.log('🚀 Starting installation...');
                    await installButton.click();
                    await this.page.waitForTimeout(5000);
                    await this.takeScreenshot('installation_started', 'Installation started');
                    
                    // Wait for installation (up to 2 minutes)
                    let installed = false;
                    for (let i = 0; i < 12; i++) {
                        await this.page.waitForTimeout(10000);
                        const startButton = await this.page.$('mwc-button:has-text("Start"), ha-button:has-text("Start")');
                        if (startButton) {
                            console.log('✅ Installation completed!');
                            await this.takeScreenshot('installation_complete', 'Installation completed');
                            installed = true;
                            break;
                        }
                        console.log(`⏳ Installation progress check ${i + 1}/12...`);
                    }
                    
                    return installed;
                } else {
                    console.log('❌ Install button not found');
                    return false;
                }
            }
        }
        
        console.log('❌ AICleaner addon not found');
        return false;
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    async execute() {
        console.log('🎯 Executing Improved Repository Refresh Solution');
        console.log('=' * 50);
        
        try {
            await this.initialize();
            
            const loginSuccess = await this.login();
            if (!loginSuccess) throw new Error('Login failed');
            
            const navSuccess = await this.navigateToAddonStore();
            if (!navSuccess) throw new Error('Navigation failed');
            
            const menuSuccess = await this.accessRepositoriesMenu();
            if (!menuSuccess) throw new Error('Menu access failed');
            
            const repoSuccess = await this.manageRepositories();
            if (!repoSuccess) throw new Error('Repository management failed');
            
            const installSuccess = await this.verifyAndInstallAddon();
            if (installSuccess) {
                console.log('🎉 SUCCESS: AICleaner v3 installation completed!');
            } else {
                console.log('⚠️ Installation verification incomplete');
            }
            
        } catch (error) {
            console.error('💥 Execution failed:', error.message);
            await this.takeScreenshot('final_error', `Error: ${error.message}`);
        } finally {
            await this.cleanup();
        }
    }
}

// Execute
if (require.main === module) {
    const manager = new ImprovedRepositoryManager();
    manager.execute().catch(console.error);
}

module.exports = ImprovedRepositoryManager;