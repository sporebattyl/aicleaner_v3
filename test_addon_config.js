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
    
    // Try to fill login form
    try {
      const usernameInput = await page.waitForSelector('input[name="username"], ha-textfield[label="Username"] input, mwc-textfield[label="Username"] input', { timeout: 10000 });
      await usernameInput.fill('drewcifer');
      
      const passwordInput = await page.waitForSelector('input[name="password"], ha-textfield[label="Password"] input, mwc-textfield[label="Password"] input', { timeout: 5000 });
      await passwordInput.fill('Minds63qq!');
      
      const submitButton = await page.waitForSelector('button[type="submit"], mwc-button[unelevated]', { timeout: 5000 });
      await submitButton.click();
      
      console.log('✅ Login submitted');
    } catch (e) {
      console.log('ℹ️ Login form not found or already logged in');
    }
    
    // Wait for dashboard
    await page.waitForTimeout(5000);
    
    console.log('📱 Navigating to Supervisor...');
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    console.log('🏪 Opening Add-on Store...');
    await page.goto('http://192.168.88.125:8123/hassio/store', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of store
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/store_current.png' });
    console.log('📸 Store screenshot saved');
    
    console.log('🔍 Looking for AICleaner V3 addon...');
    
    // Try different selectors for finding the addon
    const possibleSelectors = [
      'text="AICleaner V3"',
      '[title*="AICleaner"]',
      '[aria-label*="AICleaner"]',
      '.addon-card:has-text("AICleaner")',
      'addon-card[data-addon*="aicleaner"]'
    ];
    
    let addonFound = false;
    for (const selector of possibleSelectors) {
      try {
        console.log(`Trying selector: ${selector}`);
        const addon = await page.waitForSelector(selector, { timeout: 3000 });
        if (addon) {
          console.log('✅ Found AICleaner addon!');
          await addon.click();
          addonFound = true;
          break;
        }
      } catch (e) {
        console.log(`❌ Selector ${selector} not found`);
      }
    }
    
    if (!addonFound) {
      console.log('🔍 Searching all addon cards...');
      const addonCards = await page.$$('.addon-card, [data-addon], ha-card');
      console.log(`Found ${addonCards.length} addon cards`);
      
      for (let i = 0; i < addonCards.length; i++) {
        const card = addonCards[i];
        const text = await card.textContent();
        if (text && text.toLowerCase().includes('aicleaner')) {
          console.log(`✅ Found AICleaner at index ${i}: ${text.substring(0, 100)}...`);
          await card.click();
          addonFound = true;
          break;
        }
      }
    }
    
    if (addonFound) {
      await page.waitForTimeout(3000);
      
      console.log('⚙️ Opening Configuration tab...');
      
      // Look for Configuration tab
      const configTabSelectors = [
        'paper-tab:has-text("Configuration")',
        'mwc-tab:has-text("Configuration")', 
        'ha-tab:has-text("Configuration")',
        '[data-tab="configuration"]',
        'text="Configuration"'
      ];
      
      let configTabFound = false;
      for (const selector of configTabSelectors) {
        try {
          const configTab = await page.waitForSelector(selector, { timeout: 3000 });
          if (configTab) {
            await configTab.click();
            configTabFound = true;
            console.log('✅ Opened Configuration tab');
            break;
          }
        } catch (e) {
          console.log(`Config tab selector ${selector} not found`);
        }
      }
      
      if (!configTabFound) {
        console.log('ℹ️ Trying to click Configuration link...');
        await page.click('a[href*="config"], button:has-text("Configuration")');
      }
      
      await page.waitForTimeout(3000);
      
      // Take screenshot of configuration page
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_ui.png' });
      console.log('📸 Configuration UI screenshot saved');
      
      console.log('🔍 Analyzing configuration fields...');
      
      // Check for entity selectors
      const entitySelectors = await page.$$('[data-selector="entity"], ha-entity-picker, mwc-select, ha-select');
      console.log(`Found ${entitySelectors.length} potential entity selector(s)`);
      
      // Check for all form inputs
      const allInputs = await page.$$('input, select, textarea, ha-textfield, mwc-textfield, ha-entity-picker');
      console.log(`Found ${allInputs.length} total form inputs`);
      
      // Analyze each input
      for (let i = 0; i < allInputs.length; i++) {
        try {
          const input = allInputs[i];
          const tagName = await input.evaluate(el => el.tagName);
          const type = await input.evaluate(el => el.type || el.getAttribute('type') || 'unknown');
          const label = await input.evaluate(el => 
            el.getAttribute('label') || 
            el.getAttribute('placeholder') || 
            el.getAttribute('aria-label') ||
            (el.previousElementSibling && el.previousElementSibling.textContent) ||
            'unlabeled'
          );
          
          console.log(`Input ${i}: ${tagName} (${type}) - ${label}`);
        } catch (e) {
          console.log(`Input ${i}: Could not analyze`);
        }
      }
      
      // Test if we can find default_camera and default_todo_list fields
      const cameraField = await page.$('[label*="camera"], [placeholder*="camera"], input[name*="camera"]');
      const todoField = await page.$('[label*="todo"], [placeholder*="todo"], input[name*="todo"]');
      
      if (cameraField) {
        console.log('✅ Found camera field');
        // Try to click it to see if it opens a dropdown
        await cameraField.click();
        await page.waitForTimeout(1000);
      } else {
        console.log('❌ Camera field not found');
      }
      
      if (todoField) {
        console.log('✅ Found todo field');
        await todoField.click();
        await page.waitForTimeout(1000);
      } else {
        console.log('❌ Todo field not found');
      }
      
      // Take final screenshot
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_final.png' });
      console.log('📸 Final configuration screenshot saved');
      
    } else {
      console.log('❌ AICleaner V3 addon not found in store');
      
      // List all visible addon names
      const addonNames = await page.$$eval('.addon-card, [data-addon]', cards => 
        cards.map(card => card.textContent?.trim()).filter(text => text)
      );
      console.log('Available addons:', addonNames.slice(0, 10));
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test_error.png' });
  }
  
  console.log('✅ Test completed. Check screenshots for results.');
  
  // Keep browser open for 30 seconds to inspect
  await page.waitForTimeout(30000);
  
  await browser.close();
})();