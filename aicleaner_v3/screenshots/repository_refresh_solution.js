const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

/**
 * Repository Refresh Solution for AICleaner v3 Addon Installation Paradox
 * 
 * This script executes the solution to resolve the AICleaner v3 addon installation
 * issue by removing and re-adding the repository to force Home Assistant Supervisor
 * to refresh its cache and properly discover the addon.
 */

const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';
const REPO_URL = 'https://github.com/sporebattyl/aicleaner_v3';

class HomeAssistantRepositoryManager {
    constructor() {
        this.browser = null;
        this.page = null;
        this.screenshots = [];
    }

    async initialize() {
        console.log('🚀 Initializing Playwright browser...');
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 1000 // Slow down for visibility
        });
        this.page = await this.browser.newPage();
        
        // Set viewport and timeout
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
        
        this.screenshots.push({
            filename,
            description,
            timestamp: new Date().toISOString()
        });
        
        console.log(`📸 Screenshot saved: ${filename} - ${description}`);
        return filepath;
    }

    async login() {
        console.log('🔐 Logging into Home Assistant...');
        
        try {
            await this.page.goto(HA_URL, { waitUntil: 'networkidle' });
            await this.takeScreenshot('01_login_page', 'Home Assistant login page');

            // Wait for login form
            await this.page.waitForSelector('input[name="username"], input[type="text"]');
            
            // Fill credentials
            const usernameInput = await this.page.$('input[name="username"]') || 
                                await this.page.$('input[type="text"]');
            if (usernameInput) {
                await usernameInput.fill(USERNAME);
            }

            const passwordInput = await this.page.$('input[name="password"]') || 
                                await this.page.$('input[type="password"]');
            if (passwordInput) {
                await passwordInput.fill(PASSWORD);
            }

            await this.takeScreenshot('02_credentials_entered', 'Credentials entered');

            // Submit login
            const loginButton = await this.page.$('button[type="submit"], mwc-button') ||
                              await this.page.$('paper-button');
            if (loginButton) {
                await loginButton.click();
            }

            // Wait for dashboard
            await this.page.waitForLoadState('networkidle');
            await this.page.waitForTimeout(3000);
            
            await this.takeScreenshot('03_logged_in_dashboard', 'Successfully logged in to Home Assistant');
            console.log('✅ Successfully logged into Home Assistant');
            
            return true;
        } catch (error) {
            console.error('❌ Login failed:', error.message);
            await this.takeScreenshot('error_login', 'Login failure');
            return false;
        }
    }

    async navigateToRepositories() {
        console.log('🧭 Navigating to repository management...');
        
        try {
            // Navigate to Settings
            console.log('📍 Step 1: Going to Settings');
            await this.page.goto(`${HA_URL}/config`, { waitUntil: 'networkidle' });
            await this.takeScreenshot('04_settings_page', 'Settings page');

            // Navigate to Add-ons
            console.log('📍 Step 2: Going to Add-ons');
            await this.page.goto(`${HA_URL}/hassio`, { waitUntil: 'networkidle' });
            await this.takeScreenshot('05_supervisor_dashboard', 'Supervisor dashboard');

            // Navigate to Add-on Store
            console.log('📍 Step 3: Going to Add-on Store');
            await this.page.goto(`${HA_URL}/hassio/store`, { waitUntil: 'networkidle' });
            await this.takeScreenshot('06_addon_store', 'Add-on Store page');

            // Look for the three-dots menu or repositories link
            console.log('📍 Step 4: Looking for repositories access...');
            
            // Try multiple selectors for the repositories menu
            const repositorySelectors = [
                'mwc-icon-button[aria-label*="menu"]',
                'ha-icon-button[aria-label*="menu"]', 
                'paper-icon-button[aria-label*="menu"]',
                '[aria-label*="Repositories"]',
                'a[href*="repositories"]',
                'mwc-button:has-text("Repositories")',
                'paper-button:has-text("Repositories")'
            ];

            let repositoryButton = null;
            for (const selector of repositorySelectors) {
                try {
                    repositoryButton = await this.page.$(selector);
                    if (repositoryButton) {
                        console.log(`✅ Found repository access with selector: ${selector}`);
                        break;
                    }
                } catch (e) {
                    // Continue searching
                }
            }

            if (repositoryButton) {
                await repositoryButton.click();
                await this.page.waitForTimeout(2000);
            } else {
                // Try direct navigation to repositories
                console.log('📍 Trying direct navigation to repositories...');
                await this.page.goto(`${HA_URL}/hassio/store/repositories`, { waitUntil: 'networkidle' });
            }

            await this.takeScreenshot('07_repositories_page', 'Repositories management page');
            console.log('✅ Successfully navigated to repositories');
            return true;

        } catch (error) {
            console.error('❌ Navigation failed:', error.message);
            await this.takeScreenshot('error_navigation', 'Navigation failure');
            return false;
        }
    }

    async removeExistingRepository() {
        console.log('🗑️ Removing existing repository...');
        
        try {
            // Look for the repository in the list
            const repoElements = await this.page.$$('ha-card, paper-card, mwc-card');
            
            for (const element of repoElements) {
                const textContent = await element.textContent();
                if (textContent && textContent.includes('sporebattyl/aicleaner_v3')) {
                    console.log('🎯 Found existing repository');
                    
                    // Look for remove button within this card
                    const removeButton = await element.$('mwc-icon-button[aria-label*="remove"], paper-icon-button[aria-label*="remove"], ha-icon-button[aria-label*="remove"]') ||
                                       await element.$('mwc-button:has-text("Remove"), paper-button:has-text("Remove")');
                    
                    if (removeButton) {
                        await this.takeScreenshot('08_before_remove', 'Before removing repository');
                        await removeButton.click();
                        
                        // Confirm removal if dialog appears
                        await this.page.waitForTimeout(1000);
                        const confirmButton = await this.page.$('mwc-button:has-text("Remove"), paper-button:has-text("Remove"), mwc-button:has-text("Yes"), paper-button:has-text("Yes")');
                        if (confirmButton) {
                            await confirmButton.click();
                        }
                        
                        await this.page.waitForTimeout(3000);
                        await this.takeScreenshot('09_after_remove', 'After removing repository');
                        console.log('✅ Repository removed successfully');
                        return true;
                    }
                }
            }
            
            console.log('⚠️ Repository not found in current list - may already be removed');
            return true;
            
        } catch (error) {
            console.error('❌ Repository removal failed:', error.message);
            await this.takeScreenshot('error_remove', 'Repository removal failure');
            return false;
        }
    }

    async addRepository() {
        console.log('➕ Adding repository to force cache refresh...');
        
        try {
            // Look for "Add Repository" button or input field
            const addSelectors = [
                'mwc-button:has-text("Add repository")',
                'paper-button:has-text("Add repository")', 
                'mwc-fab[aria-label*="Add"]',
                'ha-fab[aria-label*="Add"]',
                'input[placeholder*="repository"]',
                'ha-textfield[label*="repository"]'
            ];

            await this.takeScreenshot('10_before_add', 'Before adding repository');

            let addElement = null;
            for (const selector of addSelectors) {
                try {
                    addElement = await this.page.$(selector);
                    if (addElement) {
                        console.log(`✅ Found add element with selector: ${selector}`);
                        break;
                    }
                } catch (e) {
                    // Continue searching
                }
            }

            if (addElement) {
                const tagName = await addElement.evaluate(el => el.tagName.toLowerCase());
                
                if (tagName === 'input' || tagName === 'ha-textfield') {
                    // Direct input field
                    await addElement.fill(REPO_URL);
                    
                    // Look for submit button
                    const submitButton = await this.page.$('mwc-button:has-text("Add"), paper-button:has-text("Add")');
                    if (submitButton) {
                        await submitButton.click();
                    }
                } else {
                    // Button that opens a dialog
                    await addElement.click();
                    await this.page.waitForTimeout(1000);
                    
                    // Fill the dialog input
                    const dialogInput = await this.page.$('ha-dialog input, mwc-dialog input, paper-dialog input');
                    if (dialogInput) {
                        await dialogInput.fill(REPO_URL);
                        
                        const addButton = await this.page.$('mwc-button:has-text("Add"), paper-button:has-text("Add")');
                        if (addButton) {
                            await addButton.click();
                        }
                    }
                }
                
                // Wait for repository scan
                console.log('⏳ Waiting for repository scan...');
                await this.page.waitForTimeout(10000);
                
                await this.takeScreenshot('11_after_add', 'After adding repository');
                console.log('✅ Repository added successfully');
                return true;
            } else {
                console.log('❌ Could not find add repository control');
                return false;
            }
            
        } catch (error) {
            console.error('❌ Repository addition failed:', error.message);
            await this.takeScreenshot('error_add', 'Repository addition failure');
            return false;
        }
    }

    async verifyAddonAvailability() {
        console.log('🔍 Verifying AICleaner V3 addon availability...');
        
        try {
            // Navigate back to Add-on Store
            await this.page.goto(`${HA_URL}/hassio/store`, { waitUntil: 'networkidle' });
            await this.takeScreenshot('12_store_after_refresh', 'Add-on Store after repository refresh');

            // Search for AICleaner V3
            const searchSelectors = [
                'input[placeholder*="Search"]',
                'ha-textfield[label*="Search"]',
                'paper-input[placeholder*="Search"]'
            ];

            for (const selector of searchSelectors) {
                const searchInput = await this.page.$(selector);
                if (searchInput) {
                    await searchInput.fill('AICleaner');
                    await this.page.waitForTimeout(2000);
                    break;
                }
            }

            await this.takeScreenshot('13_search_results', 'Search results for AICleaner');

            // Look for AICleaner V3 addon
            const addonCards = await this.page.$$('ha-card, paper-card, mwc-card');
            let addonFound = false;

            for (const card of addonCards) {
                const textContent = await card.textContent();
                if (textContent && (textContent.toLowerCase().includes('aicleaner') || textContent.toLowerCase().includes('ai cleaner'))) {
                    console.log('🎯 Found AICleaner V3 addon!');
                    addonFound = true;
                    
                    await this.takeScreenshot('14_addon_found', 'AICleaner V3 addon found in store');
                    
                    // Click on the addon to go to details
                    await card.click();
                    await this.page.waitForTimeout(3000);
                    
                    await this.takeScreenshot('15_addon_details', 'AICleaner V3 addon details page');
                    break;
                }
            }

            if (!addonFound) {
                console.log('❌ AICleaner V3 addon not found in store');
                await this.takeScreenshot('error_addon_not_found', 'Addon not found after repository refresh');
                return false;
            }

            return true;
            
        } catch (error) {
            console.error('❌ Addon verification failed:', error.message);
            await this.takeScreenshot('error_verify', 'Addon verification failure');
            return false;
        }
    }

    async attemptInstallation() {
        console.log('🚀 Attempting AICleaner V3 installation...');
        
        try {
            // Look for install button
            const installButton = await this.page.$('mwc-button:has-text("Install"), paper-button:has-text("Install"), ha-button:has-text("Install")');
            
            if (!installButton) {
                console.log('❌ Install button not found');
                await this.takeScreenshot('error_no_install_button', 'No install button available');
                return false;
            }

            await this.takeScreenshot('16_before_install', 'Before clicking install');
            
            await installButton.click();
            console.log('⏳ Installation started...');
            
            // Wait for installation to complete (may take several minutes)
            await this.page.waitForTimeout(5000);
            await this.takeScreenshot('17_installation_started', 'Installation in progress');
            
            // Monitor installation progress
            let installationComplete = false;
            let attempts = 0;
            const maxAttempts = 30; // 5 minutes max
            
            while (!installationComplete && attempts < maxAttempts) {
                await this.page.waitForTimeout(10000);
                attempts++;
                
                // Check for completion indicators
                const startButton = await this.page.$('mwc-button:has-text("Start"), paper-button:has-text("Start")');
                const errorElement = await this.page.$('[class*="error"], .error, ha-alert[alert-type="error"]');
                
                if (startButton) {
                    console.log('✅ Installation completed successfully!');
                    installationComplete = true;
                    await this.takeScreenshot('18_installation_success', 'Installation completed - Start button available');
                } else if (errorElement) {
                    console.log('❌ Installation failed with error');
                    await this.takeScreenshot('error_installation_failed', 'Installation failed with error');
                    return false;
                }
                
                console.log(`⏳ Installation attempt ${attempts}/${maxAttempts}...`);
            }
            
            if (!installationComplete) {
                console.log('⚠️ Installation timeout - taking final screenshot');
                await this.takeScreenshot('installation_timeout', 'Installation timed out');
                return false;
            }
            
            return true;
            
        } catch (error) {
            console.error('❌ Installation attempt failed:', error.message);
            await this.takeScreenshot('error_install', 'Installation attempt failure');
            return false;
        }
    }

    async testAddonStartup() {
        console.log('🧪 Testing addon startup and configuration...');
        
        try {
            // Click Start button if available
            const startButton = await this.page.$('mwc-button:has-text("Start"), paper-button:has-text("Start")');
            if (startButton) {
                await startButton.click();
                await this.page.waitForTimeout(5000);
                await this.takeScreenshot('19_addon_starting', 'Addon startup initiated');
            }
            
            // Navigate to configuration
            const configTab = await this.page.$('mwc-tab:has-text("Configuration"), paper-tab:has-text("Configuration")') ||
                            await this.page.$('[aria-label*="Configuration"]');
            
            if (configTab) {
                await configTab.click();
                await this.page.waitForTimeout(3000);
                await this.takeScreenshot('20_addon_config', 'Addon configuration page');
                
                // Test entity selector dropdowns
                const dropdowns = await this.page.$$('ha-entity-picker, ha-selector');
                if (dropdowns.length > 0) {
                    console.log(`✅ Found ${dropdowns.length} entity selector(s)`);
                    
                    // Test first dropdown
                    await dropdowns[0].click();
                    await this.page.waitForTimeout(2000);
                    await this.takeScreenshot('21_dropdown_test', 'Testing entity selector dropdown');
                } else {
                    console.log('⚠️ No entity selectors found');
                }
            }
            
            await this.takeScreenshot('22_final_state', 'Final addon state after testing');
            return true;
            
        } catch (error) {
            console.error('❌ Addon testing failed:', error.message);
            await this.takeScreenshot('error_test', 'Addon testing failure');
            return false;
        }
    }

    async generateReport() {
        console.log('📊 Generating execution report...');
        
        const report = {
            executionTime: new Date().toISOString(),
            screenshots: this.screenshots,
            summary: {
                totalSteps: 8,
                completedSteps: 0,
                success: false,
                errors: []
            }
        };
        
        // Save report
        const reportPath = path.join(__dirname, `repository_refresh_report_${Date.now()}.json`);
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        
        console.log(`📋 Report saved to: ${reportPath}`);
        return report;
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
        }
    }

    async execute() {
        console.log('🎯 Executing Repository Refresh Solution for AICleaner v3');
        console.log('=' * 60);
        
        try {
            await this.initialize();
            
            // Step 1: Login
            const loginSuccess = await this.login();
            if (!loginSuccess) {
                throw new Error('Login failed');
            }
            
            // Step 2: Navigate to repositories
            const navSuccess = await this.navigateToRepositories();
            if (!navSuccess) {
                throw new Error('Navigation to repositories failed');
            }
            
            // Step 3: Remove existing repository
            const removeSuccess = await this.removeExistingRepository();
            if (!removeSuccess) {
                console.log('⚠️ Repository removal failed, continuing with add...');
            }
            
            // Step 4: Re-add repository
            const addSuccess = await this.addRepository();
            if (!addSuccess) {
                throw new Error('Repository addition failed');
            }
            
            // Step 5: Verify addon availability
            const verifySuccess = await this.verifyAddonAvailability();
            if (!verifySuccess) {
                throw new Error('Addon verification failed');
            }
            
            // Step 6: Attempt installation
            const installSuccess = await this.attemptInstallation();
            if (!installSuccess) {
                throw new Error('Installation failed');
            }
            
            // Step 7: Test addon startup
            const testSuccess = await this.testAddonStartup();
            if (!testSuccess) {
                console.log('⚠️ Addon testing had issues, but installation succeeded');
            }
            
            console.log('🎉 Repository refresh solution executed successfully!');
            
        } catch (error) {
            console.error('💥 Execution failed:', error.message);
            await this.takeScreenshot('final_error', `Final error state: ${error.message}`);
        } finally {
            await this.generateReport();
            await this.cleanup();
        }
    }
}

// Execute the solution
if (require.main === module) {
    const manager = new HomeAssistantRepositoryManager();
    manager.execute().catch(console.error);
}

module.exports = HomeAssistantRepositoryManager;