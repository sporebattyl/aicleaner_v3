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
    
    console.log('📱 Navigating to confirmed working addon configuration URL...');
    await page.goto('http://192.168.88.125:8123/hassio/addon/aicleaner_v3/config', { 
      waitUntil: 'domcontentloaded', 
      timeout: 60000 
    });
    
    // Wait for page to fully load
    await page.waitForTimeout(10000);
    
    // Take screenshot of the configuration page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test-results/final_config_page.png' });
    
    console.log('🔍 Looking for iframe content...');
    
    // Check if configuration is inside an iframe
    const iframes = await page.$$('iframe');
    console.log(`Found ${iframes.length} iframes on the page`);
    
    if (iframes.length > 0) {
      console.log('🖼️ Testing iframe-based configuration...');
      
      for (let i = 0; i < iframes.length; i++) {
        try {
          console.log(`Testing iframe ${i + 1}...`);
          
          const frame = await iframes[i].contentFrame();
          if (frame) {
            // Wait for iframe content to load
            await frame.waitForTimeout(5000);
            
            // Take screenshot of iframe content
            await frame.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/iframe_${i}_content.png` });
            
            // Look for form elements in iframe
            const iframeElements = await frame.$$eval('*', elements => {
              const formElements = [];
              elements.forEach(el => {
                if (el.tagName && (
                  el.tagName === 'INPUT' ||
                  el.tagName === 'SELECT' ||
                  el.tagName === 'TEXTAREA' ||
                  el.tagName.startsWith('HA-') ||
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
                    textContent: el.textContent?.substring(0, 100)
                  });
                }
              });
              return formElements;
            });
            
            console.log(`📋 Iframe ${i + 1} form elements:`, JSON.stringify(iframeElements, null, 2));
            
            // Look specifically for entity selectors in iframe
            const entitySelectors = await frame.$$eval('*', elements => {
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
            
            console.log(`🎯 Iframe ${i + 1} entity selectors:`, JSON.stringify(entitySelectors, null, 2));
            
            if (entitySelectors.length > 0) {
              console.log(`✅ Found entity selectors in iframe ${i + 1}! Testing functionality...`);
              
              // Test camera entity selector
              try {
                console.log('📷 Testing camera entity selector...');
                const cameraSelector = await frame.waitForSelector(
                  'ha-entity-picker[name*="camera"], input[name*="camera"], [name="default_camera"]',
                  { timeout: 5000 }
                );
                
                if (cameraSelector) {
                  await cameraSelector.click();
                  await frame.waitForTimeout(2000);
                  
                  // Look for dropdown options
                  const cameraOptions = await frame.$$eval('ha-list-item, mwc-list-item, option, .option', elements => 
                    elements.map(el => el.textContent?.trim()).filter(text => text && text.includes('camera')).slice(0, 10)
                  );
                  
                  console.log('📷 Camera options found:', cameraOptions);
                  
                  if (cameraOptions.length >= 5) {
                    console.log('✅ Camera entity selector working with sufficient options');
                  } else {
                    console.log(`⚠️ Camera entity selector found but only ${cameraOptions.length} options (expected 5+)`);
                  }
                  
                  await frame.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/camera_selector_iframe_${i}.png` });
                  
                  // Close dropdown
                  await frame.click('body');
                  await frame.waitForTimeout(1000);
                } else {
                  console.log('❌ Camera entity selector not found in iframe');
                }
              } catch (e) {
                console.log('❌ Camera entity selector test failed:', e.message);
              }
              
              // Test todo entity selector
              try {
                console.log('📝 Testing todo entity selector...');
                const todoSelector = await frame.waitForSelector(
                  'ha-entity-picker[name*="todo"], input[name*="todo"], [name="default_todo_list"]',
                  { timeout: 5000 }
                );
                
                if (todoSelector) {
                  await todoSelector.click();
                  await frame.waitForTimeout(2000);
                  
                  // Look for dropdown options
                  const todoOptions = await frame.$$eval('ha-list-item, mwc-list-item, option, .option', elements => 
                    elements.map(el => el.textContent?.trim()).filter(text => text && text.includes('todo')).slice(0, 10)
                  );
                  
                  console.log('📝 Todo options found:', todoOptions);
                  
                  if (todoOptions.length >= 2) {
                    console.log('✅ Todo entity selector working with sufficient options');
                  } else {
                    console.log(`⚠️ Todo entity selector found but only ${todoOptions.length} options (expected 2+)`);
                  }
                  
                  await frame.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/todo_selector_iframe_${i}.png` });
                  
                  // Close dropdown
                  await frame.click('body');
                  await frame.waitForTimeout(1000);
                } else {
                  console.log('❌ Todo entity selector not found in iframe');
                }
              } catch (e) {
                console.log('❌ Todo entity selector test failed:', e.message);
              }
              
              // Test zone configuration if available
              try {
                console.log('🗺️ Testing zone configuration...');
                const enableZonesToggle = await frame.waitForSelector(
                  'input[name="enable_zones"], ha-switch[name="enable_zones"], [name="enable_zones"]',
                  { timeout: 5000 }
                );
                
                if (enableZonesToggle) {
                  console.log('✅ Found enable_zones toggle');
                  await enableZonesToggle.click();
                  await frame.waitForTimeout(3000);
                  
                  // Look for zone entity selectors
                  const zoneSelectors = await frame.$$eval('*', elements => {
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
                  
                  await frame.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/zone_config_iframe_${i}.png` });
                } else {
                  console.log('❌ Enable zones toggle not found in iframe');
                }
              } catch (e) {
                console.log('❌ Zone configuration test failed:', e.message);
              }
              
            } else {
              console.log(`❌ No entity selectors found in iframe ${i + 1}`);
            }
          }
        } catch (e) {
          console.log(`❌ Error testing iframe ${i + 1}: ${e.message}`);
        }
      }
    } else {
      console.log('📋 No iframes found, testing main page content...');
      
      // Test main page for entity selectors (if not in iframe)
      const mainPageElements = await page.$$eval('*', elements => {
        const selectors = [];
        elements.forEach(el => {
          if (el.tagName === 'HA-ENTITY-PICKER' || 
              el.tagName.includes('ENTITY') ||
              el.getAttribute('name')?.includes('camera') ||
              el.getAttribute('name')?.includes('todo') ||
              el.getAttribute('name')?.includes('entity')) {
            selectors.push({
              tag: el.tagName,
              name: el.name || el.getAttribute('name'),
              outerHTML: el.outerHTML.substring(0, 200)
            });
          }
        });
        return selectors;
      });
      
      console.log('📋 Main page entity selectors:', JSON.stringify(mainPageElements, null, 2));
    }
    
    // Take final full page screenshot
    await page.screenshot({ 
      path: '/home/drewcifer/aicleaner_v3/test-results/final_validation_complete.png', 
      fullPage: true 
    });
    
    console.log('🎯 Final entity selector validation completed');
    
  } catch (error) {
    console.error('❌ Validation error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test-results/validation_error.png' });
  }
  
  await browser.close();
})();