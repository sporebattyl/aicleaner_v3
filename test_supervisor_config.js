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
    
    console.log('📱 Going to Supervisor...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    console.log('📋 Going to Add-ons...');
    await page.click('text=Add-ons');
    await page.waitForTimeout(3000);
    
    console.log('🔍 Looking for AICleaner V3...');
    // Look for AICleaner in local add-ons
    await page.click('text=AICleaner V3');
    await page.waitForTimeout(2000);
    
    // Take screenshot of addon details page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_details_page.png' });
    
    console.log('🔧 Opening Configuration...');
    // Click on Configuration tab
    await page.click('[role="tab"]:has-text("Configuration"), button:has-text("Configuration")');
    await page.waitForTimeout(3000);
    
    // Take screenshot of configuration page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/configuration_tab.png' });
    
    console.log('🔍 Looking for entity selector elements...');
    
    // Check for entity selectors specifically
    const entitySelectors = await page.$$eval('*', elements => {
      const selectors = [];
      elements.forEach(el => {
        // Look for Home Assistant entity picker components
        if (el.tagName === 'HA-ENTITY-PICKER' || 
            el.tagName === 'HA-ENTITY-SELECT' ||
            el.className?.includes('entity-picker') ||
            el.getAttribute('entity-selector') ||
            (el.tagName === 'SELECT' && el.getAttribute('name')?.includes('entity')) ||
            (el.tagName === 'INPUT' && (
              el.getAttribute('placeholder')?.includes('entity') ||
              el.getAttribute('name')?.includes('camera') ||
              el.getAttribute('name')?.includes('todo')
            ))) {
          selectors.push({
            tag: el.tagName,
            id: el.id,
            name: el.getAttribute('name'),
            className: el.className,
            placeholder: el.getAttribute('placeholder'),
            value: el.value,
            outerHTML: el.outerHTML.substring(0, 200)
          });
        }
      });
      return selectors;
    });
    
    console.log('Entity selector elements found:', JSON.stringify(entitySelectors, null, 2));
    
    // Also check for any form fields
    const formFields = await page.$$eval('input, select, textarea, ha-textfield', elements => {
      return elements.map(el => ({
        tag: el.tagName,
        type: el.type,
        name: el.name || el.getAttribute('name'),
        id: el.id,
        placeholder: el.placeholder || el.getAttribute('placeholder'),
        value: el.value,
        label: el.getAttribute('label'),
        outerHTML: el.outerHTML.substring(0, 150)
      }));
    });
    
    console.log('All form fields found:', JSON.stringify(formFields.slice(0, 10), null, 2));
    
    // Take full page screenshot
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_full.png', fullPage: true });
    
    console.log('✅ Configuration analysis completed!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/supervisor_error.png' });
  }
  
  await browser.close();
})();