#!/usr/bin/env python3
"""
AICleaner V3 Playwright Automation for Home Assistant
Automated testing of addon installation and configuration
"""

import asyncio
import json
import time
from playwright.async_api import async_playwright, Page, Browser
from typing import Dict, Any, Optional

class HomeAssistantPlaywrightTester:
    def __init__(self, ha_url: str = "http://localhost:8123"):
        self.ha_url = ha_url
        self.results: Dict[str, Any] = {
            "timestamp": time.time(),
            "ha_url": ha_url,
            "tests": {},
            "screenshots": []
        }
        
    async def take_screenshot(self, page: Page, name: str, description: str = ""):
        """Take a screenshot and save it"""
        screenshot_path = f"screenshot_{name}_{int(time.time())}.png"
        await page.screenshot(path=screenshot_path)
        self.results["screenshots"].append({
            "name": name,
            "path": screenshot_path,
            "description": description,
            "timestamp": time.time()
        })
        print(f"📸 Screenshot saved: {screenshot_path}")
        
    async def test_ha_accessibility(self, page: Page) -> bool:
        """Test if Home Assistant is accessible"""
        try:
            print(f"🔍 Testing HA accessibility at {self.ha_url}")
            response = await page.goto(self.ha_url, timeout=15000)
            
            # HA often returns 415 or other codes, but if we get a response, it's working
            # HTTP 415 specifically indicates HA is running but may need browser-like interaction
            if response and (response.status < 400 or response.status in [400, 401, 415]):
                await self.take_screenshot(page, "ha_homepage", "Home Assistant main page")
                self.results["tests"]["ha_accessibility"] = {
                    "status": "success",
                    "response_code": response.status,
                    "url": response.url
                }
                print("✅ Home Assistant is accessible")
                return True
            else:
                self.results["tests"]["ha_accessibility"] = {
                    "status": "error",
                    "response_code": response.status if response else None
                }
                print(f"❌ HA accessibility failed: {response.status if response else 'No response'}")
                return False
                
        except Exception as e:
            self.results["tests"]["ha_accessibility"] = {
                "status": "error",
                "error": str(e)
            }
            print(f"❌ HA accessibility error: {e}")
            return False
    
    async def check_for_setup_screen(self, page: Page) -> bool:
        """Check if we're on the initial setup screen"""
        try:
            # Wait for page to load and check for setup indicators
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Look for common setup screen elements
            setup_indicators = [
                "Welcome to Home Assistant",
                "Create your account",
                "Set up your Home Assistant",
                "text=Create Account",
                "text=Welcome",
                "text=Set up Home Assistant",
                "button:has-text('Create Account')",
                "input[name='name']",
                "input[name='username']"
            ]
            
            for indicator in setup_indicators:
                try:
                    element = await page.wait_for_selector(indicator, timeout=2000)
                    if element:
                        print(f"🔧 Found setup screen indicator: {indicator}")
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking setup screen: {e}")
            return False
    
    async def check_for_login_screen(self, page: Page) -> bool:
        """Check if we're on the login screen"""
        try:
            # Look for login screen elements
            login_indicators = [
                "text=Sign in",
                "input[type='password']",
                "[data-test-id='login']",
                "text=Username",
                "text=Password"
            ]
            
            for indicator in login_indicators:
                try:
                    element = await page.wait_for_selector(indicator, timeout=2000)
                    if element:
                        print(f"🔐 Found login screen indicator: {indicator}")
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            print(f"⚠️ Error checking login screen: {e}")
            return False
    
    async def login_to_ha(self, page: Page, username: str = "drewcifer", password: str = "Minds63qq!") -> bool:
        """Login to Home Assistant"""
        try:
            print("🔐 Logging into Home Assistant...")
            
            # Wait for page to be fully loaded
            await page.wait_for_load_state("networkidle", timeout=10000)
            await self.take_screenshot(page, "login_screen", "Login screen")
            
            # Fill username field first
            username_selectors = [
                "input[name='username']",
                "input[type='text']",
                "input[placeholder*='Username']"
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    username_field = await page.wait_for_selector(selector, timeout=3000)
                    if username_field:
                        await username_field.clear()  # Clear any existing content
                        await username_field.fill(username)
                        print("✅ Username filled")
                        username_filled = True
                        break
                except:
                    continue
            
            if not username_filled:
                print("❌ Could not find username field")
                return False
            
            # Fill password field
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[placeholder*='Password']"
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    password_field = await page.wait_for_selector(selector, timeout=3000)
                    if password_field:
                        await password_field.clear()  # Clear any existing content
                        await password_field.fill(password)
                        print("✅ Password filled")
                        password_filled = True
                        break
                except:
                    continue
            
            if not password_filled:
                print("❌ Could not find password field")
                return False
            
            # Wait a moment for the form to be fully ready
            await page.wait_for_timeout(1000)
            
            # Click login button
            login_selectors = [
                "button:has-text('LOG IN')",
                "text=LOG IN",
                "[role='button']:has-text('LOG IN')",
                "button:has-text('Sign in')",
                "button:has-text('Login')",
                "button[type='submit']",
                "input[type='submit']",
                ".mdc-button:has-text('LOG IN')"
            ]
            
            login_clicked = False
            for selector in login_selectors:
                try:
                    login_button = await page.wait_for_selector(selector, timeout=3000)
                    if login_button:
                        print(f"🔑 Clicking login button: {selector}")
                        await login_button.click()
                        login_clicked = True
                        break
                except:
                    continue
            
            if not login_clicked:
                print("❌ Could not find login button")
                return False
            
            # Wait for login to complete
            await page.wait_for_load_state("networkidle", timeout=15000)
            await self.take_screenshot(page, "after_login", "After login attempt")
            
            # Check if login was successful by looking for main HA interface
            main_interface_indicators = [
                "text=Overview",
                "text=Settings", 
                "text=Configuration",
                "[data-test-id='sidebar']",
                "ha-sidebar",
                "text=Developer Tools"
            ]
            
            login_successful = False
            for indicator in main_interface_indicators:
                try:
                    element = await page.wait_for_selector(indicator, timeout=5000)
                    if element:
                        print(f"✅ Login successful - found: {indicator}")
                        login_successful = True
                        break
                except:
                    continue
            
            if login_successful:
                self.results["tests"]["ha_login"] = {
                    "status": "success",
                    "message": "Successfully logged into Home Assistant"
                }
                return True
            else:
                print("❌ Login may have failed - could not find main interface")
                self.results["tests"]["ha_login"] = {
                    "status": "error",
                    "message": "Login failed or could not verify main interface"
                }
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            await self.take_screenshot(page, "login_error", f"Login error: {e}")
            self.results["tests"]["ha_login"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    async def complete_ha_setup(self, page: Page) -> bool:
        """Complete Home Assistant initial setup automatically"""
        try:
            print("🏗️ Starting automated Home Assistant setup...")
            
            # Wait for initial page load
            await page.wait_for_load_state("networkidle", timeout=15000)
            await self.take_screenshot(page, "initial_setup_screen", "Initial HA setup screen")
            
            # Step 1: Look for the welcome/setup screen
            setup_selectors = [
                "button:has-text('Create Account')",
                "button:has-text('Get Started')", 
                "button:has-text('Set up Home Assistant')",
                "button:has-text('Continue')",
                "[data-test-id='onboard-create-account']"
            ]
            
            setup_button = None
            for selector in setup_selectors:
                try:
                    setup_button = await page.wait_for_selector(selector, timeout=3000)
                    if setup_button:
                        print(f"✅ Found setup button: {selector}")
                        break
                except:
                    continue
            
            if setup_button:
                await setup_button.click()
                await page.wait_for_load_state("networkidle", timeout=10000)
                await self.take_screenshot(page, "after_setup_click", "After clicking setup button")
            
            # Step 2: Fill in user account details
            print("👤 Creating admin user account...")
            
            # Try different form field patterns HA might use
            user_form_attempts = [
                # Modern HA setup forms
                {
                    "name": "input[name='name']",
                    "username": "input[name='username']", 
                    "password": "input[name='password']",
                    "confirm": "input[name='password_confirm']"
                },
                # Alternative patterns
                {
                    "name": "input[placeholder*='Name']",
                    "username": "input[placeholder*='Username']",
                    "password": "input[placeholder*='Password']", 
                    "confirm": "input[placeholder*='Confirm']"
                },
                # Generic form inputs
                {
                    "name": "input[type='text']:first-of-type",
                    "username": "input[type='text']:nth-of-type(2)",
                    "password": "input[type='password']:first-of-type",
                    "confirm": "input[type='password']:nth-of-type(2)"
                }
            ]
            
            user_created = False
            for attempt, form_fields in enumerate(user_form_attempts, 1):
                try:
                    print(f"   Attempting user form pattern {attempt}...")
                    
                    # Fill name field
                    name_field = await page.wait_for_selector(form_fields["name"], timeout=3000)
                    if name_field:
                        await name_field.fill("Test Admin")
                        print("   ✅ Filled name field")
                    
                    # Fill username field  
                    username_field = await page.wait_for_selector(form_fields["username"], timeout=3000)
                    if username_field:
                        await username_field.fill("admin")
                        print("   ✅ Filled username field")
                    
                    # Fill password field
                    password_field = await page.wait_for_selector(form_fields["password"], timeout=3000)
                    if password_field:
                        await password_field.fill("testpassword123")
                        print("   ✅ Filled password field")
                    
                    # Fill confirm password field
                    confirm_field = await page.wait_for_selector(form_fields["confirm"], timeout=3000)
                    if confirm_field:
                        await confirm_field.fill("testpassword123")
                        print("   ✅ Filled password confirmation field")
                    
                    user_created = True
                    break
                    
                except Exception as e:
                    print(f"   ❌ Form pattern {attempt} failed: {e}")
                    continue
            
            if not user_created:
                print("❌ Could not fill user form fields")
                await self.take_screenshot(page, "user_form_failed", "User form filling failed")
                return False
            
            # Step 3: Submit the user creation form
            submit_selectors = [
                "button:has-text('Create Account')",
                "button:has-text('Next')",
                "button:has-text('Continue')",
                "button[type='submit']",
                "input[type='submit']"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(selector, timeout=3000)
                    if submit_button:
                        print(f"📝 Submitting user form with: {selector}")
                        await submit_button.click()
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        await self.take_screenshot(page, "after_user_submit", "After submitting user form")
                        break
                except:
                    continue
            
            # Step 4: Skip through additional setup steps
            print("⏭️ Skipping through additional setup steps...")
            
            max_setup_steps = 5
            for step in range(max_setup_steps):
                try:
                    # Look for skip/continue buttons
                    skip_selectors = [
                        "button:has-text('Skip')",
                        "button:has-text('Next')",
                        "button:has-text('Continue')",
                        "button:has-text('Finish')",
                        "button:has-text('Done')",
                        "text=Skip this step"
                    ]
                    
                    found_skip = False
                    for selector in skip_selectors:
                        try:
                            skip_button = await page.wait_for_selector(selector, timeout=3000)
                            if skip_button:
                                print(f"   Step {step + 1}: Clicking {selector}")
                                await skip_button.click()
                                await page.wait_for_load_state("networkidle", timeout=8000)
                                found_skip = True
                                break
                        except:
                            continue
                    
                    if not found_skip:
                        print(f"   Step {step + 1}: No skip button found, setup may be complete")
                        break
                        
                except Exception as e:
                    print(f"   Step {step + 1} error: {e}")
                    break
            
            # Step 5: Verify we reached the main HA interface
            await page.wait_for_load_state("networkidle", timeout=15000)
            await self.take_screenshot(page, "setup_complete", "Setup completed - main interface")
            
            # Look for main HA interface indicators
            main_interface_indicators = [
                "text=Overview",
                "text=Settings", 
                "text=Configuration",
                "[data-test-id='sidebar']",
                "ha-sidebar",
                "text=Developer Tools"
            ]
            
            setup_successful = False
            for indicator in main_interface_indicators:
                try:
                    element = await page.wait_for_selector(indicator, timeout=5000)
                    if element:
                        print(f"✅ Setup completed successfully - found: {indicator}")
                        setup_successful = True
                        break
                except:
                    continue
            
            if setup_successful:
                self.results["tests"]["ha_setup"] = {
                    "status": "success",
                    "message": "Automated HA setup completed successfully"
                }
                print("🎉 Home Assistant setup completed successfully!")
                return True
            else:
                print("❌ Setup may not have completed successfully")
                await self.take_screenshot(page, "setup_uncertain", "Setup completion uncertain")
                self.results["tests"]["ha_setup"] = {
                    "status": "warning", 
                    "message": "Setup completed but could not verify main interface"
                }
                return False
                
        except Exception as e:
            print(f"❌ Error during HA setup: {e}")
            await self.take_screenshot(page, "setup_error", f"Setup error: {e}")
            self.results["tests"]["ha_setup"] = {
                "status": "error",
                "error": str(e)
            }
            return False
    
    async def navigate_to_addons(self, page: Page) -> bool:
        """Navigate to the Add-ons section"""
        try:
            print("🧭 Navigating to Add-ons section...")
            
            # Wait for the page to be fully loaded
            await page.wait_for_load_state("networkidle", timeout=15000)
            await self.take_screenshot(page, "before_navigation", "Before navigating to add-ons")
            
            # Try multiple methods to get to add-ons
            navigation_attempts = [
                # Method 1: Direct URL
                lambda: page.goto(f"{self.ha_url}/hassio/addon-store"),
                
                # Method 2: Via Settings menu
                lambda: self._navigate_via_settings(page),
                
                # Method 3: Via sidebar
                lambda: self._navigate_via_sidebar(page)
            ]
            
            for i, attempt in enumerate(navigation_attempts):
                try:
                    print(f"   Attempting navigation method {i+1}...")
                    await attempt()
                    
                    # Check if we successfully reached add-ons
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    
                    # Look for add-on store indicators
                    addon_indicators = [
                        "text=Add-on Store",
                        "text=Local add-ons",
                        "text=AICleaner",
                        "[data-test-id='addon-store']"
                    ]
                    
                    for indicator in addon_indicators:
                        try:
                            element = await page.wait_for_selector(indicator, timeout=3000)
                            if element:
                                print(f"✅ Successfully navigated to add-ons: {indicator}")
                                await self.take_screenshot(page, "addon_store", "Add-on store page")
                                return True
                        except:
                            continue
                            
                except Exception as e:
                    print(f"   Method {i+1} failed: {e}")
                    continue
            
            print("❌ Failed to navigate to add-ons section")
            await self.take_screenshot(page, "navigation_failed", "Failed to reach add-ons")
            return False
            
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            await self.take_screenshot(page, "navigation_error", f"Navigation error: {e}")
            return False
    
    async def _navigate_via_settings(self, page: Page):
        """Navigate via Settings menu"""
        # Look for Settings menu item
        settings_selectors = [
            "text=Settings",
            "[data-test-id='settings']",
            "a[href*='config']"
        ]
        
        for selector in settings_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state("networkidle", timeout=5000)
                
                # Look for Add-ons in settings
                await page.click("text=Add-ons", timeout=5000)
                return
            except:
                continue
                
        raise Exception("Could not find Settings menu")
    
    async def _navigate_via_sidebar(self, page: Page):
        """Navigate via sidebar"""
        # Look for sidebar add-ons link
        sidebar_selectors = [
            "text=Supervisor",
            "a[href*='hassio']",
            "text=Add-ons"
        ]
        
        for selector in sidebar_selectors:
            try:
                await page.click(selector, timeout=3000)
                await page.wait_for_load_state("networkidle", timeout=5000)
                return
            except:
                continue
                
        raise Exception("Could not find sidebar navigation")
    
    async def find_aicleaner_addon(self, page: Page) -> bool:
        """Look for AICleaner V3 addon in the store"""
        try:
            print("🔍 Looking for AICleaner V3 addon...")
            
            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Look for local add-ons section first
            local_addon_selectors = [
                "text=Local add-ons",
                "text=Local Add-ons",
                "[data-test-id='local-addons']"
            ]
            
            for selector in local_addon_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await page.wait_for_load_state("networkidle", timeout=5000)
                    break
                except:
                    continue
            
            # Look for AICleaner addon
            aicleaner_selectors = [
                "text=AICleaner V3",
                "text=AICleaner",
                "[data-addon-slug='aicleaner_v3']",
                "text*=aicleaner"
            ]
            
            for selector in aicleaner_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        print("✅ Found AICleaner V3 addon!")
                        await self.take_screenshot(page, "addon_found", "AICleaner addon found")
                        self.results["tests"]["addon_discovery"] = {"status": "success"}
                        return True
                except:
                    continue
            
            print("❌ AICleaner V3 addon not found")
            await self.take_screenshot(page, "addon_not_found", "AICleaner addon not found")
            self.results["tests"]["addon_discovery"] = {"status": "error", "message": "Addon not found"}
            return False
            
        except Exception as e:
            print(f"❌ Error searching for addon: {e}")
            await self.take_screenshot(page, "addon_search_error", f"Addon search error: {e}")
            self.results["tests"]["addon_discovery"] = {"status": "error", "error": str(e)}
            return False
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive Playwright testing"""
        print("🚀 Starting AICleaner V3 Playwright Testing...")
        print(f"🎯 Target: {self.ha_url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=1000)  # Visible mode for debugging
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Test 1: HA Accessibility
                ha_accessible = await self.test_ha_accessibility(page)
                if not ha_accessible:
                    return self.results
                
                # Test 2: Check what screen we're on and handle automatically
                is_login = await self.check_for_login_screen(page)
                is_setup = await self.check_for_setup_screen(page)
                
                # Login screen takes priority over setup screen detection
                if is_login:
                    print("ℹ️ Home Assistant is on login screen")
                    print("🔐 Attempting automated login...")
                    self.results["tests"]["screen_detection"] = {
                        "status": "info", 
                        "screen_type": "login",
                        "message": "Login screen detected - attempting automated login"
                    }
                    
                    # Test 3: Login to HA
                    login_success = await self.login_to_ha(page)
                    if not login_success:
                        print("❌ Login failed")
                        return self.results
                    
                elif is_setup:
                    print("🔧 Home Assistant is on initial setup screen")
                    print("🤖 Starting automated setup process...")
                    self.results["tests"]["screen_detection"] = {
                        "status": "info",
                        "screen_type": "setup",
                        "message": "Automated setup initiated"
                    }
                    
                    # Test 3: Complete automated setup
                    setup_success = await self.complete_ha_setup(page)
                    if not setup_success:
                        print("❌ Automated setup failed")
                        return self.results
                else:
                    print("ℹ️ Home Assistant appears to be already set up")
                    self.results["tests"]["screen_detection"] = {
                        "status": "info",
                        "screen_type": "main_interface", 
                        "message": "Already at main interface"
                    }
                
                # Test 4: Navigate to Add-ons (whether setup was completed or already done)
                print("🧭 Navigating to Add-ons section...")
                navigation_success = await self.navigate_to_addons(page)
                self.results["tests"]["addon_navigation"] = {
                    "status": "success" if navigation_success else "error"
                }
                
                if navigation_success:
                    # Test 5: Find AICleaner addon
                    await self.find_aicleaner_addon(page)
                else:
                    print("❌ Could not navigate to Add-ons section")
                    return self.results
                
                await self.take_screenshot(page, "final_state", "Final test state")
                
            except Exception as e:
                print(f"❌ Test execution error: {e}")
                await self.take_screenshot(page, "execution_error", f"Test execution error: {e}")
                self.results["tests"]["execution"] = {"status": "error", "error": str(e)}
            
            finally:
                await browser.close()
        
        return self.results

async def main():
    """Main testing function"""
    print("AICleaner V3 Playwright Home Assistant Tester")
    print("=" * 50)
    
    # Get HA URL from command line or use default
    import sys
    ha_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8123"
    
    print(f"Testing Home Assistant at: {ha_url}")
    
    tester = HomeAssistantPlaywrightTester(ha_url)
    results = await tester.run_comprehensive_test()
    
    # Save results
    with open("playwright_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n📊 Test Summary:")
    print(f"Results saved to: playwright_test_results.json")
    print(f"Screenshots taken: {len(results['screenshots'])}")
    
    # Print test results summary
    for test_name, test_result in results["tests"].items():
        status = test_result.get("status", "unknown")
        emoji = "✅" if status == "success" else "ℹ️" if status == "info" else "❌"
        print(f"{emoji} {test_name}: {status}")

if __name__ == "__main__":
    asyncio.run(main())