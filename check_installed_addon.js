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
    
    console.log('🔍 Checking if AICleaner is in sidebar...');
    // Click on AICleaner in the sidebar (I can see it in the previous screenshot)
    await page.click('a[href*="aicleaner"], text="AICleaner"');
    await page.waitForTimeout(3000);
    
    // Take screenshot of AICleaner interface
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_interface.png' });
    
    console.log('📱 Going to Supervisor to check addon status...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of supervisor dashboard
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/supervisor_dashboard.png' });
    
    console.log('📋 Checking add-ons section...');
    // Go to Add-ons tab
    await page.goto('http://192.168.88.125:8123/hassio/addon', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of addons page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addons_installed.png' });
    
    console.log('🔍 Looking for AICleaner in installed addons...');
    // Look for AICleaner addon
    try {
      const aicleanerAddon = await page.waitForSelector('text=/.*AICleaner.*/, text=/.*AI Cleaner.*/', { timeout: 5000 });
      await aicleanerAddon.click();
      await page.waitForTimeout(2000);
      
      console.log('✅ Found AICleaner addon! Opening it...');
      
      // Take screenshot of addon details
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_details.png' });
      
      console.log('🔧 Checking Configuration tab...');
      // Go to Configuration tab
      await page.click('button:has-text("Configuration"), [role="tab"]:has-text("Configuration")');
      await page.waitForTimeout(3000);
      
      // Take screenshot of configuration
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_page.png' });
      
      console.log('🔍 Analyzing configuration fields...');
      
      // Get all form elements
      const formElements = await page.$$eval('*', elements => {
        const forms = [];
        elements.forEach(el => {
          if (el.tagName && (
            el.tagName === 'INPUT' ||
            el.tagName === 'SELECT' ||
            el.tagName === 'TEXTAREA' ||
            el.tagName.includes('HA-') ||
            el.className?.includes('form') ||
            el.className?.includes('input') ||
            el.getAttribute('name') ||
            el.getAttribute('placeholder')
          )) {
            forms.push({
              tag: el.tagName,
              type: el.type,
              name: el.name,
              id: el.id,
              className: el.className,
              placeholder: el.getAttribute('placeholder'),
              value: el.value,
              textContent: el.textContent?.substring(0, 50)
            });
          }
        });
        return forms;
      });
      
      console.log('Form elements found:', JSON.stringify(formElements, null, 2));
      
      // Take full page screenshot
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_full_page.png', fullPage: true });
      
    } catch (e) {
      console.log('❌ Could not find AICleaner addon in installed addons');
      
      // List all visible addons for debugging
      const addons = await page.$$eval('*', elements => {
        const found = [];
        elements.forEach(el => {
          if (el.textContent && el.textContent.length > 3 && el.textContent.length < 100) {
            const text = el.textContent.trim();
            if (text.includes('addon') || text.includes('Add-on') || 
                (text.length > 5 && text.length < 50 && !text.includes('\n'))) {
              found.push(text);
            }
          }
        });
        return [...new Set(found)].slice(0, 20);
      });
      console.log('Visible text elements:', addons);
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/check_error.png' });
  }
  
  await browser.close();
})();