#!/usr/bin/env python3
"""
Automated Login Script
Automates the login process instead of copying cookies
"""

import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
from web_scraper import CONFIRMED_HEADERS
from utils.selenium_utils import create_chrome_driver_with_auto_version

def manual_login(url="https://novelpia.com/", wait_time=60, debug=True):
    """Open browser and wait for manual login - most reliable approach."""
    
    def handle_alerts(driver, context=""):
        """Helper function to handle any open alerts."""
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            if debug:
                print(f"⚠️  Alert detected {context}: {alert_text}")
                print("   Please handle the alert manually in the browser")
            # Don't dismiss - let user handle manually
            driver.switch_to.default_content()
            return True
        except:
            return False
    
    options = uc.ChromeOptions()
    # Non-headless mode for manual interaction
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={CONFIRMED_HEADERS['User-Agent']}")
    options.add_argument(f"--accept-language={CONFIRMED_HEADERS['Accept-Language']}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Enable detailed logging
    options.set_capability('goog:loggingPrefs', {
        'performance': 'ALL',
        'browser': 'ALL'
    })
    
    driver = create_chrome_driver_with_auto_version(options=options, debug=debug)
    
    try:
        # Enable network monitoring via CDP
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Performance.enable', {})
        
        if debug:
            print("🔐 MANUAL LOGIN PROCESS")
            print("=" * 60)
            print(f"Target URL: {url}")
            print(f"Wait time: {wait_time} seconds")
            print("Please complete the login process manually in the browser.")
        
        # STEP 1: Navigate to the main site
        if debug:
            print("\nStep 1: Navigating to main site...")
        
        # Handle any alerts before starting
        handle_alerts(driver, "before navigation")
        
        driver.get(url)
        
        # STEP 2: Wait for page to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            # Handle alerts that might prevent page load
            handle_alerts(driver, "during page load")
            # Try again
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        
        if debug:
            print("Step 2: Page loaded successfully")
            print("Step 3: Waiting for manual login...")
            print(f"⏰ You have {wait_time} seconds to complete the login process")
            print("   - Click the user menu icon (top right)")
            print("   - Click 'Google Login' or '구글로 로그인'")
            print("   - Complete Google OAuth login")
            print("   - Wait for redirect back to novelpia.com")
        
        # STEP 3: Wait for manual login
        start_time = time.time()
        logging_in = False
        while time.time() - start_time < wait_time:
            remaining_time = wait_time - (time.time() - start_time)
            
            if debug and int(remaining_time) % 10 == 0 and remaining_time > 0:
                print(f"⏰ {int(remaining_time)} seconds remaining...")
                try:
                    current_url = driver.current_url
                    print(f"   Current URL: {current_url}")
                except:
                    # Handle alerts that might prevent URL access
                    handle_alerts(driver, "while checking URL")
                    try:
                        current_url = driver.current_url
                        print(f"   Current URL: {current_url}")
                    except:
                        print("   Could not get current URL")
            #TODO: add generalization for other sites
            # Check if we're back to novelpia.com (login successful)
            try:
                current_url = driver.current_url
                if "accounts.google.com" in current_url:
                    logging_in = True
                elif "novelpia.com" in current_url and logging_in:
                    if debug:
                        print("✅ Detected return to novelpia.com - login may be successful!")
                    break
            except:
                # Handle alerts that might prevent URL access
                handle_alerts(driver, "while checking login status")
            
            # Handle any alerts that appear during wait
            handle_alerts(driver, "during wait")
            
            time.sleep(1)
        
        print("Login successful")
        
        # TODO: add check for successful login
        return {
            'page_info': page_info,
            'network_data': network_data,
            'output_file': output_file,
            'html_path': html_path,
            'driver': driver  # Return the driver so you can use it later
        }
        
    except Exception as e:
        if debug:
            print(f"❌ Error during manual login: {e}")
        # Don't close the browser on error - let user decide
        return {
            'error': str(e),
            'driver': driver
        }


if __name__ == "__main__":
    # Example usage:
    # automated_login()  # Manual login
    manual_login() 