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
    
    console.log('📱 Testing direct addon URL access...');
    // Test the correct addon URL with the slug identified by Gemini
    await page.goto('http://192.168.88.125:8123/hassio/addon/aicleaner_v3/config', { 
      waitUntil: 'domcontentloaded', 
      timeout: 60000 
    });
    await page.waitForTimeout(5000);
    
    // Take screenshot of direct access attempt
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/direct_addon_access.png' });
    
    console.log('🔍 Looking for entity selector fields...');
    
    // Look for entity picker components
    const entitySelectors = await page.$$eval('*', elements => {
      const selectors = [];
      elements.forEach(el => {
        if (el.tagName === 'HA-ENTITY-PICKER' || 
            el.tagName.includes('ENTITY') ||
            el.getAttribute('name')?.includes('camera') ||
            el.getAttribute('name')?.includes('todo') ||
            el.getAttribute('name')?.includes('entity') ||
            (el.tagName === 'INPUT' && (
              el.getAttribute('placeholder')?.includes('entity') ||
              el.getAttribute('name')?.includes('default_camera') ||
              el.getAttribute('name')?.includes('default_todo_list')
            ))) {
          selectors.push({
            tag: el.tagName,
            name: el.name || el.getAttribute('name'),
            id: el.id,
            className: el.className,
            placeholder: el.placeholder || el.getAttribute('placeholder'),
            value: el.value,
            outerHTML: el.outerHTML.substring(0, 200)
          });
        }
      });
      return selectors;
    });
    
    console.log('Entity selectors found:', JSON.stringify(entitySelectors, null, 2));
    
    if (entitySelectors.length > 0) {
      console.log('✅ Entity selectors found! Testing functionality...');
      
      // Test camera selector interaction
      try {
        const cameraSelector = await page.waitForSelector('[name*="camera"], ha-entity-picker[label*="camera"]', { timeout: 5000 });
        await cameraSelector.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/camera_selector_dropdown.png' });
        console.log('✅ Camera selector interaction successful');
      } catch (e) {
        console.log('❌ Camera selector interaction failed:', e.message);
      }
      
      // Test todo selector interaction  
      try {
        const todoSelector = await page.waitForSelector('[name*="todo"], ha-entity-picker[label*="todo"]', { timeout: 5000 });
        await todoSelector.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/todo_selector_dropdown.png' });
        console.log('✅ Todo selector interaction successful');
      } catch (e) {
        console.log('❌ Todo selector interaction failed:', e.message);
      }
      
    } else {
      console.log('❌ No entity selectors found');
    }
    
    // Take full page screenshot
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_config_full.png', fullPage: true });
    
    console.log('✅ Test completed');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test_error_complete.png' });
  }
  
  await browser.close();
})();