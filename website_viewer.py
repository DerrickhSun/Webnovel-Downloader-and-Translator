#!/usr/bin/env python3
"""
Website Viewer & Analyzer
- Sets up Selenium with confirmed headers and anti-bot evasion
- Navigates to a page
- Runs rendering diagnostics (shadow DOM, canvas, custom fonts, hidden/zero-dim text, iframes)
- Takes a screenshot
- Saves the HTML
- Collects detailed network activity (requests/responses with status codes and cookies)
- Allows specifying a main content selector (id or class)
"""

import os
import re
import json
import time
from datetime import datetime
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import automated_login
#from web_scraper import CONFIRMED_HEADERS

CONFIRMED_HEADERS = {
    'Host': 'novelpia.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Referer': 'https://novelpia.com/proc/login_google?code=4%2F0AVMBsJhc5uEhHhQJ3M9raP2fQj_LJlss5_prv81d8hIwNrvEzBwxPedOPnI5ETLcqVdiIg&scope=email+profile+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile+openid&authuser=0&prompt=none',
    'DNT': '1',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Cookie': 'NPD26061=meta; USERKEY=e0d9e95b5126f0808a8ba9b3a0c42823; LOGINKEY=f15bf96875219792a5f6708add5d5ca6_998f4c9291773a2782ffab9c86a3aa35; NPK0626=OObWV0YQ..; SITE_LANG=ko-KR; REF_DATA=%2Fnovel%2F191512; event_100_modal=0; PRIVATE_MODE=error; _fwb=107tGxxgsek80y2EBEoGD76.1750933556830; wcs_bt=s_5a2fcdbcc8d9:1750933556; modal_flag_type=1; induce_flag_type=22; induce_type=3; induce_is_first=false; _gcl_au=1.1.2014588136.1750933557; _ga_MBDFP7GFRG=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _ga=GA1.1.2065044773.1750933558; _ga_JNNCJXPDKK=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _ga_E57NBH6NLW=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _ga_X2P0SJ3118=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _ga_BYJSXXWHC9=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _ga_PVNN9Q68K3=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _ga_D026D2382N=GS2.1.s1750933557$o1$g0$t1750933562$j55$l0$h0; _wp_uid=1-05ead9d40e5e86b2b098d1a86a2b31dc-s1750933558.58172|windows_10|firefox-1qhz3p1; _redirectrurl=L25vdmVsLzE5MTUxMg%3D%3D; general_access=OOOTYwYzMwZmE4NDI5YzRiZWRlZTk0NWQwODk2ZDIzNTE.; novelpia_login=1; AUTOLOGIN=3800495; last_login=google',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'TE': 'trailers',
    'Priority': 'u=0, i',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache'
}

# --- Utility: Setup Selenium with Confirmed Headers ---
def setup_selenium_with_confirmed_headers(debug=True):
    options = uc.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={CONFIRMED_HEADERS['User-Agent']}")
    options.add_argument(f"--accept-language={CONFIRMED_HEADERS['Accept-Language']}")
    
    # Set cookies from CONFIRMED_HEADERS
    if 'Cookie' in CONFIRMED_HEADERS:
        options.add_argument(f"--cookie={CONFIRMED_HEADERS['Cookie']}")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Enable detailed logging for network activity
    options.set_capability('goog:loggingPrefs', {
        'performance': 'ALL',
        'browser': 'ALL'
    })
    
    driver = uc.Chrome(options=options)
    
    # Enable network monitoring via CDP
    try:
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Performance.enable', {})
        
        # Set only essential headers using CDP (avoid problematic ones)
        essential_headers = {
            'Accept': CONFIRMED_HEADERS['Accept'],
            'Accept-Encoding': CONFIRMED_HEADERS['Accept-Encoding'],
            'Referer': CONFIRMED_HEADERS['Referer'],
            'DNT': CONFIRMED_HEADERS['DNT'],
            'Sec-GPC': CONFIRMED_HEADERS['Sec-GPC'],
            'Connection': CONFIRMED_HEADERS['Connection'],
            'Upgrade-Insecure-Requests': CONFIRMED_HEADERS['Upgrade-Insecure-Requests'],
            'Sec-Fetch-Dest': CONFIRMED_HEADERS['Sec-Fetch-Dest'],
            'Sec-Fetch-Mode': CONFIRMED_HEADERS['Sec-Fetch-Mode'],
            'Sec-Fetch-Site': CONFIRMED_HEADERS['Sec-Fetch-Site']
        }
        
        # Remove any None or empty values
        essential_headers = {k: v for k, v in essential_headers.items() if v and v.strip()}
        
        if essential_headers:
            driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                'headers': essential_headers
            })
            if debug:
                print(f"Set essential headers via CDP: {list(essential_headers.keys())}")
        
        if debug:
            print("CDP network monitoring enabled.")
    except Exception as e:
        if debug:
            print(f"Could not enable CDP network monitoring: {e}")
    
    # Evasion: override navigator properties, etc.
    driver.execute_script(f'''
        Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
        Object.defineProperty(navigator, 'plugins', {{get: () => [1,2,3,4,5]}});
        Object.defineProperty(navigator, 'languages', {{get: () => ['en-US', 'en']}});
        Object.defineProperty(navigator, 'chrome', {{get: () => ({{runtime: {{}}, loadTimes: function() {{}}, csi: function() {{}}, app: {{}}}})}});
        Object.defineProperty(document, 'referrer', {{get: function() {{ return '{CONFIRMED_HEADERS.get('Referer', '')}'; }}}});
        
        // Override fetch to add custom headers (simplified)
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {{}}) {{
            options.headers = options.headers || {{}};
            
            // Add only essential headers
            const essentialHeaders = {{
                'Accept': '{CONFIRMED_HEADERS.get('Accept', '')}',
                'Accept-Encoding': '{CONFIRMED_HEADERS.get('Accept-Encoding', '')}',
                'Referer': '{CONFIRMED_HEADERS.get('Referer', '')}',
                'DNT': '{CONFIRMED_HEADERS.get('DNT', '')}',
                'Connection': '{CONFIRMED_HEADERS.get('Connection', '')}',
                'Upgrade-Insecure-Requests': '{CONFIRMED_HEADERS.get('Upgrade-Insecure-Requests', '')}',
                'Sec-Fetch-Dest': '{CONFIRMED_HEADERS.get('Sec-Fetch-Dest', '')}',
                'Sec-Fetch-Mode': '{CONFIRMED_HEADERS.get('Sec-Fetch-Mode', '')}',
                'Sec-Fetch-Site': '{CONFIRMED_HEADERS.get('Sec-Fetch-Site', '')}'
            }};
            
            for (const [key, value] of Object.entries(essentialHeaders)) {{
                if (value && value.trim()) {{
                    options.headers[key] = value;
                }}
            }}
            
            return originalFetch(url, options);
        }};
        
        // Override XMLHttpRequest to add custom headers (simplified)
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url, ...args) {{
            const result = originalOpen.apply(this, [method, url, ...args]);
            
            // Add only essential headers after open
            const essentialHeaders = {{
                'Accept': '{CONFIRMED_HEADERS.get('Accept', '')}',
                'Accept-Encoding': '{CONFIRMED_HEADERS.get('Accept-Encoding', '')}',
                'Referer': '{CONFIRMED_HEADERS.get('Referer', '')}',
                'DNT': '{CONFIRMED_HEADERS.get('DNT', '')}',
                'Connection': '{CONFIRMED_HEADERS.get('Connection', '')}',
                'Upgrade-Insecure-Requests': '{CONFIRMED_HEADERS.get('Upgrade-Insecure-Requests', '')}',
                'Sec-Fetch-Dest': '{CONFIRMED_HEADERS.get('Sec-Fetch-Dest', '')}',
                'Sec-Fetch-Mode': '{CONFIRMED_HEADERS.get('Sec-Fetch-Mode', '')}',
                'Sec-Fetch-Site': '{CONFIRMED_HEADERS.get('Sec-Fetch-Site', '')}'
            }};
            
            for (const [key, value] of Object.entries(essentialHeaders)) {{
                if (value && value.trim()) {{
                    this.setRequestHeader(key, value);
                }}
            }}
            
            return result;
        }};
    ''')
    
    if debug:
        print("Selenium driver set up with essential headers.")
        print(f"Using essential headers: {list(essential_headers.keys())}")
    return driver

# --- Network Activity Collection ---
def collect_network_activity(driver, debug=True):
    """Collect detailed network activity including requests, responses, status codes, and cookies."""
    network_data = {
        'requests': [],
        'responses': [],
        'cookies_sent': [],
        'cookies_received': [],
        'failed_requests': [],
        'browser_cookies': [],  # Add browser cookies
        'summary': {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'domains': set(),
            'status_codes': {},
            'content_types': {}
        }
    }
    
    # First, get all cookies from the browser
    try:
        browser_cookies = driver.get_cookies()
        network_data['browser_cookies'] = browser_cookies
        if debug:
            print(f"Browser has {len(browser_cookies)} cookies:")
            for cookie in browser_cookies:
                print(f"  {cookie['name']}: {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}")
    except Exception as e:
        if debug:
            print(f"Could not get browser cookies: {e}")
    
    try:
        # Get performance logs (CDP)
        logs = driver.get_log('performance')
        
        for log in logs:
            try:
                message = json.loads(log['message'])
                if 'message' in message:
                    method = message['message']['method']
                    params = message['message'].get('params', {})
                    
                    if method == 'Network.requestWillBeSent':
                        request_info = {
                            'requestId': params.get('requestId'),
                            'url': params.get('request', {}).get('url'),
                            'method': params.get('request', {}).get('method'),
                            'headers': params.get('request', {}).get('headers', {}),
                            'timestamp': params.get('timestamp'),
                            'type': params.get('type'),
                            'frameId': params.get('frameId')
                        }
                        network_data['requests'].append(request_info)
                        network_data['summary']['total_requests'] += 1
                        
                        # Extract cookies from request headers (improved detection)
                        headers = request_info['headers']
                        
                        # Check for Cookie header
                        if 'Cookie' in headers:
                            cookies = headers['Cookie'].split('; ')
                            for cookie in cookies:
                                if '=' in cookie:
                                    name, value = cookie.split('=', 1)
                                    network_data['cookies_sent'].append({
                                        'requestId': request_info['requestId'],
                                        'url': request_info['url'],
                                        'name': name.strip(),
                                        'value': value.strip(),
                                        'source': 'Cookie_header'
                                    })
                        
                        # Also check for cookie in lowercase (some implementations)
                        if 'cookie' in headers:
                            cookies = headers['cookie'].split('; ')
                            for cookie in cookies:
                                if '=' in cookie:
                                    name, value = cookie.split('=', 1)
                                    network_data['cookies_sent'].append({
                                        'requestId': request_info['requestId'],
                                        'url': request_info['url'],
                                        'name': name.strip(),
                                        'value': value.strip(),
                                        'source': 'cookie_header_lowercase'
                                    })
                        
                        # Track domains
                        if request_info['url']:
                            domain = urlparse(request_info['url']).netloc
                            if domain:
                                network_data['summary']['domains'].add(domain)
                    
                    elif method == 'Network.responseReceived':
                        response_info = {
                            'requestId': params.get('requestId'),
                            'url': params.get('response', {}).get('url'),
                            'status': params.get('response', {}).get('status'),
                            'statusText': params.get('response', {}).get('statusText'),
                            'headers': params.get('response', {}).get('headers', {}),
                            'mimeType': params.get('response', {}).get('mimeType'),
                            'encodedDataLength': params.get('response', {}).get('encodedDataLength'),
                            'timestamp': params.get('timestamp')
                        }
                        network_data['responses'].append(response_info)
                        
                        # Track status codes
                        status = response_info['status']
                        if status:
                            network_data['summary']['status_codes'][status] = \
                                network_data['summary']['status_codes'].get(status, 0) + 1
                            
                            if status >= 200 and status < 400:
                                network_data['summary']['successful_requests'] += 1
                            else:
                                network_data['summary']['failed_requests'] += 1
                                network_data['failed_requests'].append(response_info)
                        
                        # Track content types
                        mime_type = response_info['mimeType']
                        if mime_type:
                            network_data['summary']['content_types'][mime_type] = \
                                network_data['summary']['content_types'].get(mime_type, 0) + 1
                        
                        # Extract cookies from response headers (improved detection)
                        headers = response_info['headers']
                        
                        # Check for Set-Cookie header (case insensitive)
                        set_cookie_headers = []
                        for header_name, header_value in headers.items():
                            if header_name.lower() == 'set-cookie':
                                if isinstance(header_value, str):
                                    set_cookie_headers.append(header_value)
                                elif isinstance(header_value, list):
                                    set_cookie_headers.extend(header_value)
                        
                        for cookie_str in set_cookie_headers:
                            # Parse Set-Cookie header
                            cookie_parts = cookie_str.split(';')
                            if cookie_parts:
                                name_value = cookie_parts[0].split('=', 1)
                                if len(name_value) == 2:
                                    name, value = name_value
                                    cookie_info = {
                                        'requestId': response_info['requestId'],
                                        'url': response_info['url'],
                                        'name': name.strip(),
                                        'value': value.strip(),
                                        'full_cookie': cookie_str,
                                        'source': 'Set-Cookie_header'
                                    }
                                    network_data['cookies_received'].append(cookie_info)
                    
                    elif method == 'Network.loadingFailed':
                        failed_info = {
                            'requestId': params.get('requestId'),
                            'url': params.get('requestId'),  # We'll match this with request data
                            'errorText': params.get('errorText'),
                            'timestamp': params.get('timestamp')
                        }
                        network_data['failed_requests'].append(failed_info)
                        network_data['summary']['failed_requests'] += 1
                        
            except json.JSONDecodeError:
                continue
            except Exception as e:
                if debug:
                    print(f"Error processing log entry: {e}")
                continue
        
        # Convert sets to lists for JSON serialization
        network_data['summary']['domains'] = list(network_data['summary']['domains'])
        
        if debug:
            print(f"Collected {len(network_data['requests'])} requests")
            print(f"Collected {len(network_data['responses'])} responses")
            print(f"Collected {len(network_data['cookies_sent'])} cookies sent")
            print(f"Collected {len(network_data['cookies_received'])} cookies received")
            print(f"Browser cookies: {len(network_data['browser_cookies'])}")
            print(f"Failed requests: {len(network_data['failed_requests'])}")
        
    except Exception as e:
        if debug:
            print(f"Error collecting network activity: {e}")
    
    return network_data

# --- Main Analyzer Function ---
def analyze_website(
    url,
    output_dir="debug/website_viewer_output",
    main_id=None,
    main_class=None,
    debug=True
):
    os.makedirs(output_dir, exist_ok=True)
    driver = automated_login.manual_login(url, debug=False)['driver']
    #driver = setup_selenium_with_confirmed_headers(debug=debug)
    try:
        driver.get(url)
        time.sleep(5)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        if debug:
            print(f"Loaded: {driver.current_url}")
        # --- Screenshot ---
        screenshot_path = os.path.join(output_dir, "screenshot.png")
        driver.save_screenshot(screenshot_path)
        if debug:
            print(f"Screenshot saved: {screenshot_path}")
        # --- HTML ---
        html_path = os.path.join(output_dir, "page_source.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        if debug:
            print(f"HTML saved: {html_path}")
        # --- Rendering Diagnostics ---
        diagnostics = {}
        # Shadow DOM
        shadow_dom = driver.execute_script('''
            return Array.from(document.querySelectorAll('*')).filter(el => el.shadowRoot)
                .map(el => ({tagName: el.tagName, id: el.id, className: el.className, shadowText: el.shadowRoot.textContent.substring(0,200)}));
        ''')
        diagnostics['shadow_dom'] = shadow_dom
        # Canvas
        canvas = driver.execute_script('''
            return Array.from(document.querySelectorAll('canvas')).map(c => ({width: c.width, height: c.height, visible: c.offsetWidth>0&&c.offsetHeight>0}));
        ''')
        diagnostics['canvas'] = canvas
        # Custom fonts
        custom_fonts = driver.execute_script('''
            return Array.from(document.querySelectorAll('*')).filter(el => {
                const fam = window.getComputedStyle(el).fontFamily.toLowerCase();
                return fam && !fam.includes('arial') && !fam.includes('sans-serif') && !fam.includes('serif') && !fam.includes('monospace') && !fam.includes('system-ui');
            }).map(el => ({tagName: el.tagName, className: el.className, fontFamily: window.getComputedStyle(el).fontFamily, text: el.textContent.substring(0,100)}));
        ''')
        diagnostics['custom_fonts'] = custom_fonts
        # Hidden text
        hidden_text = driver.execute_script('''
            return Array.from(document.querySelectorAll('*')).filter(el => {
                const s = window.getComputedStyle(el);
                return el.textContent.trim().length>0 && (s.display==='none'||s.visibility==='hidden'||s.opacity==='0');
            }).map(el => ({tagName: el.tagName, className: el.className, text: el.textContent.substring(0,100)}));
        ''')
        diagnostics['hidden_text'] = hidden_text
        # Zero-dimension text
        zero_dim = driver.execute_script('''
            return Array.from(document.querySelectorAll('*')).filter(el => el.textContent.trim().length>0 && el.offsetWidth===0 && el.offsetHeight===0).map(el => ({tagName: el.tagName, className: el.className, text: el.textContent.substring(0,100)}));
        ''')
        diagnostics['zero_dim_text'] = zero_dim
        # Iframes
        iframes = driver.execute_script('''
            return Array.from(document.querySelectorAll('iframe')).map(iframe => ({src: iframe.src, width: iframe.offsetWidth, height: iframe.offsetHeight, visible: iframe.offsetWidth>0&&iframe.offsetHeight>0}));
        ''')
        diagnostics['iframes'] = iframes
        # Save diagnostics
        diag_path = os.path.join(output_dir, "rendering_diagnostics.json")
        with open(diag_path, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2, ensure_ascii=False)
        if debug:
            print(f"Rendering diagnostics saved: {diag_path}")
        # --- Enhanced Network Activity Collection ---
        if debug:
            print("Collecting detailed network activity...")
        network_data = collect_network_activity(driver, debug=debug)
        
        # Save detailed network data
        net_path = os.path.join(output_dir, "network_activity.json")
        with open(net_path, "w", encoding="utf-8") as f:
            json.dump(network_data, f, indent=2, ensure_ascii=False)
        if debug:
            print(f"Detailed network activity saved: {net_path}")
        
        # Save network summary separately for easy reading
        summary_path = os.path.join(output_dir, "network_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(network_data['summary'], f, indent=2, ensure_ascii=False)
        if debug:
            print(f"Network summary saved: {summary_path}")
        
        # --- Main Content Extraction (optional) ---
        main_content = None
        if main_id:
            try:
                elem = driver.find_element(By.ID, main_id)
                main_content = elem.get_attribute("outerHTML")
            except Exception as e:
                if debug:
                    print(f"Could not find main element by id '{main_id}': {e}")
        elif main_class:
            try:
                elem = driver.find_element(By.CLASS_NAME, main_class)
                main_content = elem.get_attribute("outerHTML")
            except Exception as e:
                if debug:
                    print(f"Could not find main element by class '{main_class}': {e}")
        if main_content:
            main_path = os.path.join(output_dir, "main_content.html")
            with open(main_path, "w", encoding="utf-8") as f:
                f.write(main_content)
            if debug:
                print(f"Main content saved: {main_path}")
        # --- Summary ---
        if debug:
            print("\nSummary:")
            print(f"  Screenshot: {screenshot_path}")
            print(f"  HTML: {html_path}")
            print(f"  Rendering diagnostics: {diag_path}")
            print(f"  Network activity: {net_path}")
            print(f"  Network summary: {summary_path}")
            if main_content:
                print(f"  Main content: {main_path}")
            
            # Print network summary
            print(f"\nNetwork Summary:")
            print(f"  Total requests: {network_data['summary']['total_requests']}")
            print(f"  Successful: {network_data['summary']['successful_requests']}")
            print(f"  Failed: {network_data['summary']['failed_requests']}")
            print(f"  Domains: {len(network_data['summary']['domains'])}")
            print(f"  Cookies sent: {len(network_data['cookies_sent'])}")
            print(f"  Cookies received: {len(network_data['cookies_received'])}")
            print(f"  Browser cookies: {len(network_data['browser_cookies'])}")
            
            if network_data['summary']['status_codes']:
                print(f"  Status codes: {dict(network_data['summary']['status_codes'])}")
            
            # Show browser cookies if any
            if network_data['browser_cookies']:
                print(f"\nBrowser Cookies:")
                for cookie in network_data['browser_cookies']:
                    print(f"  {cookie['name']}: {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # Example usage
    url = "https://novelpia.com/viewer/2358757"
    analyze_website(url, debug=True) 