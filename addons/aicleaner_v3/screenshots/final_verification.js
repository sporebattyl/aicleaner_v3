const { chromium } = require('playwright');

/**
 * Final Verification Script
 * Check if AICleaner is already installed and working
 */

const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';

class FinalVerification {
    constructor() {
        this.browser = null;
        this.page = null;
    }

    async initialize() {
        console.log('🚀 Starting final verification...');
        this.browser = await chromium.launch({ 
            headless: false,
            slowMo: 500
        });
        this.page = await this.browser.newPage();
        await this.page.setViewportSize({ width: 1920, height: 1080 });
    }

    async screenshot(name) {
        const timestamp = Date.now();
        const filepath = `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/final_${name}_${timestamp}.png`;
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
        console.log('✅ Logged in');
        await this.screenshot('logged_in');
    }

    async checkSidebar() {
        console.log('🔍 Checking sidebar for AICleaner...');
        await this.screenshot('sidebar_check');
        
        // Look for AICleaner in the sidebar
        const sidebarItems = await this.page.locator('a[role="option"], .sidebar-item, paper-item, ha-sidebar-item').all();
        
        for (const item of sidebarItems) {
            const itemText = await item.textContent();
            if (itemText && itemText.toLowerCase().includes('aicleaner')) {
                console.log('🎯 Found AICleaner in sidebar!');
                console.log(`Sidebar text: "${itemText}"`);
                
                // Click on it
                await item.click();
                await this.page.waitForTimeout(3000);
                await this.screenshot('aicleaner_page_from_sidebar');
                
                return true;
            }
        }
        
        return false;
    }

    async checkAddonStore() {
        console.log('🏪 Checking Add-on Store...');
        
        await this.page.goto(`${HA_URL}/hassio/store`);
        await this.page.waitForLoadState('networkidle');
        await this.page.waitForTimeout(3000);
        await this.screenshot('addon_store_check');
        
        // Look for search functionality
        const searchInput = this.page.locator('input[placeholder*="Search"], input[type="search"]').first();
        if (await searchInput.count() > 0) {
            console.log('🔎 Searching for AICleaner...');
            await searchInput.fill('AICleaner');
            await this.page.waitForTimeout(3000);
            await this.screenshot('search_for_aicleaner');
        }
        
        // Check different sections of the store
        const sections = [
            'Official add-ons',
            'Home Assistant Community Add-ons', 
            'Home assistant Addon Repo'
        ];
        
        for (const section of sections) {
            console.log(`📋 Checking section: ${section}`);
            
            // Look for section header
            const sectionHeader = this.page.locator(`text="${section}"`).first();
            if (await sectionHeader.count() > 0) {
                console.log(`✅ Found section: ${section}`);
                
                // Scan items in this section
                const sectionContainer = sectionHeader.locator('..').locator('..');
                const addonItems = await sectionContainer.locator('[role="button"], .addon-card, .card').all();
                
                for (const addon of addonItems) {
                    const addonText = await addon.textContent();
                    if (addonText && addonText.toLowerCase().includes('aicleaner')) {
                        console.log('🎯 Found AICleaner addon in store!');
                        console.log(`Addon text: ${addonText.substring(0, 200)}...`);
                        await this.screenshot('aicleaner_found_in_store');
                        
                        // Click on it
                        await addon.click();
                        await this.page.waitForTimeout(3000);
                        await this.screenshot('aicleaner_details');
                        
                        return true;
                    }
                }
            }
        }
        
        // Also try a more general approach - scan all visible text
        const pageText = await this.page.textContent('body');
        if (pageText && pageText.toLowerCase().includes('aicleaner')) {
            console.log('✅ AICleaner text found on page');
            return true;
        }
        
        return false;
    }

    async checkInstalledAddons() {
        console.log('📦 Checking installed addons...');
        
        await this.page.goto(`${HA_URL}/hassio/addon`);
        await this.page.waitForLoadState('networkidle');
        await this.page.waitForTimeout(5000); // Give time for loading
        await this.screenshot('installed_addons_check');
        
        // Wait for any loading to complete
        const loadingSpinner = this.page.locator('.loading, ha-circular-progress').first();
        if (await loadingSpinner.count() > 0) {
            console.log('⏳ Waiting for installed addons to load...');
            await this.page.waitForTimeout(10000);
            await this.screenshot('after_loading_wait');
        }
        
        // Check for AICleaner in installed addons
        const installedItems = await this.page.locator('[role="button"], .addon-card, .card, ha-addon-card').all();
        
        for (const item of installedItems) {
            const itemText = await item.textContent();
            if (itemText && itemText.toLowerCase().includes('aicleaner')) {
                console.log('🎯 AICleaner found in installed addons!');
                console.log(`Installed addon text: ${itemText.substring(0, 200)}...`);
                await this.screenshot('aicleaner_installed');
                
                // Click to access it
                await item.click();
                await this.page.waitForTimeout(3000);
                await this.screenshot('aicleaner_addon_page');
                
                return true;
            }
        }
        
        return false;
    }

    async testDropdownFunctionality() {
        console.log('🧪 Testing dropdown functionality...');
        
        // Try to navigate to configuration
        const configTab = this.page.locator('text=Configuration, paper-tab:has-text("Configuration"), mwc-tab:has-text("Configuration")').first();
        
        if (await configTab.count() > 0) {
            await configTab.click();
            await this.page.waitForTimeout(3000);
            await this.screenshot('configuration_tab');
            
            // Look for entity selector dropdowns
            const dropdowns = await this.page.locator('ha-entity-picker, ha-selector, ha-combo-box').all();
            
            if (dropdowns.length > 0) {
                console.log(`✅ Found ${dropdowns.length} dropdown(s) in configuration`);
                
                // Test first dropdown
                try {
                    await dropdowns[0].click();
                    await this.page.waitForTimeout(2000);
                    await this.screenshot('dropdown_opened');
                    
                    // Check if options appeared
                    const dropdownOptions = await this.page.locator('mwc-list-item, paper-item, .option').count();
                    if (dropdownOptions > 0) {
                        console.log(`✅ Dropdown working - found ${dropdownOptions} options`);
                        return true;
                    } else {
                        console.log('⚠️ Dropdown opened but no options found');
                        return false;
                    }
                } catch (e) {
                    console.log('⚠️ Error testing dropdown:', e.message);
                    return false;
                }
            } else {
                console.log('⚠️ No dropdowns found in configuration');
                return false;
            }
        } else {
            console.log('⚠️ Configuration tab not found');
            return false;
        }
    }

    async generateFinalReport(results) {
        console.log('\n🎯 FINAL VERIFICATION REPORT');
        console.log('============================');
        
        const report = {
            timestamp: new Date().toISOString(),
            results: results,
            overall_status: 'unknown'
        };
        
        if (results.sidebarFound || results.installedAddonFound) {
            report.overall_status = 'success_installed';
            console.log('🎉 SUCCESS: AICleaner v3 is INSTALLED and AVAILABLE!');
        } else if (results.storeFound) {
            report.overall_status = 'success_available';
            console.log('✅ SUCCESS: AICleaner v3 is AVAILABLE for installation!');
        } else {
            report.overall_status = 'not_found';
            console.log('❌ AICleaner v3 not found in Home Assistant');
        }
        
        console.log('\nDetailed Results:');
        console.log(`- Found in sidebar: ${results.sidebarFound ? '✅' : '❌'}`);
        console.log(`- Found in addon store: ${results.storeFound ? '✅' : '❌'}`);
        console.log(`- Found in installed addons: ${results.installedAddonFound ? '✅' : '❌'}`);
        console.log(`- Dropdowns working: ${results.dropdownsWorking ? '✅' : '❌'}`);
        
        return report;
    }

    async execute() {
        console.log('🎯 FINAL AICLEANER V3 VERIFICATION');
        console.log('==================================');
        
        const results = {
            sidebarFound: false,
            storeFound: false,
            installedAddonFound: false,
            dropdownsWorking: false
        };
        
        try {
            await this.initialize();
            await this.login();
            
            // Check 1: Sidebar
            results.sidebarFound = await this.checkSidebar();
            
            // Check 2: Add-on Store
            results.storeFound = await this.checkAddonStore();
            
            // Check 3: Installed Addons
            results.installedAddonFound = await this.checkInstalledAddons();
            
            // Check 4: Dropdown functionality (if addon found)
            if (results.sidebarFound || results.installedAddonFound) {
                results.dropdownsWorking = await this.testDropdownFunctionality();
            }
            
            const report = await this.generateFinalReport(results);
            
            // Save report to file
            const fs = require('fs');
            const reportPath = `/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots/final_verification_report_${Date.now()}.json`;
            fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
            console.log(`📊 Report saved: ${reportPath}`);
            
        } catch (error) {
            console.error('💥 Verification failed:', error.message);
            await this.screenshot('verification_error');
        } finally {
            console.log('🧹 Verification complete - keeping browser open...');
            // Keep browser open for manual inspection
        }
    }
}

// Execute verification
if (require.main === module) {
    const verification = new FinalVerification();
    verification.execute().catch(console.error);
}

module.exports = FinalVerification;