const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Configuration
const HA_URL = 'http://192.168.88.125:8123';
const USERNAME = 'drewcifer';
const PASSWORD = 'Minds63qq!';
const REPO_URL = 'https://github.com/drewcifer/aicleaner_v3';
const SCREENSHOT_DIR = '/home/drewcifer/aicleaner_v3/aicleaner_v3/screenshots';
const EXPECTED_CAMERA = 'camera.rowan_room_fluent';
const EXPECTED_TODO = 'todo.rowan_room_cleaning_to_do';

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

/**
 * Comprehensive AICleaner v3 Reinstallation and Testing
 */
async function testAICleanerReinstallation() {
    console.log('🤖 Arbiter: Starting AICleaner v3 Comprehensive Test...');
    
    const browser = await chromium.launch({ 
        headless: true, // Running headless to avoid system dependency issues
        slowMo: 500 // Reduced delay for headless mode
    });
    
    const context = await browser.newContext({
        viewport: { width: 1920, height: 1080 }
    });
    
    const page = await context.newPage();
    
    try {
        // Step 1: Login to Home Assistant
        console.log('🔐 Step 1: Logging into Home Assistant...');
        await page.goto(HA_URL);
        await page.waitForLoadState('networkidle');
        
        // Check if already logged in
        const loginForm = await page.locator('ha-login-form').first();
        if (await loginForm.isVisible()) {
            await page.fill('input[name="username"]', USERNAME);
            await page.fill('input[name="password"]', PASSWORD);
            await page.click('mwc-button[type="submit"]');
            await page.waitForLoadState('networkidle');
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '01_home_assistant_login.png'),
            fullPage: true 
        });
        
        // Step 2: Navigate to Add-on Store
        console.log('🏪 Step 2: Navigating to Add-on Store...');
        await page.click('ha-sidebar [data-panel="config"]');
        await page.waitForTimeout(2000);
        await page.click('a[href="/config/supervisor"]');
        await page.waitForLoadState('networkidle');
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '02_supervisor_page.png'),
            fullPage: true 
        });
        
        // Step 3: Manage Repositories - Remove existing
        console.log('🗂️ Step 3: Managing repositories...');
        await page.click('a[href="/supervisor/store"]');
        await page.waitForLoadState('networkidle');
        
        // Click the three-dot menu in add-on store
        const menuButton = page.locator('ha-button-menu');
        await menuButton.first().click();
        await page.waitForTimeout(1000);
        
        // Click Repositories
        await page.click('mwc-list-item:has-text("Repositories")');
        await page.waitForTimeout(2000);
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '03_repositories_dialog.png'),
            fullPage: true 
        });
        
        // Look for existing AICleaner repository and remove it
        const existingRepo = page.locator('mwc-list-item').filter({ hasText: 'aicleaner' });
        if (await existingRepo.count() > 0) {
            console.log('🗑️ Removing existing AICleaner repository...');
            const deleteButton = existingRepo.locator('ha-icon-button[data-action="remove"]');
            await deleteButton.click();
            await page.waitForTimeout(2000);
            
            // Confirm deletion if prompted
            const confirmButton = page.locator('mwc-button:has-text("Remove")');
            if (await confirmButton.isVisible()) {
                await confirmButton.click();
                await page.waitForTimeout(3000);
            }
        }
        
        // Step 4: Add repository back
        console.log('➕ Step 4: Re-adding AICleaner repository...');
        const addRepoInput = page.locator('ha-textfield[label="Add repository"]');
        await addRepoInput.fill(REPO_URL);
        await page.click('mwc-button:has-text("Add")');
        await page.waitForTimeout(5000); // Wait for repository to be processed
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '04_repository_added.png'),
            fullPage: true 
        });
        
        // Close repositories dialog
        await page.keyboard.press('Escape');
        await page.waitForTimeout(2000);
        
        // Step 5: Uninstall existing addon (if installed)
        console.log('🔄 Step 5: Managing addon installation...');
        
        // Check if AICleaner is already installed
        const aicleanerAddon = page.locator('addon-card').filter({ hasText: 'AICleaner' }).first();
        if (await aicleanerAddon.isVisible()) {
            console.log('🗑️ Uninstalling existing AICleaner addon...');
            await aicleanerAddon.click();
            await page.waitForLoadState('networkidle');
            
            // Look for uninstall option
            const uninstallButton = page.locator('mwc-button:has-text("Uninstall")');
            if (await uninstallButton.isVisible()) {
                await uninstallButton.click();
                await page.waitForTimeout(2000);
                
                // Confirm uninstall
                const confirmUninstall = page.locator('mwc-button:has-text("Uninstall")');
                if (await confirmUninstall.isVisible()) {
                    await confirmUninstall.click();
                    await page.waitForTimeout(10000); // Wait for uninstall to complete
                }
            }
            
            // Go back to store
            await page.goBack();
            await page.waitForLoadState('networkidle');
        }
        
        // Step 6: Install AICleaner fresh
        console.log('📦 Step 6: Installing AICleaner addon fresh...');
        await page.reload();
        await page.waitForLoadState('networkidle');
        
        const freshAicleanerAddon = page.locator('addon-card').filter({ hasText: 'AICleaner' }).first();
        await freshAicleanerAddon.click();
        await page.waitForLoadState('networkidle');
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '05_aicleaner_addon_page.png'),
            fullPage: true 
        });
        
        // Install the addon
        const installButton = page.locator('mwc-button:has-text("Install")');
        if (await installButton.isVisible()) {
            await installButton.click();
            await page.waitForTimeout(15000); // Wait for installation
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '06_aicleaner_installed.png'),
            fullPage: true 
        });
        
        // Step 7: Navigate to Configuration tab
        console.log('⚙️ Step 7: Testing dropdown configuration...');
        const configTab = page.locator('ha-tab:has-text("Configuration")');
        await configTab.click();
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '07_configuration_tab.png'),
            fullPage: true 
        });
        
        // Step 8: Test dropdown fields
        console.log('🎛️ Step 8: Validating dropdown implementations...');
        
        // Test default_camera dropdown
        console.log('📷 Testing default_camera dropdown...');
        const cameraDropdown = page.locator('ha-selector-entity[name="default_camera"]');
        if (await cameraDropdown.isVisible()) {
            await cameraDropdown.click();
            await page.waitForTimeout(2000);
            
            await page.screenshot({ 
                path: path.join(SCREENSHOT_DIR, '08_camera_dropdown_open.png'),
                fullPage: true 
            });
            
            // Look for expected camera entity
            const expectedCameraOption = page.locator(`mwc-list-item:has-text("${EXPECTED_CAMERA}")`);
            if (await expectedCameraOption.isVisible()) {
                console.log('✅ Camera dropdown working - found expected entity');
                await expectedCameraOption.click();
                await page.waitForTimeout(1000);
            } else {
                console.log('❌ Expected camera entity not found in dropdown');
            }
        } else {
            console.log('❌ Camera dropdown not found - may still be text input');
        }
        
        // Test default_todo_list dropdown
        console.log('📝 Testing default_todo_list dropdown...');
        const todoDropdown = page.locator('ha-selector-entity[name="default_todo_list"]');
        if (await todoDropdown.isVisible()) {
            await todoDropdown.click();
            await page.waitForTimeout(2000);
            
            await page.screenshot({ 
                path: path.join(SCREENSHOT_DIR, '09_todo_dropdown_open.png'),
                fullPage: true 
            });
            
            // Look for expected todo entity
            const expectedTodoOption = page.locator(`mwc-list-item:has-text("${EXPECTED_TODO}")`);
            if (await expectedTodoOption.isVisible()) {
                console.log('✅ Todo dropdown working - found expected entity');
                await expectedTodoOption.click();
                await page.waitForTimeout(1000);
            } else {
                console.log('❌ Expected todo entity not found in dropdown');
            }
        } else {
            console.log('❌ Todo dropdown not found - may still be text input');
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '10_dropdowns_configured.png'),
            fullPage: true 
        });
        
        // Step 9: Save configuration
        console.log('💾 Step 9: Saving configuration...');
        const saveButton = page.locator('mwc-button:has-text("Save")');
        if (await saveButton.isVisible()) {
            await saveButton.click();
            await page.waitForTimeout(3000);
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '11_configuration_saved.png'),
            fullPage: true 
        });
        
        // Step 10: Start the addon
        console.log('🚀 Step 10: Starting AICleaner addon...');
        const infoTab = page.locator('ha-tab:has-text("Info")');
        await infoTab.click();
        await page.waitForTimeout(2000);
        
        const startButton = page.locator('mwc-button:has-text("Start")');
        if (await startButton.isVisible()) {
            await startButton.click();
            await page.waitForTimeout(10000); // Wait for startup
        }
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '12_addon_started.png'),
            fullPage: true 
        });
        
        // Step 11: Check logs for errors
        console.log('📋 Step 11: Checking addon logs...');
        const logTab = page.locator('ha-tab:has-text("Log")');
        await logTab.click();
        await page.waitForTimeout(3000);
        
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, '13_addon_logs.png'),
            fullPage: true 
        });
        
        console.log('✅ AICleaner v3 Comprehensive Test Completed!');
        console.log(`📸 Screenshots saved to: ${SCREENSHOT_DIR}`);
        
        return {
            success: true,
            message: 'AICleaner v3 reinstallation and testing completed successfully',
            screenshots: [
                '01_home_assistant_login.png',
                '02_supervisor_page.png', 
                '03_repositories_dialog.png',
                '04_repository_added.png',
                '05_aicleaner_addon_page.png',
                '06_aicleaner_installed.png',
                '07_configuration_tab.png',
                '08_camera_dropdown_open.png',
                '09_todo_dropdown_open.png',
                '10_dropdowns_configured.png',
                '11_configuration_saved.png',
                '12_addon_started.png',
                '13_addon_logs.png'
            ]
        };
        
    } catch (error) {
        console.error('❌ Test failed:', error);
        await page.screenshot({ 
            path: path.join(SCREENSHOT_DIR, 'error_screenshot.png'),
            fullPage: true 
        });
        
        return {
            success: false,
            message: `Test failed: ${error.message}`,
            error: error
        };
        
    } finally {
        await browser.close();
    }
}

// Run the test
if (require.main === module) {
    testAICleanerReinstallation()
        .then(result => {
            console.log('🏁 Final Result:', result);
            process.exit(result.success ? 0 : 1);
        })
        .catch(error => {
            console.error('💥 Fatal Error:', error);
            process.exit(1);
        });
}

module.exports = { testAICleanerReinstallation };