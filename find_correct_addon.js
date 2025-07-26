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
    
    console.log('📱 Going to Supervisor Add-ons...');
    await page.goto('http://192.168.88.125:8123/hassio/addon', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(3000);
    
    // Take screenshot of addons page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addons_list.png' });
    
    console.log('🔍 Finding AICleaner addon and getting its slug...');
    
    // Get all addon links and their URLs
    const addonLinks = await page.$$eval('a[href*="/hassio/addon/"], ha-card a, [data-addon] a', elements => {
      return elements.map(el => ({
        text: el.textContent?.trim(),
        href: el.href,
        slug: el.href?.split('/addon/')[1]?.split('/')[0] || el.href?.split('/addon/')[1]
      })).filter(item => item.text && item.href);
    });
    
    console.log('Found addon links:', JSON.stringify(addonLinks, null, 2));
    
    // Look for AICleaner specifically
    const aicleanerLink = addonLinks.find(link => 
      link.text?.toLowerCase().includes('aicleaner') || 
      link.text?.toLowerCase().includes('ai cleaner')
    );
    
    if (aicleanerLink) {
      console.log('✅ Found AICleaner addon:', aicleanerLink);
      
      console.log('🔧 Navigating to AICleaner configuration...');
      await page.goto(aicleanerLink.href, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(3000);
      
      // Take screenshot of addon page
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/aicleaner_addon_page.png' });
      
      console.log('🔧 Clicking Configuration tab...');
      // Try to click on Configuration tab
      await page.click('button:has-text("Configuration"), [role="tab"]:has-text("Configuration"), text="Configuration"');
      await page.waitForTimeout(3000);
      
      // Take screenshot of configuration
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/actual_config_page.png' });
      
      console.log('🔍 Looking for form fields in configuration...');
      
      // Check for form fields
      const configFields = await page.$$eval('*', elements => {
        const fields = [];
        elements.forEach(el => {
          if (el.tagName && (
            el.tagName === 'INPUT' ||
            el.tagName === 'SELECT' ||
            el.tagName === 'TEXTAREA' ||
            el.tagName.startsWith('HA-') ||
            el.classList?.contains('input') ||
            el.classList?.contains('select') ||
            el.getAttribute('name') ||
            el.getAttribute('placeholder')
          )) {
            fields.push({
              tag: el.tagName,
              type: el.type,
              name: el.name || el.getAttribute('name'),
              id: el.id,
              className: el.className,
              placeholder: el.placeholder || el.getAttribute('placeholder'),
              value: el.value,
              textContent: el.textContent?.substring(0, 100),
              outerHTML: el.outerHTML.substring(0, 300)
            });
          }
        });
        return fields;
      });
      
      console.log('Configuration fields found:', JSON.stringify(configFields, null, 2));
      
      // Take full page screenshot
      await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_full_page_real.png', fullPage: true });
      
    } else {
      console.log('❌ AICleaner addon not found in addon list');
      
      // Try clicking on any addon card that looks like it might be AICleaner
      const addonCards = await page.$$('ha-card, .addon-card, [data-addon]');
      for (let card of addonCards) {
        const text = await card.textContent();
        if (text?.toLowerCase().includes('ai') || text?.toLowerCase().includes('cleaner')) {
          console.log('Found potential AICleaner card:', text.substring(0, 100));
          await card.click();
          await page.waitForTimeout(2000);
          await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/clicked_addon.png' });
          break;
        }
      }
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/find_addon_error.png' });
  }
  
  await browser.close();
})();