const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false,  
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  
  const context = await browser.newContext({
    ignoreHTTPSErrors: true
  });
  
  const page = await context.newPage();
  
  try {
    console.log('🔌 Navigating to Home Assistant...');
    await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle', timeout: 60000 });
    
    // Handle login
    console.log('🔐 Attempting login...');
    const usernameField = await page.waitForSelector('input[name="username"], ha-textfield[label="Username"] input', { timeout: 10000 });
    await usernameField.fill('drewcifer');
    
    const passwordField = await page.waitForSelector('input[name="password"], ha-textfield[label="Password"] input', { timeout: 10000 });
    await passwordField.fill('Minds63qq!');
    
    const submitButton = await page.waitForSelector('button[type="submit"], mwc-button', { timeout: 10000 });
    await submitButton.click();
    
    // Wait for dashboard
    await page.waitForTimeout(5000);
    
    console.log('📱 Navigating to Supervisor...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    console.log('🏪 Opening Add-on Store...');
    const storeLink = await page.waitForSelector('a[href*="store"], ha-card:has-text("Add-on Store")', { timeout: 10000 });
    await storeLink.click();
    await page.waitForTimeout(3000);
    
    console.log('📋 Opening Repositories...');
    // Navigate to repositories management
    await page.click('button[title="Repositories"], button:has-text("Repositories"), [aria-label="Repositories"]');
    await page.waitForTimeout(2000);
    
    // Take screenshot of current repositories
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/repositories_before.png' });
    
    console.log('🗑️ Removing existing AICleaner repositories (if any)...');
    try {
      // Look for existing repository entries
      const existingRepos = await page.$$('text=/.*aicleaner.*/i, text=/.*sporebattyl.*/i');
      for (const repo of existingRepos) {
        try {
          // Look for remove/delete button near this repository
          const removeBtn = await repo.locator('..').locator('button[title="Remove"], button:has-text("Remove"), mwc-icon-button[icon="delete"]').first();
          await removeBtn.click();
          await page.waitForTimeout(1000);
          // Confirm removal if needed
          const confirmBtn = await page.waitForSelector('button:has-text("Yes"), button:has-text("Remove")', { timeout: 3000 });
          await confirmBtn.click();
          await page.waitForTimeout(2000);
          console.log('✅ Removed existing repository');
        } catch (e) {
          console.log('ℹ️  No remove button found for this entry');
        }
      }
    } catch (e) {
      console.log('ℹ️  No existing repositories to remove');
    }
    
    console.log('➕ Adding corrected AICleaner repository...');
    // Add the repository
    const addButton = await page.waitForSelector('button[title="Add repository"], button:has-text("Add repository"), mwc-fab[icon="add"]', { timeout: 10000 });
    await addButton.click();
    await page.waitForTimeout(1000);
    
    // Enter repository URL
    const urlInput = await page.waitForSelector('input[placeholder*="Repository"], input[placeholder*="URL"], ha-textfield input', { timeout: 5000 });
    await urlInput.fill('https://github.com/sporebattyl/aicleaner_v3');
    
    // Click Add button
    const addConfirmButton = await page.waitForSelector('button:has-text("Add"), mwc-button:has-text("Add")', { timeout: 5000 });
    await addConfirmButton.click();
    
    console.log('⏳ Waiting for repository to load...');
    await page.waitForTimeout(10000); // Wait for repository processing
    
    // Take screenshot after adding repository
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/repositories_after.png' });
    
    console.log('🔍 Going back to store to find addon...');
    // Navigate back to store
    await page.click('button:has-text("Store"), a[href*="store"]');
    await page.waitForTimeout(3000);
    
    // Take screenshot of store
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/store_updated.png' });
    
    console.log('🔍 Looking for AICleaner V3 addon...');
    // Search for the addon
    try {
      // Try different ways to find the addon
      const addonCard = await page.waitForSelector('text="AICleaner V3", [title*="AICleaner"], ha-card:has-text("AICleaner")', { timeout: 15000 });
      await addonCard.click();
      await page.waitForTimeout(2000);
      
      console.log('📦 Found AICleaner V3!')
      
      // Take screenshot of addon page
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_found.png' });
      
      console.log('🚀 Installing addon...');
      // Install the addon
      const installButton = await page.waitForSelector('button:has-text("Install"), mwc-button:has-text("Install")', { timeout: 5000 });
      await installButton.click();
      
      console.log('⏳ Waiting for installation...');
      // Wait for installation to complete
      await page.waitForFunction(
        () => !document.querySelector('button:has-text("Installing")'),
        { timeout: 180000 } // 3 minutes
      );
      
      console.log('✅ Installation completed! Testing configuration...');
      
      // Navigate to Configuration tab
      await page.click('button:has-text("Configuration"), tab-button:has-text("Configuration")');
      await page.waitForTimeout(3000);
      
      // Take screenshot of configuration page
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_test.png' });
      
      console.log('🔧 Testing entity selectors...');
      
      // Check if entity selectors are properly displayed as dropdowns
      const cameraSelector = await page.waitForSelector('ha-entity-picker[label*="camera"], ha-entity-picker[label*="Camera"], select[name*="camera"], ha-select[label*="camera"]', { timeout: 10000 });
      console.log('✅ Camera entity selector found!');
      
      const todoSelector = await page.waitForSelector('ha-entity-picker[label*="todo"], ha-entity-picker[label*="Todo"], select[name*="todo"], ha-select[label*="todo"]', { timeout: 10000 });
      console.log('✅ Todo list entity selector found!');
      
      // Test clicking on selectors to see if dropdowns appear
      await cameraSelector.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/camera_dropdown.png' });
      
      // Click elsewhere to close dropdown
      await page.click('body');
      await page.waitForTimeout(500);
      
      await todoSelector.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/todo_dropdown.png' });
      
      console.log('🎉 Entity selectors are working correctly!');
      
      // Take final configuration screenshot
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/final_config.png' });
      
    } catch (e) {
      console.log('❌ Could not find AICleaner V3 addon in store');
      
      // List available addons for debugging
      const addons = await page.$$eval('[data-addon], .addon-card, ha-card', elements => 
        elements.map(el => el.textContent?.trim()).filter(text => text && text.length < 200)
      );
      console.log('Available addons:', addons.slice(0, 10));
      
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_not_found.png' });
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error('Stack:', error.stack);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test_error.png' });
  }
  
  console.log('🎯 Test completed. Check screenshots for results.');
  await browser.close();
})();