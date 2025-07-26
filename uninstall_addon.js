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
    
    // Wait for dashboard to load
    await page.waitForTimeout(5000);
    
    console.log('📱 Navigating to Supervisor...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    console.log('🏪 Opening Add-on Store...');
    // Look for "Add-on Store" link or button
    const storeLink = await page.waitForSelector('a[href*="store"], ha-card:has-text("Add-on Store")', { timeout: 10000 });
    await storeLink.click();
    await page.waitForTimeout(3000);
    
    console.log('🔍 Looking for AICleaner addon...');
    // Search for AICleaner in installed addons
    const aicleanerElement = await page.waitForSelector('text="AICleaner", text="AI Cleaner", [title*="AICleaner"], [title*="AI Cleaner"]', { timeout: 10000 });
    await aicleanerElement.click();
    await page.waitForTimeout(2000);
    
    console.log('🗑️ Uninstalling addon...');
    // Look for uninstall button
    const uninstallButton = await page.waitForSelector('button:has-text("Uninstall"), mwc-button:has-text("Uninstall")', { timeout: 10000 });
    await uninstallButton.click();
    
    // Confirm uninstall
    await page.waitForTimeout(1000);
    const confirmButton = await page.waitForSelector('button:has-text("Yes"), button:has-text("Confirm"), mwc-button:has-text("Yes")', { timeout: 5000 });
    await confirmButton.click();
    
    console.log('⏳ Waiting for uninstallation to complete...');
    // Wait for uninstall to complete
    await page.waitForFunction(
      () => !document.querySelector('button:has-text("Uninstalling")'),
      { timeout: 60000 }
    );
    
    console.log('✅ AICleaner addon uninstalled successfully!');
    
    // Take screenshot of final state
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/uninstall_complete.png' });
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error('Stack:', error.stack);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/uninstall_error.png' });
  }
  
  await browser.close();
})();