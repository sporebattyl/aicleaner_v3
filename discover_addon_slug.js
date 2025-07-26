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
    
    console.log('📱 Navigating to Supervisor Add-ons...');
    await page.goto('http://192.168.88.125:8123/hassio/addon', { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    
    // Take screenshot of addons page
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test-results/supervisor_addons_list.png' });
    
    console.log('🔍 Discovering all installed addons...');
    
    // Get all addon cards and their URLs
    const addonInfo = await page.$$eval('*', elements => {
      const addons = [];
      elements.forEach(el => {
        // Look for links that contain addon URLs
        if (el.tagName === 'A' && el.href && el.href.includes('/hassio/addon/')) {
          const slug = el.href.split('/addon/')[1]?.split('/')[0];
          const text = el.textContent?.trim();
          if (slug && text && text.length > 0 && text.length < 100) {
            addons.push({
              name: text,
              slug: slug,
              url: el.href
            });
          }
        }
        
        // Also look for any element that mentions AICleaner or similar
        if (el.textContent && (
          el.textContent.toLowerCase().includes('aicleaner') ||
          el.textContent.toLowerCase().includes('ai cleaner') ||
          el.textContent.toLowerCase().includes('ai-cleaner')
        )) {
          addons.push({
            name: el.textContent.trim().substring(0, 100),
            element: el.tagName,
            className: el.className,
            potential_match: true
          });
        }
      });
      return addons;
    });
    
    console.log('📋 All discovered addons:', JSON.stringify(addonInfo, null, 2));
    
    // Filter for potential AICleaner matches
    const aicleanerMatches = addonInfo.filter(addon => 
      addon.name?.toLowerCase().includes('aicleaner') ||
      addon.name?.toLowerCase().includes('ai cleaner') ||
      addon.slug?.includes('aicleaner')
    );
    
    console.log('🎯 AICleaner matches found:', JSON.stringify(aicleanerMatches, null, 2));
    
    // Test systematic slug patterns
    const testSlugs = [
      'aicleaner_v3',
      'local_aicleaner_v3',
      '66f15fac_aicleaner_v3',
      'aicleaner',
      'ai_cleaner_v3',
      'ai-cleaner-v3'
    ];
    
    console.log('🧪 Testing systematic slug patterns...');
    
    for (const slug of testSlugs) {
      console.log(`Testing slug: ${slug}`);
      
      try {
        const testUrl = `http://192.168.88.125:8123/hassio/addon/${slug}`;
        await page.goto(testUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForTimeout(2000);
        
        // Check for error messages
        const errorElement = await page.$('text=/Error fetching addon info/');
        const notFoundElement = await page.$('text=/does not exist/');
        
        if (!errorElement && !notFoundElement) {
          console.log(`✅ SUCCESS: Found working slug: ${slug}`);
          console.log(`✅ Working URL: ${testUrl}`);
          
          // Take screenshot of successful access
          await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/working_slug_${slug}.png` });
          
          // Try to access configuration
          const configUrl = `${testUrl}/config`;
          await page.goto(configUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
          await page.waitForTimeout(3000);
          
          await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/config_${slug}.png` });
          
          console.log(`✅ Configuration URL: ${configUrl}`);
          break;
          
        } else {
          console.log(`❌ Failed: ${slug} - addon does not exist`);
        }
      } catch (e) {
        console.log(`❌ Error testing ${slug}: ${e.message}`);
      }
    }
    
    // Also try to find addons by searching the page source
    console.log('🔍 Searching page source for addon references...');
    const pageContent = await page.content();
    
    // Look for addon slug patterns in the page HTML
    const slugMatches = pageContent.match(/\/hassio\/addon\/([^"'\s]+)/g);
    if (slugMatches) {
      const uniqueSlugs = [...new Set(slugMatches.map(match => match.split('/addon/')[1]))];
      console.log('🔍 Found addon slugs in page source:', uniqueSlugs);
      
      // Test any that look like they might be AICleaner
      for (const foundSlug of uniqueSlugs) {
        if (foundSlug.toLowerCase().includes('ai') || foundSlug.toLowerCase().includes('clean')) {
          console.log(`🎯 Testing potential AICleaner slug from page source: ${foundSlug}`);
          
          try {
            const testUrl = `http://192.168.88.125:8123/hassio/addon/${foundSlug}`;
            await page.goto(testUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
            await page.waitForTimeout(2000);
            
            const errorElement = await page.$('text=/Error fetching addon info/');
            if (!errorElement) {
              console.log(`✅ FOUND IT: Working AICleaner slug from page source: ${foundSlug}`);
              await page.screenshot({ path: `/home/drewcifer/aicleaner_v3/test-results/found_slug_${foundSlug.replace(/[^a-zA-Z0-9]/g, '_')}.png` });
            }
          } catch (e) {
            console.log(`❌ Error testing found slug ${foundSlug}: ${e.message}`);
          }
        }
      }
    }
    
    console.log('🎯 Slug discovery completed');
    
  } catch (error) {
    console.error('❌ Discovery error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/test-results/discovery_error.png' });
  }
  
  await browser.close();
})();