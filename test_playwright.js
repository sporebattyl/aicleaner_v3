const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  
  const context = await browser.newContext({
    ignoreHTTPSErrors: true
  });
  
  const page = await context.newPage();
  
  try {
    console.log('🔌 Navigating to Home Assistant...');
    await page.goto('http://192.168.88.125:8123', { waitUntil: 'networkidle' });
    
    // Handle login
    console.log('🔐 Attempting login...');
    await page.fill('input[name="username"]', 'drewcifer');
    await page.fill('input[name="password"]', 'Minds63qq!');
    await page.click('button[type="submit"]');
    
    // Wait for dashboard to load
    await page.waitForTimeout(3000);
    
    console.log('📱 Navigating to Supervisor...');
    // Navigate to supervisor/addon store
    await page.goto('http://192.168.88.125:8123/hassio/dashboard', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    console.log('🏪 Taking screenshot...');
    
    // Take a screenshot to see current state
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/supervisor_dashboard.png' });
    console.log('📸 Screenshot saved');
    
    console.log('✅ Successfully navigated to supervisor');
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    await page.screenshot({ path: '/home/drewcifer/aicleaner_v3/addon_test_error.png' });
  }
  
  await browser.close();
})();