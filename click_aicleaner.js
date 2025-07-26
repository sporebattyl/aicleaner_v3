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
    await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of current state
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/current_store.png' });
    
    console.log('🔍 Clicking on AI Cleaner v3...');
    // Click on the AI Cleaner v3 addon
    const aicleanerCard = await page.waitForSelector('text="AI Cleaner v3"', { timeout: 10000 });
    await aicleanerCard.click();
    await page.waitForTimeout(3000);
    
    // Take screenshot of addon page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_page_current.png' });
    
    console.log('🔧 Going to Configuration tab...');
    // Navigate to Configuration
    await page.click('button:has-text("Configuration"), [role="tab"]:has-text("Configuration")');
    await page.waitForTimeout(3000);
    
    // Take screenshot of configuration
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_current.png' });
    
    console.log('🔍 Checking entity selectors...');
    
    // Look for entity picker elements
    const entityPickers = await page.$$('[type="text"], ha-textfield, ha-entity-picker, ha-select');
    console.log(`Found ${entityPickers.length} input elements`);
    
    // Check if there are any dropdowns or entity selectors
    const selectors = await page.$$eval('*', elements => {
      const found = [];
      elements.forEach(el => {
        if (el.tagName && (
          el.tagName.includes('ha-entity') ||
          el.tagName.includes('ha-select') ||
          el.className?.includes('entity') ||
          el.getAttribute('placeholder')?.includes('entity')
        )) {
          found.push({
            tag: el.tagName,
            id: el.id,
            className: el.className,
            placeholder: el.getAttribute('placeholder'),
            textContent: el.textContent?.substring(0, 50)
          });
        }
      });
      return found;
    });
    
    console.log('Entity-related elements found:', selectors);
    
    // Take detailed screenshot showing any form fields
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/form_fields.png', fullPage: true });
    
    console.log('✅ Configuration check completed!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/click_error.png' });
  }
  
  await browser.close();
})();