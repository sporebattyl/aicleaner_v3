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
    
    console.log('📱 Going directly to Add-ons...');
    await page.goto('http://192.168.88.125:8123/hassio/addon', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of addons page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addons_page.png' });
    
    console.log('🔍 Looking for AICleaner...');
    // Try to find AICleaner addon
    try {
      await page.click('text=AICleaner');
      await page.waitForTimeout(2000);
      console.log('✅ Found AICleaner addon!');
    } catch (e) {
      console.log('❌ AICleaner not found in first attempt, trying alternatives...');
      try {
        await page.click('text=AI Cleaner');
        await page.waitForTimeout(2000);
        console.log('✅ Found AI Cleaner addon!');
      } catch (e2) {
        // Show what's available
        const elements = await page.$$eval('*', els => 
          els.map(el => el.textContent?.trim())
            .filter(text => text && text.length > 3 && text.length < 100)
            .slice(0, 20)
        );
        console.log('Available elements:', elements);
        return;
      }
    }
    
    // Take screenshot of addon page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_page.png' });
    
    console.log('🔧 Going to Configuration...');
    // Navigate to Configuration tab
    await page.click('text=Configuration');
    await page.waitForTimeout(3000);
    
    // Take screenshot of configuration
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/configuration.png' });
    
    console.log('✅ Configuration accessed successfully!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/final_error.png' });
  }
  
  await browser.close();
})();