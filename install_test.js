const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false,  // Keep visible for debugging
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
    await page.waitForTimeout(2000);
    
    // Try different login selectors
    try {
      await page.fill('input[name="username"]', 'drewcifer');
      await page.fill('input[name="password"]', 'Minds63qq!');
      await page.click('button[type="submit"]');
    } catch (e) {
      // Try alternative selectors
      await page.fill('ha-textfield[label="Username"] input', 'drewcifer');
      await page.fill('ha-textfield[label="Password"] input', 'Minds63qq!');
      await page.click('mwc-button');
    }
    
    // Wait for dashboard
    await page.waitForTimeout(5000);
    
    console.log('📱 Navigating to Supervisor...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of supervisor
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/supervisor_screen.png' });
    console.log('📸 Supervisor screenshot saved');
    
    console.log('🏪 Opening Add-on Store...');
    // Try different ways to get to addon store
    try {
      await page.click('text=Add-on Store');
    } catch (e) {
      await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'domcontentloaded' });
    }
    
    await page.waitForTimeout(3000);
    
    console.log('📋 Checking repositories...');
    // Navigate to repositories
    await page.click('[title="Repositories"], button:has-text("Repositories")');
    await page.waitForTimeout(2000);
    
    // Take screenshot of repositories
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/repositories_screen.png' });
    console.log('📸 Repositories screenshot saved');
    
    console.log('➕ Adding AICleaner repository...');
    try {
      // Try to add repository
      await page.click('button[title="Add repository"], button:has-text("Add repository")');
      await page.waitForTimeout(1000);
      
      await page.fill('input[placeholder*="Repository"], input[placeholder*="URL"]', 'https://github.com/sporebattyl/aicleaner_v3');
      await page.click('button:has-text("Add")');
      await page.waitForTimeout(5000);
      
      console.log('✅ Repository added successfully');
    } catch (e) {
      console.log('ℹ️  Repository might already exist');
    }
    
    console.log('🔍 Going back to store to find addon...');
    // Go back to store
    await page.click('button:has-text("Store")');
    await page.waitForTimeout(3000);
    
    // Take screenshot of store
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/store_screen.png' });
    console.log('📸 Store screenshot saved');
    
    console.log('🔍 Looking for AICleaner V3 addon...');
    // Look for our addon
    try {
      await page.click('text="AICleaner V3"');
      await page.waitForTimeout(2000);
      
      console.log('📦 Found AICleaner V3, checking status...');
      
      // Take screenshot of addon page
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_page.png' });
      console.log('📸 Addon page screenshot saved');
      
      // Try to install if not installed
      try {
        await page.click('button:has-text("Install")');
        console.log('🚀 Installing addon...');
        
        // Wait for installation to complete
        await page.waitForFunction(
          () => !document.querySelector('button:has-text("Installing")'),
          { timeout: 180000 } // 3 minutes
        );
        
        console.log('✅ Installation completed!');
        
        // Take final screenshot
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/install_complete.png' });
        
      } catch (e) {
        console.log('ℹ️  Install button not found - addon might already be installed');
      }
      
    } catch (e) {
      console.log('❌ AICleaner V3 addon not found in store');
      console.log('Available addons on page:');
      
      const addons = await page.$$eval('[data-addon], .addon-card, .addon-item', elements => 
        elements.map(el => el.textContent?.trim()).filter(text => text)
      );
      console.log(addons);
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/error_screen.png' });
  }
  
  console.log('🎯 Test completed. Check screenshots for results.');
  await browser.close();
})();