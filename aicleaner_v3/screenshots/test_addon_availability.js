const { chromium } = require('playwright');

/**
 * Test Addon Availability - Check if AICleaner v3 is now available
 * This script focuses on verifying if the addon is accessible for installation
 */

const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';

class AddonAvailabilityTest {
    constructor() {
        this.browser = null;
        this.page = null;
    }

    async initialize() {
        console.log('🚀 Starting availability test...');
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 1000
        });
        this.page = await this.browser.newPage();
        await this.page.setViewportSize({ width: 1920, height: 1080 });
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
        console.log('✅ Logged in successfully');
        await this.screenshot('logged_in');
    }

    async searchForAICleaner() {
        console.log('🔍 Searching for AICleaner addon...');
        
        // Navigate to Add-on Store
        await this.page.goto(`${HA_URL}/hassio/store`);
        await this.page.waitForLoadState('networkidle');
        await this.screenshot('addon_store_loaded');
        
        // Try to search for AICleaner
        const searchInput = this.page.locator('input[placeholder*="Search"], input[type="search"]').first();
        if (await searchInput.count() > 0) {
            console.log('🔎 Using search functionality...');
            await searchInput.fill('AICleaner');
            await this.page.waitForTimeout(3000);
            await this.screenshot('search_results');
        }
        
        // Scan all addon cards for AICleaner
        console.log('📋 Scanning all addon cards...');
        const allCards = await this.page.locator('ha-card').all();
        console.log(`Found ${allCards.length} addon cards to examine`);
        
        let aicleanerFound = false;
        let aicleanerCard = null;
        
        for (let i = 0; i < allCards.length; i++) {
            const card = allCards[i];
            const cardText = await card.textContent();
            
            if (cardText) {
                const lowerText = cardText.toLowerCase();
                if (lowerText.includes('aicleaner') || lowerText.includes('ai cleaner')) {
                    console.log(`🎯 Found AICleaner addon at card ${i}!`);
                    console.log(`Card text: ${cardText.substring(0, 200)}...`);
                    aicleanerFound = true;
                    aicleanerCard = card;
                    await this.screenshot(`aicleaner_found_card_${i}`);
                    break;
                }
            }
        }
        
        return { found: aicleanerFound, card: aicleanerCard };
    }

    async testInstallation(card) {
        console.log('🚀 Testing addon installation...');
        
        // Click on the addon card to open details
        await card.click();
        await this.page.waitForTimeout(3000);
        await this.screenshot('addon_details_page');
        
        // Look for install button
        const installButton = this.page.locator('mwc-button:has-text("Install"), ha-button:has-text("Install")').first();
        
        if (await installButton.count() > 0) {
            console.log('✅ Install button found - addon is ready for installation!');
            await this.screenshot('install_button_available');
            
            // Optionally attempt actual installation
            console.log('🤖 Attempting installation...');
            await installButton.click();
            
            // Monitor installation progress
            let installationAttempts = 0;
            const maxAttempts = 30; // 5 minutes max
            
            while (installationAttempts < maxAttempts) {
                await this.page.waitForTimeout(10000); // Wait 10 seconds
                installationAttempts++;
                
                // Check for success indicators
                const startButton = this.page.locator('mwc-button:has-text("Start"), ha-button:has-text("Start")').first();
                const errorAlert = this.page.locator('[class*="error"], .error, ha-alert[alert-type="error"]').first();
                
                if (await startButton.count() > 0) {
                    console.log('🎉 INSTALLATION SUCCESSFUL!');
                    await this.screenshot('installation_success');
                    return { success: true, error: null };
                } else if (await errorAlert.count() > 0) {
                    const errorText = await errorAlert.textContent();
                    console.log('❌ Installation failed with error:', errorText);
                    await this.screenshot('installation_error');
                    return { success: false, error: errorText };
                }
                
                console.log(`⏳ Installation progress: ${installationAttempts}/${maxAttempts}...`);
                
                if (installationAttempts % 6 === 0) { // Every minute
                    await this.screenshot(`installation_progress_${installationAttempts}`);
                }
            }
            
            console.log('⚠️ Installation timeout - taking final screenshot');
            await this.screenshot('installation_timeout');
            return { success: false, error: 'Installation timeout' };
            
        } else {
            console.log('❌ Install button not found');
            await this.screenshot('no_install_button');
            
            // Check for other buttons that might indicate the state
            const allButtons = await this.page.locator('mwc-button, ha-button').all();
            console.log('Available buttons:');
            for (const button of allButtons) {
                const buttonText = await button.textContent();
                console.log(`- "${buttonText}"`);
            }
            
            return { success: false, error: 'Install button not available' };
        }
    }

    async checkIfAlreadyInstalled() {
        console.log('🔍 Checking if addon is already installed...');
        
        // Navigate to installed addons
        await this.page.goto(`${HA_URL}/hassio/addon`);
        await this.page.waitForLoadState('networkidle');
        await this.screenshot('installed_addons_page');
        
        const installedCards = await this.page.locator('ha-card').all();
        
        for (const card of installedCards) {
            const cardText = await card.textContent();
            if (cardText && cardText.toLowerCase().includes('aicleaner')) {
                console.log('✅ AICleaner is already installed!');
                await this.screenshot('aicleaner_already_installed');
                
                // Click on it to access configuration
                await card.click();
                await this.page.waitForTimeout(3000);
                await this.screenshot('aicleaner_config_page');
                
                return true;
            }
        }
        
        return false;
    }

    async generateReport(results) {
        console.log('📊 Generating test report...');
        
        const report = {
            timestamp: new Date().toISOString(),
            testResults: results,
            summary: {
                addonFound: results.addonSearch?.found || false,
                installationAttempted: !!results.installation,
                installationSuccessful: results.installation?.success || false,
                alreadyInstalled: results.alreadyInstalled || false,
                error: results.installation?.error || results.error
            }
        };
        
        console.log('\n📋 TEST REPORT SUMMARY:');
        console.log('=' * 40);
        console.log(`Addon Found: ${report.summary.addonFound ? '✅' : '❌'}`);
        console.log(`Installation Attempted: ${report.summary.installationAttempted ? '✅' : '❌'}`);
        console.log(`Installation Successful: ${report.summary.installationSuccessful ? '✅' : '❌'}`);
        console.log(`Already Installed: ${report.summary.alreadyInstalled ? '✅' : '❌'}`);
        if (report.summary.error) {
            console.log(`Error: ${report.summary.error}`);
        }
        
        return report;
    }

    async execute() {
        console.log('🎯 AICLEANER V3 AVAILABILITY TEST');
        console.log('=================================');
        
        const results = {};
        
        try {
            await this.initialize();
            await this.login();
            
            // Check if already installed first
            results.alreadyInstalled = await this.checkIfAlreadyInstalled();
            
            if (results.alreadyInstalled) {
                console.log('🎉 AICleaner v3 is already installed and working!');
            } else {
                // Search for addon in store
                results.addonSearch = await this.searchForAICleaner();
                
                if (results.addonSearch.found) {
                    console.log('✅ AICleaner addon found in store!');
                    
                    // Attempt installation
                    results.installation = await this.testInstallation(results.addonSearch.card);
                    
                    if (results.installation.success) {
                        console.log('🎉 SUCCESS: AICleaner v3 has been successfully installed!');
                    } else {
                        console.log('⚠️ Installation encountered issues:', results.installation.error);
                    }
                } else {
                    console.log('❌ AICleaner addon not found in store');
                }
            }
            
            await this.generateReport(results);
            
        } catch (error) {
            console.error('💥 Test execution failed:', error.message);
            results.error = error.message;
            await this.screenshot('test_execution_error');
        } finally {
            console.log('🧹 Test completed - keeping browser open for inspection...');
            // Keep browser open for manual verification
        }
    }
}

// Execute the test
if (require.main === module) {
    const test = new AddonAvailabilityTest();
    test.execute().catch(console.error);
}

module.exports = AddonAvailabilityTest;