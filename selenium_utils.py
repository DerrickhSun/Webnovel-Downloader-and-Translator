"""
All Selenium-related scraping utilities, refactored from web_scraper.py
"""
import time
import json
import random
from typing import List, Optional, Union
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from web_scraper import session_manager

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available. Install with: pip install selenium")

# Try to import undetected-chromedriver for better anti-detection
try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    print("Undetected ChromeDriver not available. Install with: pip install undetected-chromedriver")

# The following global variables must be imported from web_scraper.py:
# - CONFIRMED_HEADERS
# - session_manager

# The following functions are refactored from web_scraper.py:
# - fetch_with_exact_headers

# --- fetch_with_exact_headers ---
def fetch_with_exact_headers(url: str, CONFIRMED_HEADERS: dict, main_id: str = None, main_class: str = None, 
                            wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches content using undetected-chromedriver with exact headers.
    This leverages undetected-chromedriver's built-in anti-detection while ensuring exact header matching.
    """
    if not UNDETECTED_AVAILABLE:
        raise ImportError("Undetected ChromeDriver is not available. Install with: pip install undetected-chromedriver")
    
    if debug:
        print(f"\n=== Fetching with Exact Headers (Undetected Chrome) ===")
        print(f"URL: {url}")
        print("Using undetected-chromedriver with exact headers")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if main_id is None and main_class is None:
        raise ValueError("Either main_id or main_class must be provided")
    if main_id is not None and main_class is not None:
        raise ValueError("Only one of main_id or main_class should be provided")

    driver = None
    try:
        # Set up undetected Chrome options
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Set the exact user agent from confirmed headers
        options.add_argument(f"--user-agent={CONFIRMED_HEADERS['User-Agent']}")
        
        # Add language preference
        options.add_argument(f"--accept-language={CONFIRMED_HEADERS['Accept-Language']}")
        
        # Additional undetected-chromedriver specific options
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Disable various Chrome features that might be detected
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # We'll re-enable this after setup
        
        if debug:
            print("Setting up undetected Chrome driver with exact headers...")
            print(f"User-Agent: {CONFIRMED_HEADERS['User-Agent']}")
            print(f"Accept-Language: {CONFIRMED_HEADERS['Accept-Language']}")
        
        # Initialize the undetected driver
        driver = uc.Chrome(options=options)
        
        # Re-enable JavaScript after driver initialization
        driver.execute_script("""
            // Re-enable JavaScript execution
            document.documentElement.style.pointerEvents = 'auto';
        """)
        
        # Add random delay to simulate human behavior
        if debug:
            print("Adding random delay to simulate human behavior...")
        time.sleep(random.uniform(1, 3))
        
        # Execute script to override fetch and XMLHttpRequest with exact headers
        driver.execute_script(f"""
            // Override fetch to add exact headers
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {{
                options = options || {{}};
                options.headers = options.headers || {{}};
                
                // Add ALL confirmed headers
                const confirmedHeaders = {json.dumps(CONFIRMED_HEADERS)};
                for (const [key, value] of Object.entries(confirmedHeaders)) {{
                    options.headers[key] = value;
                }}
                
                // Log what headers are being sent
                console.log('Fetch request headers:', options.headers);
                
                return originalFetch(url, options);
            }};
            
            // Override XMLHttpRequest to add exact headers
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
            
            XMLHttpRequest.prototype.open = function(method, url, ...args) {{
                this._url = url;
                this._method = method;
                this._headers = {{}};
                return originalOpen.call(this, method, url, ...args);
            }};
            
            XMLHttpRequest.prototype.setRequestHeader = function(header, value) {{
                this._headers[header] = value;
                return originalSetRequestHeader.call(this, header, value);
            }};
            
            // Override send to add missing headers
            const originalSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.send = function(data) {{
                const confirmedHeaders = {json.dumps(CONFIRMED_HEADERS)};
                for (const [key, value] of Object.entries(confirmedHeaders)) {{
                    if (!this._headers[key]) {{
                        originalSetRequestHeader.call(this, key, value);
                    }}
                }}
                
                // Log what headers are being sent
                console.log('XMLHttpRequest headers:', this._headers);
                
                return originalSend.call(this, data);
            }};
            
            // Override navigator properties to avoid detection
            Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
            Object.defineProperty(navigator, 'plugins', {{get: () => [1, 2, 3, 4, 5]}});
            Object.defineProperty(navigator, 'languages', {{get: () => ['en-US', 'en']}});
            
            // Override Chrome-specific properties
            Object.defineProperty(navigator, 'chrome', {{
                get: () => ({{
                    runtime: {{}},
                    loadTimes: function() {{}},
                    csi: function() {{}},
                    app: {{}}
                }})
            }});
            
            // Set referer
            Object.defineProperty(document, 'referrer', {{
                get: function() {{ return '{CONFIRMED_HEADERS.get('Referer', '')}'; }}
            }});
            
            // Log the confirmed headers for verification
            console.log('Confirmed headers loaded:', {json.dumps(CONFIRMED_HEADERS)});
        """)
        
        if debug:
            print("\n=== Header Verification ===")
            print("Confirmed headers that should be sent:")
            for key, value in CONFIRMED_HEADERS.items():
                print(f"  {key}: {value}")
            print("=== End Header Verification ===\n")
        
        # Run comprehensive cookie debugging
        debug_selenium_cookies(driver, url, debug)
        
        if debug:
            print("Navigating to URL with cookies set...")
        
        # Add random delay before final navigation
        time.sleep(random.uniform(1, 3))
        
        # Now navigate to the actual URL with cookies set
        driver.get(url)
        
        # Add random delay after page load
        time.sleep(random.uniform(2, 5))
        
        # Simulate human behavior to avoid detection
        simulate_human_behavior(driver, debug)
        
        # Debug: Check what we received
        if debug:
            print("\n=== Selenium Response Debug ===")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            print(f"Page source length: {len(driver.page_source)}")
            
            # Check if we got redirected
            if driver.current_url != url:
                print(f"⚠️  Redirected from {url} to {driver.current_url}")
            
            # Show first 500 characters of page source
            page_source = driver.page_source
            print(f"\nFirst 500 characters of page source:")
            print("=" * 50)
            print(page_source[:500])
            print("=" * 50)
            
            # Check for common error indicators
            error_indicators = ['captcha', 'blocked', 'forbidden', 'access denied', 'cloudflare', 'security check']
            page_lower = page_source.lower()
            found_errors = []
            for indicator in error_indicators:
                if indicator in page_lower:
                    found_errors.append(indicator)
            
            if found_errors:
                print(f"⚠️  Found potential error indicators: {found_errors}")
            
            # Check for main elements in the raw HTML
            if main_id:
                if f'id="{main_id}"' in page_source:
                    print(f"✅ Found main element with id '{main_id}' in HTML")
                else:
                    print(f"❌ Main element with id '{main_id}' NOT found in HTML")
            
            if main_class:
                if f'class="{main_class}"' in page_source or f'class=\'{main_class}\'' in page_source:
                    print(f"✅ Found main element with class '{main_class}' in HTML")
                else:
                    print(f"❌ Main element with class '{main_class}' NOT found in HTML")
            
            print("=== End Selenium Response Debug ===\n")
        
        # Save full page source to file for detailed inspection
        if debug:
            try:
                timestamp = int(time.time())
                filename = f"undetected_debug_{timestamp}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print(f"💾 Full page source saved to: {filename}")
                
                # Verify cookies were set correctly
                print("Verifying cookies in browser...")
                browser_cookies = driver.get_cookies()
                print(f"Browser has {len(browser_cookies)} cookies:")
                for cookie in browser_cookies:
                    print(f"  {cookie['name']}: {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}")
                
                # Compare with confirmed headers cookies
                if 'Cookie' in CONFIRMED_HEADERS:
                    print("\nComparing with confirmed headers cookies:")
                    confirmed_cookies = CONFIRMED_HEADERS['Cookie'].split('; ')
                    for cookie in confirmed_cookies:
                        if '=' in cookie:
                            name, value = cookie.split('=', 1)
                            name = name.strip()
                            value = value.strip()
                            # Check if this cookie exists in browser
                            found = False
                            for browser_cookie in browser_cookies:
                                if browser_cookie['name'] == name:
                                    if browser_cookie['value'] == value:
                                        print(f"  ✅ {name}: matches")
                                    else:
                                        print(f"  ❌ {name}: value mismatch (confirmed: {value}, browser: {browser_cookie['value']})")
                                    found = True
                                    break
                            if not found:
                                print(f"  ❌ {name}: not found in browser")
                
                print("=== End Cookie Analysis ===\n")
                
            except Exception as e:
                print(f"❌ Failed to save page source: {e}")
        
        # Wait for the page to load
        if debug:
            print(f"Waiting {wait_time} seconds for JavaScript to render...")
        time.sleep(wait_time)
        
        # Wait for the specific element to be present
        wait = WebDriverWait(driver, timeout)
        
        if main_id is not None:
            if debug:
                print(f"Waiting for main element with id: {main_id}")
            try:
                main_element = wait.until(EC.presence_of_element_located((By.ID, main_id)))
                if debug:
                    print("✅ Main element found!")
            except TimeoutException:
                if debug:
                    print(f"❌ Timeout waiting for main element with id: {main_id}")
                return None
        else:
            if debug:
                print(f"Waiting for main elements with class: {main_class}")
            try:
                main_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, main_class)))
                if debug:
                    print(f"✅ Found {len(main_elements)} main elements!")
            except TimeoutException:
                if debug:
                    print(f"❌ Timeout waiting for main elements with class: {main_class}")
                return None
        
        # Get the page source after JavaScript has rendered
        page_source = driver.page_source
        
        if debug:
            print(f"Page source length: {len(page_source)}")
        
        # Parse the rendered HTML
        soup = BeautifulSoup(page_source, 'html.parser')
        
        def process_main_content(main_element):
            """Helper function to process main content consistently"""
            if not main_element:
                if debug:
                    print("❌ Main element is None")
                return None
            
            if debug:
                print(f"🔍 Processing main element: {main_element.name} {main_element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(main_element))}")
            
            # Replace <br> tags with newlines
            for br in main_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in main_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = main_element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        if main_id is not None:
            # Find main by ID (single main)
            target_main = soup.find('main', id=main_id)
            
            if debug:
                print(f"\nLooking for main with id: {main_id}")
                if target_main:
                    print("✅ Found target main!")
                else:
                    print("❌ Target main not found.")
                
                # Show all main elements with IDs
                all_mains = soup.find_all('main', id=True)
                if all_mains:
                    print("Available main IDs:")
                    for main_elem in all_mains:
                        print(f"  - {main_elem.get('id')}")
            
            return process_main_content(target_main)
            
        else:
            # Find mains by class (multiple mains)
            target_mains = soup.find_all('main', class_=main_class)
            
            if debug:
                print(f"\nLooking for main elements with class: {main_class}")
                print(f"Found {len(target_mains)} main elements with class '{main_class}'")
                
                # Show details of each found main element
                for i, main_elem in enumerate(target_mains):
                    print(f"Main {i+1}: {main_elem.name} {main_elem.attrs}")
                    print(f"  HTML length: {len(str(main_elem))}")
                    print(f"  Text content length: {len(main_elem.get_text())}")
                    print(f"  First 100 chars: {repr(main_elem.get_text()[:100])}")
            
            if not target_mains:
                return None
            
            # Process all found main elements
            results = []
            for i, main_elem in enumerate(target_mains):
                if debug:
                    print(f"\n--- Processing main {i+1} ---")
                content = process_main_content(main_elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed main {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ Main {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            return results if results else None
        
    except WebDriverException as e:
        if debug:
            print(f"WebDriver error: {str(e)}")
        raise Exception(f"WebDriver error: {str(e)}")
    except Exception as e:
        if debug:
            print(f"Error: {str(e)}")
        raise Exception(f"Error processing webpage: {str(e)}")
    finally:
        if driver:
            if debug:
                print("Closing browser...")
            driver.quit()

def simulate_human_behavior(driver, debug: bool = True):
    """
    Simulates realistic human behavior to avoid detection.
    
    Args:
        driver: The WebDriver instance
        debug (bool): If True, prints debug information
    """
    if debug:
        print("Simulating human behavior...")
    
    try:
        # Get page dimensions
        page_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        # Simulate random scrolling
        scroll_positions = [0, page_height // 4, page_height // 2, page_height * 3 // 4, page_height]
        for pos in scroll_positions:
            driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(random.uniform(0.5, 2.0))
        
        # Simulate mouse movements (if not headless)
        try:
            # Try to move mouse to random positions
            action = webdriver.ActionChains(driver)
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                action.move_by_offset(x, y).perform()
                time.sleep(random.uniform(0.1, 0.5))
        except:
            pass  # Mouse movements might not work in headless mode
        
        # Simulate random page interactions
        try:
            # Try to focus on random elements
            elements = driver.find_elements(By.TAG_NAME, "div")
            if elements:
                random_element = random.choice(elements[:10])  # Pick from first 10 elements
                driver.execute_script("arguments[0].focus();", random_element)
                time.sleep(random.uniform(0.2, 1.0))
        except:
            pass
        
        if debug:
            print("Human behavior simulation complete")
            
    except Exception as e:
        if debug:
            print(f"Error during human behavior simulation: {e}")

def debug_selenium_cookies(driver, url: str, debug: bool = True):
    """
    Comprehensive debugging function to track cookie changes in Selenium.
    This helps identify when and why cookies might be changing.
    
    Args:
        driver: The Selenium WebDriver instance
        url (str): The URL being accessed
        debug (bool): If True, prints detailed debug information
    """
    if not debug:
        return
    
    print("\n=== Selenium Cookie Debug ===")
    
    # Step 1: Check initial cookies before any navigation
    print("1. Initial cookies (before any navigation):")
    try:
        initial_cookies = driver.get_cookies()
        print(f"   Found {len(initial_cookies)} cookies")
        for cookie in initial_cookies:
            print(f"   - {cookie['name']}: {cookie['value'][:30]}{'...' if len(cookie['value']) > 30 else ''}")
    except Exception as e:
        print(f"   Error getting initial cookies: {e}")
    
    # Step 2: Navigate to domain and check cookies
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    protocol = parsed_url.scheme
    domain_url = f"{protocol}://{domain}"
    
    print(f"\n2. Navigating to domain: {domain_url}")
    try:
        driver.get(domain_url)
        time.sleep(2)  # Wait for page to load
        
        domain_cookies = driver.get_cookies()
        print(f"   After domain navigation: {len(domain_cookies)} cookies")
        for cookie in domain_cookies:
            print(f"   - {cookie['name']}: {cookie['value'][:30]}{'...' if len(cookie['value']) > 30 else ''}")
            
        # Check for any new cookies added by the domain
        initial_names = {c['name'] for c in initial_cookies}
        domain_names = {c['name'] for c in domain_cookies}
        new_cookies = domain_names - initial_names
        if new_cookies:
            print(f"   ⚠️  Domain added {len(new_cookies)} new cookies: {list(new_cookies)}")
            
    except Exception as e:
        print(f"   Error during domain navigation: {e}")
    
    # Step 3: Set our cookies and verify
    print(f"\n3. Setting cookies from CONFIRMED_HEADERS:")
    if 'Cookie' in CONFIRMED_HEADERS:
        cookie_string = CONFIRMED_HEADERS['Cookie']
        cookies = cookie_string.split('; ')
        
        print(f"   Parsing cookie string: {cookie_string[:100]}{'...' if len(cookie_string) > 100 else ''}")
        print(f"   Found {len(cookies)} cookie parts")
        
        # Track which cookies we're setting
        cookies_to_set = []
        for cookie in cookies:
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                name = name.strip()
                value = value.strip()
                cookies_to_set.append((name, value))
                print(f"   - Will set: {name} = {value[:30]}{'...' if len(value) > 30 else ''}")
        
        # Set cookies one by one and track changes
        for name, value in cookies_to_set:
            try:
                before_cookies = driver.get_cookies()
                before_names = {c['name'] for c in before_cookies}
                
                driver.add_cookie({
                    'name': name,
                    'value': value,
                    'domain': domain
                })
                
                after_cookies = driver.get_cookies()
                after_names = {c['name'] for c in after_cookies}
                
                # Check if cookie was added/modified
                if name in after_names:
                    # Find the cookie value
                    for cookie in after_cookies:
                        if cookie['name'] == name:
                            if cookie['value'] == value:
                                print(f"   ✅ {name}: set successfully")
                            else:
                                print(f"   ⚠️  {name}: value changed from '{value[:30]}...' to '{cookie['value'][:30]}...'")
                            break
                else:
                    print(f"   ❌ {name}: failed to set")
                    
            except Exception as e:
                print(f"   ❌ {name}: error setting cookie: {e}")
    
    # Step 4: Navigate to final URL and check cookies again
    print(f"\n4. Navigating to final URL: {url}")
    try:
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        final_cookies = driver.get_cookies()
        print(f"   After final navigation: {len(final_cookies)} cookies")
        for cookie in final_cookies:
            print(f"   - {cookie['name']}: {cookie['value'][:30]}{'...' if len(cookie['value']) > 30 else ''}")
        
        # Check for any cookies that changed or were removed
        domain_names = {c['name'] for c in domain_cookies}
        final_names = {c['name'] for c in final_cookies}
        
        removed_cookies = domain_names - final_names
        if removed_cookies:
            print(f"   ⚠️  {len(removed_cookies)} cookies were removed: {list(removed_cookies)}")
        
        added_cookies = final_names - domain_names
        if added_cookies:
            print(f"   ⚠️  {len(added_cookies)} new cookies were added: {list(added_cookies)}")
        
        # Check for value changes in common cookies
        domain_cookie_dict = {c['name']: c['value'] for c in domain_cookies}
        final_cookie_dict = {c['name']: c['value'] for c in final_cookies}
        
        changed_cookies = []
        for name in domain_names & final_names:
            if domain_cookie_dict[name] != final_cookie_dict[name]:
                changed_cookies.append(name)
        
        if changed_cookies:
            print(f"   ⚠️  {len(changed_cookies)} cookies changed values: {changed_cookies}")
            for name in changed_cookies:
                print(f"      {name}: '{domain_cookie_dict[name][:30]}...' -> '{final_cookie_dict[name][:30]}...'")
        
    except Exception as e:
        print(f"   Error during final navigation: {e}")
    
    # Step 5: Check for any JavaScript that might be modifying cookies
    print(f"\n5. Checking for JavaScript cookie modifications:")
    try:
        # Execute script to check if any JS is modifying cookies
        js_check = driver.execute_script("""
            // Check if document.cookie is being modified
            let originalCookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
            let cookieModifications = 0;
            
            Object.defineProperty(document, 'cookie', {
                get: function() {
                    return originalCookie.get.call(this);
                },
                set: function(value) {
                    cookieModifications++;
                    console.log('Cookie modification detected:', value);
                    return originalCookie.set.call(this, value);
                }
            });
            
            return {
                cookieModifications: cookieModifications,
                currentCookies: document.cookie
            };
        """)
        
        print(f"   JavaScript cookie modifications detected: {js_check.get('cookieModifications', 0)}")
        print(f"   Current document.cookie: {js_check.get('currentCookies', 'None')}")
        
    except Exception as e:
        print(f"   Error checking JavaScript cookie modifications: {e}")
    
    # Step 6: Check for redirects that might affect cookies
    print(f"\n6. Checking for redirects:")
    try:
        current_url = driver.current_url
        if current_url != url:
            print(f"   ⚠️  Redirected from {url} to {current_url}")
            
            # Check cookies after redirect
            redirect_cookies = driver.get_cookies()
            print(f"   After redirect: {len(redirect_cookies)} cookies")
            
            # Compare with expected cookies
            if 'Cookie' in CONFIRMED_HEADERS:
                expected_cookies = {name.strip(): value.strip() for name, value in 
                                  [cookie.split('=', 1) for cookie in CONFIRMED_HEADERS['Cookie'].split('; ') if '=' in cookie]}
                
                for name, expected_value in expected_cookies.items():
                    found = False
                    for cookie in redirect_cookies:
                        if cookie['name'] == name:
                            if cookie['value'] == expected_value:
                                print(f"   ✅ {name}: matches expected value")
                            else:
                                print(f"   ❌ {name}: expected '{expected_value[:30]}...', got '{cookie['value'][:30]}...'")
                            found = True
                            break
                    if not found:
                        print(f"   ❌ {name}: not found in browser cookies")
        else:
            print(f"   ✅ No redirect detected")
            
    except Exception as e:
        print(f"   Error checking redirects: {e}")
    
    print("=== End Selenium Cookie Debug ===\n")

def fetch_with_exact_headers_preserve_cookies(url: str, CONFIRMED_HEADERS: dict, main_id: str = None, main_class: str = None, 
                                            wait_time: int = 5, timeout: int = 30, debug: bool = True,
                                            preserve_cookies: List[str] = None) -> Optional[Union[str, List[str]]]:
    """
    Fetches content using undetected-chromedriver with exact headers and cookie preservation.
    This prevents the website from modifying specific cookies that are critical for authentication.
    
    Args:
        url (str): The URL to fetch
        main_id (str, optional): The ID of the main element to find
        main_class (str, optional): The class name of main elements to find
        wait_time (int): Time to wait for JavaScript to render
        timeout (int): Timeout for element detection
        debug (bool): If True, prints debug information
        preserve_cookies (List[str], optional): List of cookie names to preserve from changes
        
    Returns:
        Optional[Union[str, List[str]]]: The fetched content
    """
    if not UNDETECTED_AVAILABLE:
        raise ImportError("Undetected ChromeDriver is not available. Install with: pip install undetected-chromedriver")
    
    if debug:
        print(f"\n=== Fetching with Exact Headers (Cookie Preservation) ===")
        print(f"URL: {url}")
        print(f"Preserving cookies: {preserve_cookies or 'None (all cookies)'}")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if main_id is None and main_class is None:
        raise ValueError("Either main_id or main_class must be provided")
    if main_id is not None and main_class is not None:
        raise ValueError("Only one of main_id or main_class should be provided")

    # If no preserve_cookies specified, preserve all cookies from CONFIRMED_HEADERS
    if preserve_cookies is None and 'Cookie' in CONFIRMED_HEADERS:
        cookie_string = CONFIRMED_HEADERS['Cookie']
        preserve_cookies = []
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                name = cookie.split('=', 1)[0].strip()
                preserve_cookies.append(name)
        if debug:
            print(f"Auto-detected cookies to preserve: {preserve_cookies}")

    driver = None
    try:
        # Set up undetected Chrome options
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Set the exact user agent from confirmed headers
        options.add_argument(f"--user-agent={CONFIRMED_HEADERS['User-Agent']}")
        
        # Add language preference
        options.add_argument(f"--accept-language={CONFIRMED_HEADERS['Accept-Language']}")
        
        # Additional undetected-chromedriver specific options
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Disable various Chrome features that might be detected
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # We'll re-enable this after setup
        
        if debug:
            print("Setting up undetected Chrome driver with cookie preservation...")
            print(f"User-Agent: {CONFIRMED_HEADERS['User-Agent']}")
            print(f"Accept-Language: {CONFIRMED_HEADERS['Accept-Language']}")
        
        # Initialize the undetected driver
        driver = uc.Chrome(options=options)
        
        # Re-enable JavaScript after driver initialization
        driver.execute_script("""
            // Re-enable JavaScript execution
            document.documentElement.style.pointerEvents = 'auto';
        """)
        
        # Add random delay to simulate human behavior
        if debug:
            print("Adding random delay to simulate human behavior...")
        time.sleep(random.uniform(1, 3))
        
        # Execute script to override fetch and XMLHttpRequest with exact headers
        driver.execute_script(f"""
            // Override fetch to add exact headers
            const originalFetch = window.fetch;
            window.fetch = function(url, options) {{
                options = options || {{}};
                options.headers = options.headers || {{}};
                
                // Add ALL confirmed headers
                const confirmedHeaders = {json.dumps(CONFIRMED_HEADERS)};
                for (const [key, value] of Object.entries(confirmedHeaders)) {{
                    options.headers[key] = value;
                }}
                
                // Log what headers are being sent
                console.log('Fetch request headers:', options.headers);
                
                return originalFetch(url, options);
            }};
            
            // Override XMLHttpRequest to add exact headers
            const originalOpen = XMLHttpRequest.prototype.open;
            const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
            
            XMLHttpRequest.prototype.open = function(method, url, ...args) {{
                this._url = url;
                this._method = method;
                this._headers = {{}};
                return originalOpen.call(this, method, url, ...args);
            }};
            
            XMLHttpRequest.prototype.setRequestHeader = function(header, value) {{
                this._headers[header] = value;
                return originalSetRequestHeader.call(this, header, value);
            }};
            
            // Override send to add missing headers
            const originalSend = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.send = function(data) {{
                const confirmedHeaders = {json.dumps(CONFIRMED_HEADERS)};
                for (const [key, value] of Object.entries(confirmedHeaders)) {{
                    if (!this._headers[key]) {{
                        originalSetRequestHeader.call(this, key, value);
                    }}
                }}
                
                // Log what headers are being sent
                console.log('XMLHttpRequest headers:', this._headers);
                
                return originalSend.call(this, data);
            }};
            
            // Override navigator properties to avoid detection
            Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
            Object.defineProperty(navigator, 'plugins', {{get: () => [1, 2, 3, 4, 5]}});
            Object.defineProperty(navigator, 'languages', {{get: () => ['en-US', 'en']}});
            
            // Override Chrome-specific properties
            Object.defineProperty(navigator, 'chrome', {{
                get: () => ({{
                    runtime: {{}},
                    loadTimes: function() {{}},
                    csi: function() {{}},
                    app: {{}}
                }})
            }});
            
            // Set referer
            Object.defineProperty(document, 'referrer', {{
                get: function() {{ return '{CONFIRMED_HEADERS.get('Referer', '')}'; }}
            }});
            
            // Log the confirmed headers for verification
            console.log('Confirmed headers loaded:', {json.dumps(CONFIRMED_HEADERS)});
        """)
        
        if debug:
            print("\n=== Header Verification ===")
            print("Confirmed headers that should be sent:")
            for key, value in CONFIRMED_HEADERS.items():
                print(f"  {key}: {value}")
            print("=== End Header Verification ===\n")
        
        # Set up cookie preservation if specified
        if preserve_cookies:
            if debug:
                print(f"Setting up cookie preservation for: {preserve_cookies}")
            
            # Store original cookie values
            original_cookie_values = {}
            if 'Cookie' in CONFIRMED_HEADERS:
                cookie_string = CONFIRMED_HEADERS['Cookie']
                for cookie in cookie_string.split('; '):
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        name = name.strip()
                        value = value.strip()
                        if name in preserve_cookies:
                            original_cookie_values[name] = value
            
            # Execute JavaScript to prevent cookie modifications
            driver.execute_script(f"""
                // Store original cookie values that should be preserved
                const preservedCookies = {json.dumps(original_cookie_values)};
                const preservedCookieNames = {json.dumps(preserve_cookies)};
                
                console.log('Setting up cookie preservation for:', preservedCookieNames);
                console.log('Original cookie values:', preservedCookies);
                
                // Override document.cookie to prevent modifications to preserved cookies
                const originalCookieDescriptor = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
                let cookieModifications = 0;
                
                Object.defineProperty(document, 'cookie', {{
                    get: function() {{
                        return originalCookieDescriptor.get.call(this);
                    }},
                    set: function(value) {{
                        cookieModifications++;
                        console.log('Cookie modification attempt:', value);
                        
                        // Parse the cookie being set
                        if (value && value.includes('=')) {{
                            const [name] = value.split('=');
                            const cookieName = name.trim();
                            
                            // Check if this is a preserved cookie
                            if (preservedCookieNames.includes(cookieName)) {{
                                console.log('BLOCKED: Attempt to modify preserved cookie:', cookieName);
                                console.log('Original value:', preservedCookies[cookieName]);
                                console.log('Attempted value:', value);
                                
                                // Block the modification by not calling the original setter
                                return;
                            }}
                        }}
                        
                        // Allow non-preserved cookies to be set normally
                        return originalCookieDescriptor.set.call(this, value);
                    }}
                }});
                
                // Function to restore preserved cookies
                window.restorePreservedCookies = function() {{
                    console.log('Restoring preserved cookies...');
                    for (const [name, value] of Object.entries(preservedCookies)) {{
                        const cookieString = `${{name}}=${{value}}; path=/`;
                        console.log('Restoring cookie:', cookieString);
                        originalCookieDescriptor.set.call(document, cookieString);
                    }}
                }};
                
                // Set up periodic cookie restoration
                setInterval(function() {{
                    window.restorePreservedCookies();
                }}, 1000); // Restore every second
                
                // Also restore on page load events
                window.addEventListener('load', function() {{
                    setTimeout(window.restorePreservedCookies, 100);
                }});
                
                window.addEventListener('DOMContentLoaded', function() {{
                    setTimeout(window.restorePreservedCookies, 100);
                }});
                
                console.log('Cookie preservation system activated');
            """)
            
            # Verify the function was created
            try:
                result = driver.execute_script("return typeof window.restorePreservedCookies;")
                if result == "function":
                    if debug:
                        print("✅ Cookie preservation function created successfully")
                else:
                    if debug:
                        print(f"❌ Cookie preservation function not created properly: {result}")
            except Exception as e:
                if debug:
                    print(f"❌ Error verifying cookie preservation function: {e}")
        
        # Run comprehensive cookie debugging
        debug_selenium_cookies(driver, url, debug)
        
        if debug:
            print("Navigating to URL with cookies set...")
        
        # Add random delay before final navigation
        time.sleep(random.uniform(1, 3))
        
        # Now navigate to the actual URL with cookies set
        driver.get(url)
        
        # Add random delay after page load
        time.sleep(random.uniform(2, 5))
        
        # Restore preserved cookies after navigation
        if preserve_cookies:
            if debug:
                print("Restoring preserved cookies after navigation...")
            try:
                # Check if function exists before calling it
                function_exists = driver.execute_script("return typeof window.restorePreservedCookies === 'function';")
                if function_exists:
                    driver.execute_script("window.restorePreservedCookies();")
                    if debug:
                        print("✅ Cookies restored successfully")
                else:
                    if debug:
                        print("❌ Cookie restoration function not found, skipping restoration")
            except Exception as e:
                if debug:
                    print(f"❌ Error restoring cookies: {e}")
            time.sleep(1)  # Give time for cookies to be restored
        
        # Simulate human behavior to avoid detection
        simulate_human_behavior(driver, debug)
        
        # Periodically restore cookies during the session
        if preserve_cookies:
            if debug:
                print("Setting up periodic cookie restoration...")
            
            # Restore cookies every few seconds
            for i in range(3):  # Restore 3 times during the session
                time.sleep(2)
                try:
                    # Check if function exists before calling it
                    function_exists = driver.execute_script("return typeof window.restorePreservedCookies === 'function';")
                    if function_exists:
                        driver.execute_script("window.restorePreservedCookies();")
                        if debug:
                            print(f"✅ Cookie restoration {i+1}/3 completed")
                    else:
                        if debug:
                            print(f"❌ Cookie restoration {i+1}/3 skipped - function not found")
                except Exception as e:
                    if debug:
                        print(f"❌ Error during cookie restoration {i+1}/3: {e}")
        
        # Debug: Check what we received
        if debug:
            print("\n=== Selenium Response Debug ===")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")
            print(f"Page source length: {len(driver.page_source)}")
            
            # Check if we got redirected
            if driver.current_url != url:
                print(f"⚠️  Redirected from {url} to {driver.current_url}")
            
            # Show first 500 characters of page source
            page_source = driver.page_source
            print(f"\nFirst 500 characters of page source:")
            print("=" * 50)
            print(page_source[:500])
            print("=" * 50)
            
            # Check for common error indicators
            error_indicators = ['captcha', 'blocked', 'forbidden', 'access denied', 'cloudflare', 'security check']
            page_lower = page_source.lower()
            found_errors = []
            for indicator in error_indicators:
                if indicator in page_lower:
                    found_errors.append(indicator)
            
            if found_errors:
                print(f"⚠️  Found potential error indicators: {found_errors}")
            
            # Check for main elements in the raw HTML
            if main_id:
                if f'id="{main_id}"' in page_source:
                    print(f"✅ Found main element with id '{main_id}' in HTML")
                else:
                    print(f"❌ Main element with id '{main_id}' NOT found in HTML")
            
            if main_class:
                if f'class="{main_class}"' in page_source or f'class=\'{main_class}\'' in page_source:
                    print(f"✅ Found main element with class '{main_class}' in HTML")
                else:
                    print(f"❌ Main element with class '{main_class}' NOT found in HTML")
            
            print("=== End Selenium Response Debug ===\n")
        
        # Save full page source to file for detailed inspection
        if debug:
            try:
                timestamp = int(time.time())
                filename = f"undetected_debug_{timestamp}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print(f"💾 Full page source saved to: {filename}")
                
                # Verify cookies were set correctly
                print("Verifying cookies in browser...")
                browser_cookies = driver.get_cookies()
                print(f"Browser has {len(browser_cookies)} cookies:")
                for cookie in browser_cookies:
                    print(f"  {cookie['name']}: {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}")
                
                # Compare with confirmed headers cookies
                if 'Cookie' in CONFIRMED_HEADERS:
                    print("\nComparing with confirmed headers cookies:")
                    confirmed_cookies = CONFIRMED_HEADERS['Cookie'].split('; ')
                    for cookie in confirmed_cookies:
                        if '=' in cookie:
                            name, value = cookie.split('=', 1)
                            name = name.strip()
                            value = value.strip()
                            # Check if this cookie exists in browser
                            found = False
                            for browser_cookie in browser_cookies:
                                if browser_cookie['name'] == name:
                                    if browser_cookie['value'] == value:
                                        print(f"  ✅ {name}: matches")
                                    else:
                                        print(f"  ❌ {name}: value mismatch (confirmed: {value}, browser: {browser_cookie['value']})")
                                    found = True
                                    break
                            if not found:
                                print(f"  ❌ {name}: not found in browser")
                
                print("=== End Cookie Analysis ===\n")
                
            except Exception as e:
                print(f"❌ Failed to save page source: {e}")
        
        # Wait for the page to load
        if debug:
            print(f"Waiting {wait_time} seconds for JavaScript to render...")
        time.sleep(wait_time)
        
        # Wait for the specific element to be present
        wait = WebDriverWait(driver, timeout)
        
        if main_id is not None:
            if debug:
                print(f"Waiting for main element with id: {main_id}")
            try:
                main_element = wait.until(EC.presence_of_element_located((By.ID, main_id)))
                if debug:
                    print("✅ Main element found!")
            except TimeoutException:
                if debug:
                    print(f"❌ Timeout waiting for main element with id: {main_id}")
                return None
        else:
            if debug:
                print(f"Waiting for main elements with class: {main_class}")
            try:
                main_elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, main_class)))
                if debug:
                    print(f"✅ Found {len(main_elements)} main elements!")
            except TimeoutException:
                if debug:
                    print(f"❌ Timeout waiting for main elements with class: {main_class}")
                return None
        
        # Get the page source after JavaScript has rendered
        page_source = driver.page_source
        
        if debug:
            print(f"Page source length: {len(page_source)}")
        
        # Parse the rendered HTML
        soup = BeautifulSoup(page_source, 'html.parser')
        
        def process_main_content(main_element):
            """Helper function to process main content consistently"""
            if not main_element:
                if debug:
                    print("❌ Main element is None")
                return None
            
            if debug:
                print(f"🔍 Processing main element: {main_element.name} {main_element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(main_element))}")
            
            # Replace <br> tags with newlines
            for br in main_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in main_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = main_element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        if main_id is not None:
            # Find main by ID (single main)
            target_main = soup.find('main', id=main_id)
            
            if debug:
                print(f"\nLooking for main with id: {main_id}")
                if target_main:
                    print("✅ Found target main!")
                else:
                    print("❌ Target main not found.")
                
                # Show all main elements with IDs
                all_mains = soup.find_all('main', id=True)
                if all_mains:
                    print("Available main IDs:")
                    for main_elem in all_mains:
                        print(f"  - {main_elem.get('id')}")
            
            return process_main_content(target_main)
            
        else:
            # Find mains by class (multiple mains)
            target_mains = soup.find_all('main', class_=main_class)
            
            if debug:
                print(f"\nLooking for main elements with class: {main_class}")
                print(f"Found {len(target_mains)} main elements with class '{main_class}'")
                
                # Show details of each found main element
                for i, main_elem in enumerate(target_mains):
                    print(f"Main {i+1}: {main_elem.name} {main_elem.attrs}")
                    print(f"  HTML length: {len(str(main_elem))}")
                    print(f"  Text content length: {len(main_elem.get_text())}")
                    print(f"  First 100 chars: {repr(main_elem.get_text()[:100])}")
            
            if not target_mains:
                return None
            
            # Process all found main elements
            results = []
            for i, main_elem in enumerate(target_mains):
                if debug:
                    print(f"\n--- Processing main {i+1} ---")
                content = process_main_content(main_elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed main {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ Main {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            return results if results else None
        
    except Exception as e:
        if debug:
            print(f"Error in fetch_with_exact_headers_preserve_cookies: {str(e)}")
        raise e
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

# --- fetch_with_existing_driver variants ---

def fetch_with_existing_driver_div(driver, url: str, div_id: str = None, div_class: str = None, 
                                  wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Fetches content from div elements using an existing driver instance.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        div_id (str): ID of the div element to extract content from
        div_class (str): Class name of div elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"\n=== Fetching Div Content with Existing Driver ===")
        print(f"URL: {url}")
        print(f"Div ID: {div_id}")
        print(f"Div Class: {div_class}")
    
    return _fetch_with_existing_driver_generic(
        driver=driver,
        url=url,
        element_type="div",
        element_id=div_id,
        element_class=div_class,
        wait_time=wait_time,
        timeout=timeout,
        debug=debug
    )

def fetch_with_existing_driver_list(driver, url: str, list_id: str = None, list_class: str = None, 
                                   wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Fetches content from list elements (ul, ol) using an existing driver instance.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        list_id (str): ID of the list element to extract content from
        list_class (str): Class name of list elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"\n=== Fetching List Content with Existing Driver ===")
        print(f"URL: {url}")
        print(f"List ID: {list_id}")
        print(f"List Class: {list_class}")
    
    return _fetch_with_existing_driver_generic(
        driver=driver,
        url=url,
        element_type="ul,ol",  # Both ul and ol elements
        element_id=list_id,
        element_class=list_class,
        wait_time=wait_time,
        timeout=timeout,
        debug=debug
    )

def fetch_with_existing_driver_section(driver, url: str, section_id: str = None, section_class: str = None, 
                                      wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Fetches content from section elements using an existing driver instance.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        section_id (str): ID of the section element to extract content from
        section_class (str): Class name of section elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"\n=== Fetching Section Content with Existing Driver ===")
        print(f"URL: {url}")
        print(f"Section ID: {section_id}")
        print(f"Section Class: {section_class}")
    
    return _fetch_with_existing_driver_generic(
        driver=driver,
        url=url,
        element_type="section",
        element_id=section_id,
        element_class=section_class,
        wait_time=wait_time,
        timeout=timeout,
        debug=debug
    )

def fetch_with_existing_driver_article(driver, url: str, article_id: str = None, article_class: str = None, 
                                      wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Fetches content from article elements using an existing driver instance.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        article_id (str): ID of the article element to extract content from
        article_class (str): Class name of article elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"\n=== Fetching Article Content with Existing Driver ===")
        print(f"URL: {url}")
        print(f"Article ID: {article_id}")
        print(f"Article Class: {article_class}")
    
    return _fetch_with_existing_driver_generic(
        driver=driver,
        url=url,
        element_type="article",
        element_id=article_id,
        element_class=article_class,
        wait_time=wait_time,
        timeout=timeout,
        debug=debug
    )

def fetch_with_existing_driver_custom(driver, url: str, element_type: str, element_id: str = None, element_class: str = None, 
                                     wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Fetches content from any custom element type using an existing driver instance.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        element_type (str): Type of HTML element (e.g., 'div', 'span', 'p', 'ul', 'ol', 'section', 'article', etc.)
        element_id (str): ID of the element to extract content from
        element_class (str): Class name of elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"\n=== Fetching Custom Element Content with Existing Driver ===")
        print(f"URL: {url}")
        print(f"Element Type: {element_type}")
        print(f"Element ID: {element_id}")
        print(f"Element Class: {element_class}")
    
    return _fetch_with_existing_driver_generic(
        driver=driver,
        url=url,
        element_type=element_type,
        element_id=element_id,
        element_class=element_class,
        wait_time=wait_time,
        timeout=timeout,
        debug=debug
    )

def _fetch_with_existing_driver_generic(driver, url: str, element_type: str, element_id: str = None, element_class: str = None, 
                                       wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Generic function that handles fetching content from any element type.
    This is the underlying implementation for all the specific element type functions.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        element_type (str): Type of HTML element
        element_id (str): ID of the element to extract content from
        element_class (str): Class name of elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"Using existing driver with authenticated session")
        print(f"Driver type: {type(driver).__name__}")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if element_id is None and element_class is None:
        raise ValueError("Either element_id or element_class must be provided")
    if element_id is not None and element_class is not None:
        raise ValueError("Only one of element_id or element_class should be provided")

    try:
        # Check if driver is still valid
        try:
            current_url = driver.current_url
            if debug:
                print(f"Current driver URL: {current_url}")
        except Exception as e:
            raise Exception(f"Driver is no longer valid: {str(e)}")
        
        # Add random delay to simulate human behavior
        if debug:
            print("Adding random delay to simulate human behavior...")
        time.sleep(random.uniform(1, 3))
        
        if debug:
            print("Navigating to target URL...")
        
        # Navigate to the target URL
        driver.get(url)
        
        # Add random delay after page load
        time.sleep(random.uniform(2, 5))
        
        # Simulate human behavior to avoid detection
        simulate_human_behavior(driver, debug)
        
        # Get page info
        page_info = {
            'title': driver.title,
            'current_url': driver.current_url,
            'page_source_length': len(driver.page_source)
        }
        
        # Debug: Check what we received
        if debug:
            print("\n=== Driver Response Debug ===")
            print(f"Current URL: {page_info['current_url']}")
            print(f"Page title: {page_info['title']}")
            print(f"Page source length: {page_info['page_source_length']}")
            
            # Check if we got redirected
            if page_info['current_url'] != url:
                print(f"⚠️  Redirected from {url} to {page_info['current_url']}")
            
            # Show first 500 characters of page source
            page_source = driver.page_source
            print(f"\nFirst 500 characters of page source:")
            print("=" * 50)
            print(page_source[:500])
            print("=" * 50)
            
            # Check for common error indicators
            error_indicators = ['captcha', 'blocked', 'forbidden', 'access denied', 'cloudflare', 'security check']
            page_lower = page_source.lower()
            found_errors = []
            for indicator in error_indicators:
                if indicator in page_lower:
                    found_errors.append(indicator)
            
            if found_errors:
                print(f"⚠️  Found potential error indicators: {found_errors}")
            
            # Check for target elements in the raw HTML
            if element_id:
                if f'id="{element_id}"' in page_source:
                    print(f"✅ Found element with id '{element_id}' in HTML")
                else:
                    print(f"❌ Element with id '{element_id}' NOT found in HTML")
            
            if element_class:
                if f'class="{element_class}"' in page_source or f'class=\'{element_class}\'' in page_source:
                    print(f"✅ Found element with class '{element_class}' in HTML")
                else:
                    print(f"❌ Element with class '{element_class}' NOT found in HTML")
            
            print("=== End Driver Response Debug ===\n")
        
        # Save full page source to file for detailed inspection
        if debug:
            try:
                timestamp = int(time.time())
                filename = f"existing_driver_{element_type}_debug_{timestamp}.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print(f"💾 Full page source saved to: {filename}")
                
                # Show current cookies in browser
                print("Current cookies in browser:")
                browser_cookies = driver.get_cookies()
                print(f"Browser has {len(browser_cookies)} cookies:")
                for cookie in browser_cookies:
                    print(f"  {cookie['name']}: {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}")
                
                print("=== End Cookie Analysis ===\n")
                
            except Exception as e:
                print(f"❌ Failed to save page source: {e}")
        
        # Wait for the page to load
        if debug:
            print(f"Waiting {wait_time} seconds for JavaScript to render...")
        time.sleep(wait_time)
        
        # Wait for the specific element to be present
        wait = WebDriverWait(driver, timeout)
        
        # Store Selenium elements for return
        selenium_elements = []
        
        if element_id is not None:
            if debug:
                print(f"Waiting for {element_type} element with id: {element_id}")
            try:
                # Handle multiple element types (like "ul,ol")
                if "," in element_type:
                    element_types = [et.strip() for et in element_type.split(",")]
                    main_element = None
                    for et in element_types:
                        try:
                            main_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{et}#{element_id}")))
                            selenium_elements.append(main_element)
                            if debug:
                                print(f"✅ Found {et} element with id: {element_id}")
                            break
                        except TimeoutException:
                            continue
                    if not main_element:
                        if debug:
                            print(f"❌ Timeout waiting for {element_type} element with id: {element_id}")
                        return {
                            'content': None,
                            'elements': [],
                            'soup_elements': [],
                            'page_info': page_info,
                            'success': False
                        }
                else:
                    main_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{element_type}#{element_id}")))
                    selenium_elements.append(main_element)
                    if debug:
                        print("✅ Element found!")
            except TimeoutException:
                if debug:
                    print(f"❌ Timeout waiting for {element_type} element with id: {element_id}")
                return {
                    'content': None,
                    'elements': [],
                    'soup_elements': [],
                    'page_info': page_info,
                    'success': False
                }
        else:
            if debug:
                print(f"Waiting for {element_type} elements with class: {element_class}")
            try:
                # Handle multiple element types (like "ul,ol")
                if "," in element_type:
                    element_types = [et.strip() for et in element_type.split(",")]
                    main_elements = []
                    for et in element_types:
                        try:
                            elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"{et}.{element_class}")))
                            main_elements.extend(elements)
                        except TimeoutException:
                            continue
                    if not main_elements:
                        if debug:
                            print(f"❌ Timeout waiting for {element_type} elements with class: {element_class}")
                        return {
                            'content': None,
                            'elements': [],
                            'soup_elements': [],
                            'page_info': page_info,
                            'success': False
                        }
                    selenium_elements = main_elements
                    if debug:
                        print(f"✅ Found {len(main_elements)} {element_type} elements!")
                else:
                    main_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"{element_type}.{element_class}")))
                    selenium_elements = main_elements
                    if debug:
                        print(f"✅ Found {len(main_elements)} {element_type} elements!")
            except TimeoutException:
                if debug:
                    print(f"❌ Timeout waiting for {element_type} elements with class: {element_class}")
                return {
                    'content': None,
                    'elements': [],
                    'soup_elements': [],
                    'page_info': page_info,
                    'success': False
                }
        
        # Get the page source after JavaScript has rendered
        page_source = driver.page_source
        
        if debug:
            print(f"Page source length: {len(page_source)}")
        
        # Parse the rendered HTML
        soup = BeautifulSoup(page_source, 'html.parser')
        
        def process_element_content(element):
            """Helper function to process element content consistently"""
            if not element:
                if debug:
                    print("❌ Element is None")
                return None
            
            if debug:
                print(f"🔍 Processing {element.name} element: {element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(element))}")
            
            # Special handling for list elements
            if element.name in ['ul', 'ol']:
                return process_list_content(element, debug)
            
            # Replace <br> tags with newlines
            for br in element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        def process_list_content(list_element, debug: bool = True):
            """Special processing for list elements to preserve list structure"""
            if debug:
                print(f"🔍 Processing list element: {list_element.name}")
            
            # Get all list items
            list_items = list_element.find_all('li')
            
            if debug:
                print(f"🔍 Found {len(list_items)} list items")
            
            # Process each list item
            processed_items = []
            for i, item in enumerate(list_items):
                if debug:
                    print(f"🔍 Processing list item {i+1}")
                
                # Get text content of the item
                item_text = item.get_text().strip()
                
                if item_text:
                    # Add bullet point or number based on list type
                    if list_element.name == 'ul':
                        processed_items.append(f"• {item_text}")
                    elif list_element.name == 'ol':
                        processed_items.append(f"{i+1}. {item_text}")
                    else:
                        processed_items.append(item_text)
                    
                    if debug:
                        print(f"🔍 List item {i+1}: {item_text[:100]}{'...' if len(item_text) > 100 else ''}")
            
            # Join all items with newlines
            final_content = '\n'.join(processed_items)
            
            if debug:
                print(f"🔍 Final list content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final list content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final list content is empty")
            
            return final_content
        
        # Find BeautifulSoup elements
        soup_elements = []
        if element_id is not None:
            # Find element by ID (single element)
            if "," in element_type:
                # Handle multiple element types
                element_types = [et.strip() for et in element_type.split(",")]
                target_element = None
                for et in element_types:
                    target_element = soup.find(et, id=element_id)
                    if target_element:
                        break
            else:
                target_element = soup.find(element_type, id=element_id)
            
            if target_element:
                soup_elements.append(target_element)
            
            if debug:
                print(f"\nLooking for {element_type} with id: {element_id}")
                if target_element:
                    print("✅ Found target element!")
                else:
                    print("❌ Target element not found.")
                
                # Show all elements with IDs of the target type
                if "," in element_type:
                    element_types = [et.strip() for et in element_type.split(",")]
                    all_elements = []
                    for et in element_types:
                        elements = soup.find_all(et, id=True)
                        all_elements.extend(elements)
                else:
                    all_elements = soup.find_all(element_type, id=True)
                
                if all_elements:
                    print(f"Available {element_type} IDs:")
                    for elem in all_elements:
                        print(f"  - {elem.get('id')}")
            
            # Process content
            content = process_element_content(target_element)
            
        else:
            # Find elements by class (multiple elements)
            if "," in element_type:
                # Handle multiple element types
                element_types = [et.strip() for et in element_type.split(",")]
                target_elements = []
                for et in element_types:
                    elements = soup.find_all(et, class_=element_class)
                    target_elements.extend(elements)
            else:
                target_elements = soup.find_all(element_type, class_=element_class)
            
            soup_elements = target_elements
            
            if debug:
                print(f"\nLooking for {element_type} elements with class: {element_class}")
                print(f"Found {len(target_elements)} {element_type} elements with class '{element_class}'")
                
                # Show details of each found element
                for i, elem in enumerate(target_elements):
                    print(f"Element {i+1}: {elem.name} {elem.attrs}")
                    print(f"  HTML length: {len(str(elem))}")
                    print(f"  Text content length: {len(elem.get_text())}")
                    print(f"  First 100 chars: {repr(elem.get_text()[:100])}")
            
            if not target_elements:
                return {
                    'content': None,
                    'elements': selenium_elements,
                    'soup_elements': soup_elements,
                    'page_info': page_info,
                    'success': False
                }
            
            # Process all found elements
            results = []
            for i, elem in enumerate(target_elements):
                if debug:
                    print(f"\n--- Processing {element_type} {i+1} ---")
                content = process_element_content(elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed {element_type} {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ {element_type} {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            content = results if results else None
        
        # Return dictionary with all information
        return {
            'content': content,
            'elements': selenium_elements,
            'soup_elements': soup_elements,
            'page_info': page_info,
            'success': content is not None
        }
        
    except WebDriverException as e:
        if debug:
            print(f"WebDriver error: {str(e)}")
        raise Exception(f"WebDriver error: {str(e)}")
    except Exception as e:
        if debug:
            print(f"Error: {str(e)}")
        raise Exception(f"Error processing webpage: {str(e)}")

# --- fetch_with_existing_driver (original) ---
def fetch_with_existing_driver(driver, url: str, main_id: str = None, main_class: str = None, 
                              wait_time: int = 5, timeout: int = 30, debug: bool = True) -> Optional[dict]:
    """
    Fetches content from main elements using an existing driver instance.
    This function uses a driver that already has an authenticated session (e.g., from manual_login).
    No headers or cookies are set since the driver already has the session.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        url (str): URL to fetch
        main_id (str): ID of the main element to extract content from
        main_class (str): Class name of main elements to extract content from
        wait_time (int): Time to wait for JavaScript rendering
        timeout (int): Timeout for element waiting
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'content': Extracted text content (str or List[str])
            - 'elements': List of Selenium WebElement objects
            - 'soup_elements': List of BeautifulSoup element objects
            - 'page_info': Dictionary with page title, URL, etc.
            - 'success': Boolean indicating if fetch was successful
    """
    if debug:
        print(f"\n=== Fetching Main Content with Existing Driver ===")
        print(f"URL: {url}")
        print(f"Main ID: {main_id}")
        print(f"Main Class: {main_class}")
    
    return _fetch_with_existing_driver_generic(
        driver=driver,
        url=url,
        element_type="main",
        element_id=main_id,
        element_class=main_class,
        wait_time=wait_time,
        timeout=timeout,
        debug=debug
    )

def interact_with_pagination(driver, pagination_class: str = "pagination", 
                           page_item_class: str = "page-item", 
                           page_link_class: str = "page-link",
                           page_number: int = None, wait_time: int = 2, debug: bool = True) -> Optional[dict]:
    """
    Helper function to interact with pagination lists.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        pagination_class (str): CSS class of the pagination container (default: "pagination")
        page_item_class (str): CSS class of individual page items (default: "page-item")
        page_link_class (str): CSS class of page links (default: "page-link")
        page_number (int, optional): If provided, automatically clicks on this page number
        wait_time (int): Time to wait after clicking (if page_number is provided)
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'current_page': Current active page number
            - 'total_pages': Total number of pages
            - 'page_elements': List of page element dictionaries with info and WebElement
            - 'has_prev': Boolean indicating if previous button exists
            - 'has_next': Boolean indicating if next button exists
            - 'prev_element': WebElement for previous button (if exists)
            - 'next_element': WebElement for next button (if exists)
            - 'clicked_page': Page number that was clicked (if page_number was provided)
            - 'click_success': Boolean indicating if page click was successful (if page_number was provided)
            - 'success': Boolean indicating if pagination was found
    """
    if debug:
        print(f"\n=== Interacting with Pagination ===")
        print(f"Looking for pagination with class: {pagination_class}")
        print(f"Page items with class: {page_item_class}")
        print(f"Page links with class: {page_link_class}")
        if page_number is not None:
            print(f"Will click on page number: {page_number}")
    
    try:
        # Find the pagination container
        pagination_selectors = [
            f"ul.{pagination_class}",
            f".{pagination_class}",
            "ul[class*='pagination']"
        ]
        
        pagination_element = None
        for selector in pagination_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    pagination_element = elements[0]
                    if debug:
                        print(f"✅ Found pagination element with selector: {selector}")
                    break
            except Exception as e:
                if debug:
                    print(f"Tried selector '{selector}': {e}")
                continue
        
        if not pagination_element:
            if debug:
                print("❌ No pagination element found")
            return {
                'current_page': None,
                'total_pages': 0,
                'page_elements': [],
                'has_prev': False,
                'has_next': False,
                'prev_element': None,
                'next_element': None,
                'clicked_page': None,
                'click_success': False,
                'success': False
            }
        
        # Scroll to pagination element to ensure it's visible and clickable
        if debug:
            print("Scrolling to pagination element...")
        
        try:
            # Scroll to the pagination element
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", pagination_element)
            time.sleep(1)  # Wait for scroll to complete
            
            # Additional scroll to ensure it's fully visible
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'nearest'});", pagination_element)
            time.sleep(0.5)
            
            if debug:
                print("✅ Successfully scrolled to pagination element")
                
        except Exception as e:
            if debug:
                print(f"⚠️  Warning: Could not scroll to pagination element: {e}")
                print("Continuing anyway...")
        
        # Find all page items
        page_items = pagination_element.find_elements(By.CSS_SELECTOR, f"li.{page_item_class}")
        
        if debug:
            print(f"Found {len(page_items)} page items")
        
        # Parse page information
        current_page = None
        total_pages = 0
        page_elements = []
        prev_element = None
        next_element = None
        has_prev = False
        has_next = False
        target_element = None  # Element to click if page_number is provided
        
        for i, item in enumerate(page_items):
            try:
                # Get the page link element
                link_element = item.find_element(By.CSS_SELECTOR, f"div.{page_link_class}")
                
                # Get the text content
                text = link_element.text.strip()
                
                # Check if this is the active page
                is_active = "active" in item.get_attribute("class")
                
                # Check if this is a navigation button (prev/next)
                onclick = link_element.get_attribute("onclick") or ""
                
                page_info = {
                    'index': i,
                    'text': text,
                    'is_active': is_active,
                    'onclick': onclick,
                    'element': link_element,
                    'item_element': item
                }
                
                # Determine page type
                if "arrow-left" in onclick or "arrow-left" in str(item.get_attribute("innerHTML")):
                    # Previous button
                    has_prev = True
                    prev_element = link_element
                    page_info['type'] = 'prev'
                    if debug:
                        print(f"  Previous button: {text}")
                elif "arrow-right" in onclick or "arrow-right" in str(item.get_attribute("innerHTML")):
                    # Next button
                    has_next = True
                    next_element = link_element
                    page_info['type'] = 'next'
                    if debug:
                        print(f"  Next button: {text}")
                elif text.isdigit():
                    # Numbered page
                    page_num = int(text)
                    total_pages = max(total_pages, page_num)
                    page_info['type'] = 'number'
                    page_info['page_number'] = page_num
                    
                    # Check if this is the target page to click
                    if page_number is not None and page_num == page_number:
                        target_element = link_element
                        if debug:
                            print(f"  Target page found: {page_num}")
                    
                    if is_active:
                        current_page = page_num
                        if debug:
                            print(f"  Current page: {page_num} (active)")
                    else:
                        if debug:
                            print(f"  Page {page_num}")
                else:
                    # Other element (like search button)
                    page_info['type'] = 'other'
                    if debug:
                        print(f"  Other element: {text}")
                
                page_elements.append(page_info)
                
            except Exception as e:
                if debug:
                    print(f"Error processing page item {i}: {e}")
                continue
        
        if debug:
            print(f"\nPagination Summary:")
            print(f"  Current page: {current_page}")
            print(f"  Total pages: {total_pages}")
            print(f"  Has previous: {has_prev}")
            print(f"  Has next: {has_next}")
            print(f"  Total elements: {len(page_elements)}")
        
        # Click on target page if specified
        clicked_page = None
        click_success = False
        
        if page_number is not None and target_element is not None:
            # Check if page is already active
            if current_page == page_number:
                if debug:
                    print(f"✅ Page {page_number} is already active")
                clicked_page = page_number
                click_success = True
            else:
                if debug:
                    print(f"Clicking on page {page_number}...")
                
                try:
                    # Ensure the target element is visible and clickable
                    if debug:
                        print("Ensuring target element is visible...")
                    
                    # Scroll to the specific target element
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
                    time.sleep(0.5)
                    
                    # Wait for element to be clickable
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    wait = WebDriverWait(driver, 5)
                    wait.until(EC.element_to_be_clickable(target_element))
                    
                    # Click the element
                    target_element.click()
                    
                    # Wait for page to load
                    if debug:
                        print(f"Waiting {wait_time} seconds for page to load...")
                    time.sleep(wait_time)
                    
                    clicked_page = page_number
                    click_success = True
                    
                    if debug:
                        print(f"✅ Successfully clicked page {page_number}")
                        
                except Exception as e:
                    if debug:
                        print(f"❌ Error clicking page {page_number}: {e}")
                        print("Trying alternative click method...")
                    
                    try:
                        # Alternative click method using JavaScript
                        driver.execute_script("arguments[0].click();", target_element)
                        time.sleep(wait_time)
                        
                        clicked_page = page_number
                        click_success = True
                        
                        if debug:
                            print(f"✅ Successfully clicked page {page_number} using JavaScript")
                            
                    except Exception as js_error:
                        if debug:
                            print(f"❌ JavaScript click also failed: {js_error}")
                        click_success = False
                        
        elif page_number is not None and target_element is None:
            if debug:
                print(f"❌ Page number {page_number} not found")
                available_pages = [p.get('page_number') for p in page_elements if p.get('type') == 'number']
                print(f"Available pages: {available_pages}")
            click_success = False
        
        return {
            'current_page': current_page,
            'total_pages': total_pages,
            'page_elements': page_elements,
            'has_prev': has_prev,
            'has_next': has_next,
            'prev_element': prev_element,
            'next_element': next_element,
            'clicked_page': clicked_page,
            'click_success': click_success,
            'success': True
        }
        
    except Exception as e:
        if debug:
            print(f"❌ Error interacting with pagination: {e}")
        return {
            'current_page': None,
            'total_pages': 0,
            'page_elements': [],
            'has_prev': False,
            'has_next': False,
            'prev_element': None,
            'next_element': None,
            'clicked_page': None,
            'click_success': False,
            'success': False
        }

def click_page_number(driver, page_number: int, pagination_class: str = "pagination", 
                     page_item_class: str = "page-item", page_link_class: str = "page-link",
                     wait_time: int = 2, debug: bool = True) -> bool:
    """
    Click on a specific page number in pagination.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        page_number (int): The page number to click on
        pagination_class (str): CSS class of the pagination container
        page_item_class (str): CSS class of individual page items
        page_link_class (str): CSS class of page links
        wait_time (int): Time to wait after clicking
        debug (bool): If True, prints debug information
    
    Returns:
        bool: True if page was clicked successfully, False otherwise
    """
    if debug:
        print(f"\n=== Clicking Page Number {page_number} ===")
    
    try:
        # Get pagination information
        pagination_info = interact_with_pagination(
            driver, pagination_class, page_item_class, page_link_class, debug
        )
        
        if not pagination_info['success']:
            if debug:
                print("❌ No pagination found")
            return False
        
        # Find the target page element
        target_element = None
        for page_info in pagination_info['page_elements']:
            if (page_info['type'] == 'number' and 
                page_info.get('page_number') == page_number):
                target_element = page_info['element']
                break
        
        if not target_element:
            if debug:
                print(f"❌ Page number {page_number} not found")
                print(f"Available pages: {[p.get('page_number') for p in pagination_info['page_elements'] if p.get('type') == 'number']}")
            return False
        
        # Check if page is already active
        for page_info in pagination_info['page_elements']:
            if (page_info['type'] == 'number' and 
                page_info.get('page_number') == page_number and 
                page_info['is_active']):
                if debug:
                    print(f"✅ Page {page_number} is already active")
                return True
        
        # Click the page
        if debug:
            print(f"Clicking page {page_number}...")
        
        # Scroll to element to ensure it's visible
        driver.execute_script("arguments[0].scrollIntoView(true);", target_element)
        time.sleep(0.5)
        
        # Click the element
        target_element.click()
        
        # Wait for page to load
        if debug:
            print(f"Waiting {wait_time} seconds for page to load...")
        time.sleep(wait_time)
        
        if debug:
            print(f"✅ Successfully clicked page {page_number}")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"❌ Error clicking page {page_number}: {e}")
        return False

def click_next_page(driver, pagination_class: str = "pagination", 
                   page_item_class: str = "page-item", page_link_class: str = "page-link",
                   wait_time: int = 2, debug: bool = True) -> bool:
    """
    Click on the next page button in pagination.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        pagination_class (str): CSS class of the pagination container
        page_item_class (str): CSS class of individual page items
        page_link_class (str): CSS class of page links
        wait_time (int): Time to wait after clicking
        debug (bool): If True, prints debug information
    
    Returns:
        bool: True if next page was clicked successfully, False otherwise
    """
    if debug:
        print(f"\n=== Clicking Next Page ===")
    
    try:
        # Get pagination information
        pagination_info = interact_with_pagination(
            driver, pagination_class, page_item_class, page_link_class, debug
        )
        
        if not pagination_info['success']:
            if debug:
                print("❌ No pagination found")
            return False
        
        if not pagination_info['has_next']:
            if debug:
                print("❌ No next page button found")
            return False
        
        # Click the next button
        if debug:
            print("Clicking next page button...")
        
        # Scroll to element to ensure it's visible
        driver.execute_script("arguments[0].scrollIntoView(true);", pagination_info['next_element'])
        time.sleep(0.5)
        
        # Click the element
        pagination_info['next_element'].click()
        
        # Wait for page to load
        if debug:
            print(f"Waiting {wait_time} seconds for page to load...")
        time.sleep(wait_time)
        
        if debug:
            print("✅ Successfully clicked next page")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"❌ Error clicking next page: {e}")
        return False

def click_prev_page(driver, pagination_class: str = "pagination", 
                   page_item_class: str = "page-item", page_link_class: str = "page-link",
                   wait_time: int = 2, debug: bool = True) -> bool:
    """
    Click on the previous page button in pagination.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        pagination_class (str): CSS class of the pagination container
        page_item_class (str): CSS class of individual page items
        page_link_class (str): CSS class of page links
        wait_time (int): Time to wait after clicking
        debug (bool): If True, prints debug information
    
    Returns:
        bool: True if previous page was clicked successfully, False otherwise
    """
    if debug:
        print(f"\n=== Clicking Previous Page ===")
    
    try:
        # Get pagination information
        pagination_info = interact_with_pagination(
            driver, pagination_class, page_item_class, page_link_class, debug
        )
        
        if not pagination_info['success']:
            if debug:
                print("❌ No pagination found")
            return False
        
        if not pagination_info['has_prev']:
            if debug:
                print("❌ No previous page button found")
            return False
        
        # Click the previous button
        if debug:
            print("Clicking previous page button...")
        
        # Scroll to element to ensure it's visible
        driver.execute_script("arguments[0].scrollIntoView(true);", pagination_info['prev_element'])
        time.sleep(0.5)
        
        # Click the element
        pagination_info['prev_element'].click()
        
        # Wait for page to load
        if debug:
            print(f"Waiting {wait_time} seconds for page to load...")
        time.sleep(wait_time)
        
        if debug:
            print("✅ Successfully clicked previous page")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"❌ Error clicking previous page: {e}")
        return False

def navigate_through_pages(driver, start_page: int = 1, end_page: int = None, 
                         pagination_class: str = "pagination", 
                         page_item_class: str = "page-item", 
                         page_link_class: str = "page-link",
                         wait_time: int = 2, debug: bool = True) -> dict:
    """
    Navigate through a range of pages in pagination.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        start_page (int): Starting page number (default: 1)
        end_page (int): Ending page number (if None, goes to last page)
        pagination_class (str): CSS class of the pagination container
        page_item_class (str): CSS class of individual page items
        page_link_class (str): CSS class of page links
        wait_time (int): Time to wait after each page click
        debug (bool): If True, prints debug information
    
    Returns:
        dict: Dictionary containing navigation results:
            - 'success': Boolean indicating if navigation was successful
            - 'pages_visited': List of page numbers that were successfully visited
            - 'failed_pages': List of page numbers that failed to load
            - 'total_pages': Total number of pages found
            - 'current_page': Final page number reached
    """
    if debug:
        print(f"\n=== Navigating Through Pages ===")
        print(f"Start page: {start_page}")
        print(f"End page: {end_page}")
    
    try:
        # Get initial pagination information
        pagination_info = interact_with_pagination(
            driver, pagination_class, page_item_class, page_link_class, debug
        )
        
        if not pagination_info['success']:
            if debug:
                print("❌ No pagination found")
            return {
                'success': False,
                'pages_visited': [],
                'failed_pages': [],
                'total_pages': 0,
                'current_page': None
            }
        
        total_pages = pagination_info['total_pages']
        if end_page is None:
            end_page = total_pages
        
        if debug:
            print(f"Total pages available: {total_pages}")
            print(f"Will navigate from page {start_page} to page {end_page}")
        
        pages_visited = []
        failed_pages = []
        current_page = pagination_info['current_page']
        
        # Navigate to start page if not already there
        if current_page != start_page:
            if debug:
                print(f"Navigating to start page {start_page}...")
            if click_page_number(driver, start_page, pagination_class, page_item_class, page_link_class, wait_time, debug):
                pages_visited.append(start_page)
                current_page = start_page
            else:
                failed_pages.append(start_page)
                if debug:
                    print(f"❌ Failed to navigate to start page {start_page}")
                return {
                    'success': False,
                    'pages_visited': pages_visited,
                    'failed_pages': failed_pages,
                    'total_pages': total_pages,
                    'current_page': current_page
                }
        
        # Navigate through pages
        for page_num in range(start_page + 1, end_page + 1):
            if debug:
                print(f"\nNavigating to page {page_num}...")
            
            if click_page_number(driver, page_num, pagination_class, page_item_class, page_link_class, wait_time, debug):
                pages_visited.append(page_num)
                current_page = page_num
                if debug:
                    print(f"✅ Successfully navigated to page {page_num}")
            else:
                failed_pages.append(page_num)
                if debug:
                    print(f"❌ Failed to navigate to page {page_num}")
                break  # Stop if we can't navigate to a page
        
        if debug:
            print(f"\nNavigation Summary:")
            print(f"  Pages visited: {pages_visited}")
            print(f"  Failed pages: {failed_pages}")
            print(f"  Final page: {current_page}")
        
        return {
            'success': len(failed_pages) == 0,
            'pages_visited': pages_visited,
            'failed_pages': failed_pages,
            'total_pages': total_pages,
            'current_page': current_page
        }
        
    except Exception as e:
        if debug:
            print(f"❌ Error during page navigation: {e}")
        return {
            'success': False,
            'pages_visited': [],
            'failed_pages': [],
            'total_pages': 0,
            'current_page': None
        }

def interact_with_episode_table(driver, table_selector: str = "tbody", 
                               row_class: str = "ep_style5", 
                               episode_no_attr: str = "data-episode-no",
                               clickable_td_class: str = "font12",
                               episode_number: int = None, wait_time: int = 2, debug: bool = True) -> Optional[dict]:
    """
    Helper function to interact with episode tables.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        table_selector (str): CSS selector for the table body (default: "tbody")
        row_class (str): CSS class of episode rows (default: "ep_style5")
        episode_no_attr (str): Attribute name containing episode number (default: "data-episode-no")
        clickable_td_class (str): CSS class of clickable table cells (default: "font12")
        episode_number (int, optional): If provided, automatically clicks on this episode
        wait_time (int): Time to wait after clicking (if episode_number is provided)
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Dictionary containing:
            - 'episodes': List of episode dictionaries with info and WebElement
            - 'total_episodes': Total number of episodes found
            - 'clicked_episode': Episode number that was clicked (if episode_number was provided)
            - 'click_success': Boolean indicating if episode click was successful (if episode_number was provided)
            - 'success': Boolean indicating if table was found
    """
    if debug:
        print(f"\n=== Interacting with Episode Table ===")
        print(f"Table selector: {table_selector}")
        print(f"Row class: {row_class}")
        print(f"Episode number attribute: {episode_no_attr}")
        print(f"Clickable TD class: {clickable_td_class}")
        if episode_number is not None:
            print(f"Will click on episode number: {episode_number}")
    
    try:
        # Wait for page to load and look for episode-related elements
        if debug:
            print("Waiting for page to load and looking for episode elements...")
        
        # Wait for any episode-related elements to appear
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        wait = WebDriverWait(driver, 10)
        
        # Try to find episode rows directly first
        try:
            episode_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, f"tr.{row_class}")))
            if debug:
                print(f"✅ Found {len(episode_rows)} episode rows directly")
            table_element = episode_rows[0].find_element(By.XPATH, "./..")  # Get parent tbody
        except:
            if debug:
                print("Episode rows not found directly, trying table selectors...")
            
            # Find the table body with multiple selector strategies
            table_selectors = [
                table_selector,
                "tbody",
                "table tbody",
                "div[class*='episode'] tbody",
                "div[class*='list'] tbody",
                "div[class*='table'] tbody",
                "table",
                "div[class*='episode'] table",
                "div[class*='list'] table"
            ]
            
            table_element = None
            for selector in table_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        # Check if any of these elements contain episode rows
                        for element in elements:
                            episode_rows_in_element = element.find_elements(By.CSS_SELECTOR, f"tr.{row_class}")
                            if episode_rows_in_element:
                                table_element = element
                                if debug:
                                    print(f"✅ Found table element with selector: {selector}")
                                    print(f"   Contains {len(episode_rows_in_element)} episode rows")
                                break
                        if table_element:
                            break
                except Exception as e:
                    if debug:
                        print(f"Tried selector '{selector}': {e}")
                    continue
        
        if not table_element:
            if debug:
                print("❌ No table element found")
                print("Trying to find any elements with episode-related classes...")
                
                # Look for any elements that might contain episodes
                all_elements = driver.find_elements(By.CSS_SELECTOR, "*")
                episode_related = []
                for elem in all_elements:
                    try:
                        class_attr = elem.get_attribute("class") or ""
                        if any(keyword in class_attr.lower() for keyword in ['episode', 'ep_', 'list', 'table']):
                            episode_related.append({
                                'tag': elem.tag_name,
                                'class': class_attr,
                                'id': elem.get_attribute("id") or "none"
                            })
                    except:
                        continue
                
                if episode_related:
                    print("Found elements with episode-related classes:")
                    for elem in episode_related[:10]:  # Show first 10
                        print(f"  {elem['tag']} - class: {elem['class']} - id: {elem['id']}")
                else:
                    print("No episode-related elements found")
                
                # Also check the page source for episode-related content
                page_source = driver.page_source
                if "ep_style5" in page_source:
                    print("Found 'ep_style5' in page source")
                if "data-episode-no" in page_source:
                    print("Found 'data-episode-no' in page source")
                if "font12" in page_source:
                    print("Found 'font12' in page source")
            
            return {
                'episodes': [],
                'total_episodes': 0,
                'clicked_episode': None,
                'click_success': False,
                'success': False
            }
        
        # Scroll to table element to ensure it's visible
        if debug:
            print("Scrolling to table element...")
        
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", table_element)
            time.sleep(1)
            if debug:
                print("✅ Successfully scrolled to table element")
        except Exception as e:
            if debug:
                print(f"⚠️  Warning: Could not scroll to table element: {e}")
        
        # Find all episode rows
        episode_rows = table_element.find_elements(By.CSS_SELECTOR, f"tr.{row_class}")
        
        if debug:
            print(f"Found {len(episode_rows)} episode rows")
            
            # Show some debug info about the first few rows
            for i, row in enumerate(episode_rows[:3]):
                try:
                    row_html = row.get_attribute("outerHTML")[:200]
                    print(f"  Row {i+1} HTML preview: {row_html}...")
                except:
                    print(f"  Row {i+1}: Could not get HTML")
        
        # Parse episode information
        episodes = []
        target_element = None  # Element to click if episode_number is provided
        
        for i, row in enumerate(episode_rows):
            try:
                # Get episode number from data attribute
                episode_no = row.get_attribute(episode_no_attr)
                if not episode_no:
                    if debug:
                        print(f"  Row {i+1}: No episode number found in {episode_no_attr}")
                        # Try alternative attributes
                        for attr in ['data-episode', 'data-id', 'data-no', 'id']:
                            alt_episode_no = row.get_attribute(attr)
                            if alt_episode_no:
                                print(f"    Found alternative attribute {attr}: {alt_episode_no}")
                    continue
                
                episode_no = int(episode_no)
                
                # Find the clickable cell (usually the second td with font12 class)
                clickable_cells = row.find_elements(By.CSS_SELECTOR, f"td.{clickable_td_class}")
                clickable_element = None
                if clickable_cells:
                    clickable_element = clickable_cells[0]
                else:
                    # Try alternative selectors for clickable cells
                    alternative_selectors = [
                        "td[onclick]",
                        "td[class*='click']",
                        "td[class*='link']",
                        "td:has(onclick)",
                        "td"
                    ]
                    for selector in alternative_selectors:
                        try:
                            cells = row.find_elements(By.CSS_SELECTOR, selector)
                            if cells:
                                clickable_element = cells[0]  # Take the first one
                                if debug:
                                    print(f"    Found clickable element with selector: {selector}")
                                break
                        except:
                            continue
                
                # Extract episode information
                episode_info = {
                    'index': i,
                    'episode_no': episode_no,
                    'row_element': row,
                    'clickable_element': clickable_element
                }
                
                # Extract link information
                episode_link = None
                if clickable_element:
                    # Try to find href attribute on the clickable element or its children
                    try:
                        # Check if the clickable element itself has an href
                        episode_link = clickable_element.get_attribute('href')
                        
                        # If not, look for <a> tags within the clickable element
                        if not episode_link:
                            link_elements = clickable_element.find_elements(By.CSS_SELECTOR, "a")
                            if link_elements:
                                episode_link = link_elements[0].get_attribute('href')
                        
                        # If still not found, check for onclick that might contain a URL
                        if not episode_link:
                            onclick = clickable_element.get_attribute('onclick')
                            if onclick and ('location.href' in onclick or 'window.open' in onclick):
                                # Try to extract URL from onclick
                                import re
                                url_match = re.search(r"['\"]([^'\"]*\.html?[^'\"]*)['\"]", onclick)
                                if url_match:
                                    episode_link = url_match.group(1)
                        
                        # Also check the parent row for any link information
                        if not episode_link:
                            row_links = row.find_elements(By.CSS_SELECTOR, "a")
                            if row_links:
                                episode_link = row_links[0].get_attribute('href')
                        
                    except Exception as e:
                        if debug:
                            print(f"    Error extracting link for episode {episode_no}: {e}")
                
                episode_info['link'] = episode_link
                
                # Extract text content for additional info
                if clickable_element:
                    text_content = clickable_element.text.strip()
                    episode_info['text_content'] = text_content
                    
                    # Try to extract episode title and other details
                    try:
                        # Look for episode title (usually in <b> tag)
                        title_elements = clickable_element.find_elements(By.CSS_SELECTOR, "b")
                        if title_elements:
                            title_text = title_elements[0].text.strip()
                            episode_info['title'] = title_text
                        
                        # Look for episode number (EP.X)
                        ep_elements = clickable_element.find_elements(By.CSS_SELECTOR, "span[style*='background-color: #eee']")
                        if ep_elements:
                            ep_text = ep_elements[0].text.strip()
                            episode_info['episode_label'] = ep_text
                        
                        # Look for word count
                        word_count_elements = clickable_element.find_elements(By.CSS_SELECTOR, "i.icon.ion-document-text")
                        if word_count_elements:
                            # Get the text after the document icon
                            parent_text = clickable_element.text
                            if "ion-document-text" in parent_text:
                                # Extract number after document icon
                                import re
                                word_match = re.search(r'ion-document-text.*?(\d+)', parent_text)
                                if word_match:
                                    episode_info['word_count'] = int(word_match.group(1))
                        
                        # Look for view count
                        view_elements = clickable_element.find_elements(By.CSS_SELECTOR, "span.episode_count_view")
                        if view_elements:
                            view_text = view_elements[0].text.strip()
                            # Remove commas and convert to int
                            view_count = int(view_text.replace(',', ''))
                            episode_info['view_count'] = view_count
                        
                        # Look for date
                        date_elements = clickable_element.find_elements(By.CSS_SELECTOR, "b[style*='font: normal normal bold 12px']")
                        if date_elements:
                            date_text = date_elements[0].text.strip()
                            episode_info['date'] = date_text
                        
                    except Exception as e:
                        if debug:
                            print(f"  Error extracting details for episode {episode_no}: {e}")
                
                # Check if this is the target episode to click
                if episode_number is not None and episode_no == episode_number:
                    target_element = clickable_element
                    if debug:
                        print(f"  Target episode found: {episode_no}")
                
                episodes.append(episode_info)
                
                if debug:
                    print(f"  Episode {episode_no}: {episode_info.get('title', 'Unknown')} - {episode_info.get('episode_label', '')}")
                
            except Exception as e:
                if debug:
                    print(f"Error processing episode row {i}: {e}")
                continue
        
        if debug:
            print(f"\nEpisode Table Summary:")
            print(f"  Total episodes: {len(episodes)}")
            print(f"  Episode numbers: {[ep['episode_no'] for ep in episodes]}")
        
        # Click on target episode if specified
        clicked_episode = None
        click_success = False
        
        if episode_number is not None and target_element is not None:
            if debug:
                print(f"Clicking on episode {episode_number}...")
            
            try:
                # Ensure the target element is visible and clickable
                if debug:
                    print("Ensuring target element is visible...")
                
                # Scroll to the specific target element
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", target_element)
                time.sleep(0.5)
                
                # Wait for element to be clickable
                wait = WebDriverWait(driver, 5)
                wait.until(EC.element_to_be_clickable(target_element))
                
                # Click the element
                target_element.click()
                
                # Wait for page to load
                if debug:
                    print(f"Waiting {wait_time} seconds for page to load...")
                time.sleep(wait_time)
                
                clicked_episode = episode_number
                click_success = True
                
                if debug:
                    print(f"✅ Successfully clicked episode {episode_number}")
                    
            except Exception as e:
                if debug:
                    print(f"❌ Error clicking episode {episode_number}: {e}")
                    print("Trying alternative click method...")
                
                try:
                    # Alternative click method using JavaScript
                    driver.execute_script("arguments[0].click();", target_element)
                    time.sleep(wait_time)
                    
                    clicked_episode = episode_number
                    click_success = True
                    
                    if debug:
                        print(f"✅ Successfully clicked episode {episode_number} using JavaScript")
                        
                except Exception as js_error:
                    if debug:
                        print(f"❌ JavaScript click also failed: {js_error}")
                    click_success = False
                    
        elif episode_number is not None and target_element is None:
            if debug:
                print(f"❌ Episode number {episode_number} not found")
                available_episodes = [ep['episode_no'] for ep in episodes]
                print(f"Available episodes: {available_episodes}")
            click_success = False
        
        return {
            'episodes': episodes,
            'total_episodes': len(episodes),
            'clicked_episode': clicked_episode,
            'click_success': click_success,
            'success': True
        }
        
    except Exception as e:
        if debug:
            print(f"❌ Error interacting with episode table: {e}")
        return {
            'episodes': [],
            'total_episodes': 0,
            'clicked_episode': None,
            'click_success': False,
            'success': False
        }

def click_episode_by_number(driver, episode_number: int, 
                           table_selector: str = "tbody", 
                           row_class: str = "ep_style5", 
                           episode_no_attr: str = "data-episode-no",
                           clickable_td_class: str = "font12",
                           wait_time: int = 2, debug: bool = True) -> bool:
    """
    Click on a specific episode by episode number.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        episode_number (int): The episode number to click on
        table_selector (str): CSS selector for the table body
        row_class (str): CSS class of episode rows
        episode_no_attr (str): Attribute name containing episode number
        clickable_td_class (str): CSS class of clickable table cells
        wait_time (int): Time to wait after clicking
        debug (bool): If True, prints debug information
    
    Returns:
        bool: True if episode was clicked successfully, False otherwise
    """
    if debug:
        print(f"\n=== Clicking Episode Number {episode_number} ===")
    
    try:
        # Get episode table information and click
        table_info = interact_with_episode_table(
            driver, table_selector, row_class, episode_no_attr, clickable_td_class, 
            episode_number, wait_time, debug
        )
        
        if not table_info['success']:
            if debug:
                print("❌ No episode table found")
            return False
        
        if not table_info['click_success']:
            if debug:
                print(f"❌ Failed to click episode {episode_number}")
            return False
        
        if debug:
            print(f"✅ Successfully clicked episode {episode_number}")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"❌ Error clicking episode {episode_number}: {e}")
        return False

def get_episode_info(driver, episode_number: int = None,
                    table_selector: str = "tbody", 
                    row_class: str = "ep_style5", 
                    episode_no_attr: str = "data-episode-no",
                    clickable_td_class: str = "font12",
                    debug: bool = True) -> Optional[dict]:
    """
    Get information about episodes in the table.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        episode_number (int, optional): If provided, returns info for this specific episode
        table_selector (str): CSS selector for the table body
        row_class (str): CSS class of episode rows
        episode_no_attr (str): Attribute name containing episode number
        clickable_td_class (str): CSS class of clickable table cells
        debug (bool): If True, prints debug information
    
    Returns:
        Optional[dict]: Episode information dictionary
    """
    if debug:
        print(f"\n=== Getting Episode Information ===")
        if episode_number:
            print(f"Looking for episode: {episode_number}")
        else:
            print("Getting all episodes information")
    
    try:
        # Get episode table information
        table_info = interact_with_episode_table(
            driver, table_selector, row_class, episode_no_attr, clickable_td_class, 
            None, 0, debug
        )
        
        if not table_info['success']:
            if debug:
                print("❌ No episode table found")
            return None
        
        if episode_number is not None:
            # Find specific episode
            for episode in table_info['episodes']:
                if episode['episode_no'] == episode_number:
                    if debug:
                        print(f"✅ Found episode {episode_number}")
                    return episode
            
            if debug:
                print(f"❌ Episode {episode_number} not found")
            return None
        else:
            # Return all episodes
            if debug:
                print(f"✅ Found {len(table_info['episodes'])} episodes")
            return table_info['episodes']
        
    except Exception as e:
        if debug:
            print(f"❌ Error getting episode information: {e}")
        return None

def navigate_episodes(driver, start_episode: int = None, end_episode: int = None,
                     table_selector: str = "tbody", 
                     row_class: str = "ep_style5", 
                     episode_no_attr: str = "data-episode-no",
                     clickable_td_class: str = "font12",
                     wait_time: int = 2, debug: bool = True) -> dict:
    """
    Navigate through a range of episodes.
    
    Args:
        driver: Existing WebDriver instance with authenticated session
        start_episode (int, optional): Starting episode number
        end_episode (int, optional): Ending episode number
        table_selector (str): CSS selector for the table body
        row_class (str): CSS class of episode rows
        episode_no_attr (str): Attribute name containing episode number
        clickable_td_class (str): CSS class of clickable table cells
        wait_time (int): Time to wait after each episode click
        debug (bool): If True, prints debug information
    
    Returns:
        dict: Dictionary containing navigation results:
            - 'success': Boolean indicating if navigation was successful
            - 'episodes_clicked': List of episode numbers that were successfully clicked
            - 'failed_episodes': List of episode numbers that failed to load
            - 'total_episodes': Total number of episodes found
            - 'current_episode': Final episode number reached
    """
    if debug:
        print(f"\n=== Navigating Through Episodes ===")
        print(f"Start episode: {start_episode}")
        print(f"End episode: {end_episode}")
    
    try:
        # Get episode table information
        table_info = interact_with_episode_table(
            driver, table_selector, row_class, episode_no_attr, clickable_td_class, 
            None, 0, debug
        )
        
        if not table_info['success']:
            if debug:
                print("❌ No episode table found")
            return {
                'success': False,
                'episodes_clicked': [],
                'failed_episodes': [],
                'total_episodes': 0,
                'current_episode': None
            }
        
        total_episodes = table_info['total_episodes']
        available_episodes = [ep['episode_no'] for ep in table_info['episodes']]
        
        if debug:
            print(f"Total episodes available: {total_episodes}")
            print(f"Available episode numbers: {available_episodes}")
        
        # Determine episode range
        if start_episode is None:
            start_episode = min(available_episodes) if available_episodes else 1
        
        if end_episode is None:
            end_episode = max(available_episodes) if available_episodes else 1
        
        if debug:
            print(f"Will navigate from episode {start_episode} to episode {end_episode}")
        
        episodes_clicked = []
        failed_episodes = []
        current_episode = None
        
        # Navigate through episodes
        for episode_num in range(start_episode, end_episode + 1):
            if episode_num not in available_episodes:
                if debug:
                    print(f"⚠️  Episode {episode_num} not available, skipping...")
                continue
            
            if debug:
                print(f"\nNavigating to episode {episode_num}...")
            
            if click_episode_by_number(driver, episode_num, table_selector, row_class, 
                                     episode_no_attr, clickable_td_class, wait_time, debug):
                episodes_clicked.append(episode_num)
                current_episode = episode_num
                if debug:
                    print(f"✅ Successfully navigated to episode {episode_num}")
            else:
                failed_episodes.append(episode_num)
                if debug:
                    print(f"❌ Failed to navigate to episode {episode_num}")
                break  # Stop if we can't navigate to an episode
        
        if debug:
            print(f"\nNavigation Summary:")
            print(f"  Episodes clicked: {episodes_clicked}")
            print(f"  Failed episodes: {failed_episodes}")
            print(f"  Final episode: {current_episode}")
        
        return {
            'success': len(failed_episodes) == 0,
            'episodes_clicked': episodes_clicked,
            'failed_episodes': failed_episodes,
            'total_episodes': total_episodes,
            'current_episode': current_episode
        }
        
    except Exception as e:
        if debug:
            print(f"❌ Error during episode navigation: {e}")
        return {
            'success': False,
            'episodes_clicked': [],
            'failed_episodes': [],
            'total_episodes': 0,
            'current_episode': None
        }
