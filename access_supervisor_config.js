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
    
    console.log('📱 Going to Supervisor dashboard...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of supervisor dashboard
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/supervisor_dash.png' });
    
    console.log('📋 Looking for local add-ons section...');
    
    // Try multiple ways to access local addons
    const possibleSelectors = [
      'text="Local add-ons"',
      'text="Add-ons"',
      '[data-panel="addons"]',
      'ha-card:has-text("Add-ons")',
      'a[href*="/hassio/addon"]'
    ];
    
    let addonSectionFound = false;
    
    for (const selector of possibleSelectors) {
      try {
        console.log(`Trying selector: ${selector}`);
        await page.click(selector, { timeout: 3000 });
        await page.waitForTimeout(2000);
        addonSectionFound = true;
        break;
      } catch (e) {
        console.log(`Selector ${selector} not found`);
      }
    }
    
    if (!addonSectionFound) {
      // Try direct navigation to addons
      console.log('📋 Direct navigation to addons...');
      await page.goto('http://192.168.88.125:8123/hassio/addon', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(5000);
    }
    
    // Take screenshot after navigation
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/after_addon_nav.png' });
    
    console.log('🔍 Looking for any addon cards or elements...');
    
    // Wait for page to fully load
    await page.waitForTimeout(5000);
    
    // Look for addon cards with more broad selectors
    const addonElements = await page.$$eval('*', elements => {
      const found = [];
      elements.forEach(el => {
        const text = el.textContent?.trim() || '';
        if (text.length > 5 && text.length < 200 && (
          text.toLowerCase().includes('aicleaner') ||
          text.toLowerCase().includes('ai cleaner') ||
          text.toLowerCase().includes('addon') ||
          (text.includes('v3') && text.toLowerCase().includes('ai'))
        )) {
          found.push({
            tag: el.tagName,
            text: text.substring(0, 100),
            className: el.className,
            id: el.id,
            clickable: el.tagName === 'A' || el.tagName === 'BUTTON' || el.onclick || el.classList?.contains('clickable')
          });
        }
      });
      return found.slice(0, 20);
    });
    
    console.log('Addon-related elements found:', JSON.stringify(addonElements, null, 2));
    
    // Try to click on any AICleaner element
    try {
      console.log('🔍 Attempting to click on AICleaner element...');
      await page.click('text=/.*AICleaner.*/', { timeout: 5000 });
      await page.waitForTimeout(3000);
      
      console.log('✅ Clicked on AICleaner element!');
      
      // Take screenshot after clicking
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/after_aicleaner_click.png' });
      
      console.log('🔧 Looking for Configuration section...');
      
      // Try to find configuration
      const configSelectors = [
        'button:has-text("Configuration")',
        '[role="tab"]:has-text("Configuration")',
        'text="Configuration"',
        '.configuration',
        '[data-tab="configuration"]'
      ];
      
      let configFound = false;
      for (const selector of configSelectors) {
        try {
          console.log(`Trying config selector: ${selector}`);
          await page.click(selector, { timeout: 3000 });
          await page.waitForTimeout(2000);
          configFound = true;
          break;
        } catch (e) {
          console.log(`Config selector ${selector} not found`);
        }
      }
      
      if (configFound) {
        console.log('✅ Found Configuration section!');
        
        // Take screenshot of configuration
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_screen.png' });
        
        console.log('🔍 Looking for form fields...');
        
        // Look for form fields
        const formFields = await page.$$eval('*', elements => {
          const fields = [];
          elements.forEach(el => {
            if (el.tagName && (
              el.tagName === 'INPUT' ||
              el.tagName === 'SELECT' ||
              el.tagName === 'TEXTAREA' ||
              el.tagName.startsWith('HA-') ||
              el.getAttribute('name') ||
              el.getAttribute('placeholder')
            )) {
              fields.push({
                tag: el.tagName,
                type: el.type,
                name: el.name || el.getAttribute('name'),
                placeholder: el.placeholder || el.getAttribute('placeholder'),
                value: el.value,
                visible: el.offsetParent !== null,
                outerHTML: el.outerHTML.substring(0, 200)
              });
            }
          });
          return fields;
        });
        
        console.log('Form fields in configuration:', JSON.stringify(formFields, null, 2));
        
        // Take full page screenshot
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_full_final.png', fullPage: true });
        
      } else {
        console.log('❌ Configuration section not found');
      }
      
    } catch (e) {
      console.log('❌ Could not click on AICleaner element:', e.message);
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/supervisor_access_error.png' });
  }
  
  await browser.close();
})();