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
    
    console.log('📱 Going directly to addon configuration...');
    // Navigate directly to the addon configuration URL
    await page.goto('http://192.168.88.125:8123/hassio/addon/local_aicleaner_v3/config', { 
      waitUntil: 'domcontentloaded', 
      timeout: 60000 
    });
    await page.waitForTimeout(5000);
    
    // Take screenshot of configuration page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_config_direct.png' });
    
    console.log('🔍 Looking for entity selector form fields...');
    
    // Look for all input elements and their types
    const formElements = await page.$$eval('*', elements => {
      const found = [];
      elements.forEach(el => {
        if (el.tagName && (
          el.tagName === 'HA-ENTITY-PICKER' ||
          el.tagName === 'HA-SELECT' ||
          el.tagName === 'SELECT' ||
          (el.tagName === 'INPUT' && el.type !== 'hidden') ||
          el.tagName === 'TEXTAREA' ||
          el.classList?.contains('entity-picker') ||
          el.getAttribute('name')?.includes('camera') ||
          el.getAttribute('name')?.includes('todo') ||
          el.getAttribute('name')?.includes('entity') ||
          el.getAttribute('placeholder')?.includes('entity')
        )) {
          found.push({
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
      return found;
    });
    
    console.log('Form elements found:', JSON.stringify(formElements, null, 2));
    
    console.log('🔍 Specifically looking for camera/todo selectors...');
    
    // Try to find and interact with camera selector
    try {
      console.log('Testing camera entity selector...');
      const cameraSelector = await page.waitForSelector(
        'ha-entity-picker[label*="camera"], ha-entity-picker[name*="camera"], input[name*="camera"], select[name*="camera"]',
        { timeout: 5000 }
      );
      
      if (cameraSelector) {
        console.log('✅ Found camera selector!');
        await cameraSelector.click();
        await page.waitForTimeout(2000);
        
        // Take screenshot with dropdown open
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/camera_selector_test.png' });
        
        // Try to see if dropdown options appear
        const options = await page.$$eval('ha-list-item, mwc-list-item, option, .option', elements => 
          elements.map(el => el.textContent?.trim()).filter(text => text)
        );
        console.log('Camera dropdown options:', options.slice(0, 10));
        
        // Click away to close dropdown
        await page.click('body');
        await page.waitForTimeout(1000);
      }
    } catch (e) {
      console.log('❌ Camera selector not found or not clickable:', e.message);
    }
    
    // Try to find and interact with todo selector
    try {
      console.log('Testing todo entity selector...');
      const todoSelector = await page.waitForSelector(
        'ha-entity-picker[label*="todo"], ha-entity-picker[name*="todo"], input[name*="todo"], select[name*="todo"]',
        { timeout: 5000 }
      );
      
      if (todoSelector) {
        console.log('✅ Found todo selector!');
        await todoSelector.click();
        await page.waitForTimeout(2000);
        
        // Take screenshot with dropdown open
        await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/todo_selector_test.png' });
        
        // Try to see if dropdown options appear
        const options = await page.$$eval('ha-list-item, mwc-list-item, option, .option', elements => 
          elements.map(el => el.textContent?.trim()).filter(text => text)
        );
        console.log('Todo dropdown options:', options.slice(0, 10));
      }
    } catch (e) {
      console.log('❌ Todo selector not found or not clickable:', e.message);
    }
    
    // Take final full page screenshot
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/config_final_test.png', fullPage: true });
    
    console.log('🔍 Checking for any configuration form...');
    
    // Look for any configuration form elements at all
    const anyConfigElements = await page.$$eval('form, .config, .configuration, [data-config]', elements => {
      return elements.map(el => ({
        tag: el.tagName,
        className: el.className,
        id: el.id,
        innerHTML: el.innerHTML.substring(0, 500)
      }));
    });
    
    console.log('Configuration containers found:', JSON.stringify(anyConfigElements, null, 2));
    
    console.log('✅ Entity selector testing completed!');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error('Stack:', error.stack);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/selector_test_error.png' });
  }
  
  await browser.close();
})();