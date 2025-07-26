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
    
    console.log('⏳ Waiting for repository updates to propagate...');
    await page.waitForTimeout(10000); // Give time for HA to reload repository
    
    // Test multiple addon access URLs
    const testUrls = [
      'http://192.168.88.125:8123/hassio/addon/aicleaner_v3/config',
      'http://192.168.88.125:8123/hassio/addon/local_aicleaner_v3/config',
      'http://192.168.88.125:8123/hassio/addon/66f15fac_aicleaner_v3/config' // Hash-based slug
    ];
    
    let configAccessible = false;
    let workingUrl = '';
    
    for (const url of testUrls) {
      console.log(`🧪 Testing URL: ${url}`);
      
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(3000);
        
        // Check if we get an error message
        const errorElement = await page.$('text=/Error fetching addon info/');
        const notFoundElement = await page.$('text=/does not exist/');
        
        if (!errorElement && !notFoundElement) {
          console.log(`✅ Successfully accessed: ${url}`);
          configAccessible = true;
          workingUrl = url;
          
          // Take screenshot of successful access
          await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/config_access_success_${Date.now()}.png` });
          break;
        } else {
          console.log(`❌ Failed to access: ${url}`);
          await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/config_access_failed_${Date.now()}.png` });
        }
      } catch (e) {
        console.log(`❌ Error accessing ${url}: ${e.message}`);
      }
    }
    
    if (!configAccessible) {
      console.log('🔍 Trying navigation through Supervisor interface...');
      
      // Navigate through Supervisor
      await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'domcontentloaded', timeout: 60000 });
      await page.waitForTimeout(3000);
      
      // Try to find Add-ons section
      try {
        await page.click('text=Add-ons, a[href*="/hassio/addon"]');
        await page.waitForTimeout(3000);
        
        // Look for AICleaner addon
        await page.click('text=/.*AICleaner.*/, text=/.*AI Cleaner.*/');
        await page.waitForTimeout(3000);
        
        // Click Configuration tab
        await page.click('button:has-text("Configuration"), [role="tab"]:has-text("Configuration")');
        await page.waitForTimeout(3000);
        
        configAccessible = true;
        workingUrl = 'Navigation through Supervisor';
        
        console.log('✅ Successfully accessed configuration through Supervisor navigation');
        await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/config_via_supervisor_${Date.now()}.png` });
        
      } catch (e) {
        console.log(`❌ Failed to navigate through Supervisor: ${e.message}`);
      }
    }
    
    if (configAccessible) {
      console.log(`🎉 Configuration accessible via: ${workingUrl}`);
      
      console.log('🔍 Analyzing configuration form...');
      
      // Look for all form elements
      const allFormElements = await page.$$eval('*', elements => {
        const formElements = [];
        elements.forEach(el => {
          if (el.tagName && (
            el.tagName === 'INPUT' ||
            el.tagName === 'SELECT' ||
            el.tagName === 'TEXTAREA' ||
            el.tagName.startsWith('HA-') ||
            el.classList?.contains('entity-picker') ||
            el.getAttribute('name') ||
            el.getAttribute('placeholder')
          )) {
            formElements.push({
              tag: el.tagName,
              type: el.type,
              name: el.name || el.getAttribute('name'),
              id: el.id,
              className: el.className,
              placeholder: el.placeholder || el.getAttribute('placeholder'),
              value: el.value,
              visible: el.offsetParent !== null,
              outerHTML: el.outerHTML.substring(0, 300)
            });
          }
        });
        return formElements;
      });
      
      console.log('📋 All form elements found:', JSON.stringify(allFormElements, null, 2));
      
      // Specifically look for entity selectors
      const entitySelectors = await page.$$eval('*', elements => {
        const selectors = [];
        elements.forEach(el => {
          if (el.tagName === 'HA-ENTITY-PICKER' || 
              el.tagName.includes('ENTITY') ||
              el.getAttribute('name')?.includes('camera') ||
              el.getAttribute('name')?.includes('todo') ||
              el.getAttribute('name')?.includes('entity') ||
              el.getAttribute('placeholder')?.includes('entity') ||
              (el.tagName === 'INPUT' && (
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
              visible: el.offsetParent !== null,
              outerHTML: el.outerHTML.substring(0, 300)
            });
          }
        });
        return selectors;
      });
      
      console.log('🎯 Entity selectors found:', JSON.stringify(entitySelectors, null, 2));
      
      if (entitySelectors.length > 0) {
        console.log('✅ Entity selectors found! Testing functionality...');
        
        // Test camera entity selector
        try {
          console.log('📷 Testing camera entity selector...');
          const cameraSelector = await page.waitForSelector(
            'ha-entity-picker[name*="camera"], ha-entity-picker[placeholder*="camera"], input[name*="camera"], [name="default_camera"]',
            { timeout: 5000 }
          );
          
          if (cameraSelector) {
            await cameraSelector.click();
            await page.waitForTimeout(2000);
            
            // Look for dropdown options
            const cameraOptions = await page.$$eval('ha-list-item, mwc-list-item, option', elements => 
              elements.map(el => el.textContent?.trim()).filter(text => text && text.includes('camera')).slice(0, 10)
            );
            
            console.log('📷 Camera options found:', cameraOptions);
            
            if (cameraOptions.length >= 5) {
              console.log('✅ Camera entity selector working with sufficient options');
            } else {
              console.log(`⚠️ Camera entity selector found but only ${cameraOptions.length} options (expected 5+)`);
            }
            
            await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/camera_selector_${Date.now()}.png` });
            
            // Close dropdown
            await page.click('body');
            await page.waitForTimeout(1000);
          }
        } catch (e) {
          console.log('❌ Camera entity selector test failed:', e.message);
        }
        
        // Test todo entity selector
        try {
          console.log('📝 Testing todo entity selector...');
          const todoSelector = await page.waitForSelector(
            'ha-entity-picker[name*="todo"], ha-entity-picker[placeholder*="todo"], input[name*="todo"], [name="default_todo_list"]',
            { timeout: 5000 }
          );
          
          if (todoSelector) {
            await todoSelector.click();
            await page.waitForTimeout(2000);
            
            // Look for dropdown options
            const todoOptions = await page.$$eval('ha-list-item, mwc-list-item, option', elements => 
              elements.map(el => el.textContent?.trim()).filter(text => text && text.includes('todo')).slice(0, 10)
            );
            
            console.log('📝 Todo options found:', todoOptions);
            
            if (todoOptions.length >= 2) {
              console.log('✅ Todo entity selector working with sufficient options');
            } else {
              console.log(`⚠️ Todo entity selector found but only ${todoOptions.length} options (expected 2+)`);
            }
            
            await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/todo_selector_${Date.now()}.png` });
            
            // Close dropdown
            await page.click('body');
            await page.waitForTimeout(1000);
          }
        } catch (e) {
          console.log('❌ Todo entity selector test failed:', e.message);
        }
        
        // Test advanced zone configuration
        try {
          console.log('🗺️ Testing zone configuration...');
          const enableZonesToggle = await page.waitForSelector(
            'input[name="enable_zones"], ha-switch[name="enable_zones"], [name="enable_zones"]',
            { timeout: 5000 }
          );
          
          if (enableZonesToggle) {
            console.log('✅ Found enable_zones toggle');
            await enableZonesToggle.click();
            await page.waitForTimeout(2000);
            
            // Look for zone entity selectors
            const zoneSelectors = await page.$$eval('*', elements => {
              const selectors = [];
              elements.forEach(el => {
                if (el.getAttribute('name')?.includes('camera_entity') ||
                    el.getAttribute('name')?.includes('todo_list_entity')) {
                  selectors.push({
                    name: el.name || el.getAttribute('name'),
                    tag: el.tagName,
                    visible: el.offsetParent !== null
                  });
                }
              });
              return selectors;
            });
            
            console.log('🗺️ Zone entity selectors found:', zoneSelectors);
            
            if (zoneSelectors.length > 0) {
              console.log('✅ Zone configuration entity selectors found');
            } else {
              console.log('❌ Zone configuration entity selectors not found');
            }
            
            await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/zone_config_${Date.now()}.png` });
          }
        } catch (e) {
          console.log('❌ Zone configuration test failed:', e.message);
        }
        
      } else {
        console.log('❌ No entity selectors found in configuration');
      }
      
      // Take final full page screenshot
      await page.screenshot({ 
        path: `/home/drewcifer/aicleaner_v3/test-results/final_config_validation_${Date.now()}.png`, 
        fullPage: true 
      });
      
    } else {
      console.log('❌ Could not access addon configuration interface');
    }
    
    console.log('🎯 Validation test completed');
    
  } catch (error) {
    console.error('❌ Test error:', error.message);
    await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/test_error_${Date.now()}.png` });
  }
  
  await browser.close();
})();