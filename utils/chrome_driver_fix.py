#!/usr/bin/env python3
"""
ChromeDriver Version Fix Utility
Helps diagnose and fix ChromeDriver version compatibility issues
"""

import sys
import subprocess
import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def get_chrome_version():
    """Get the current Chrome browser version."""
    try:
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        version = line.split()[-1]
                        return version
        else:
            # Linux/Mac
            result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split()[-1]
                return version
    except Exception as e:
        print(f"Warning: Could not detect Chrome version: {e}")

    return None


def test_chromedriver_installation():
    """Test if ChromeDriver is properly installed and working using Selenium."""
    try:
        # Try to create a driver using Selenium Manager
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        print("🔍 Testing ChromeDriver creation via Selenium...")
        driver = webdriver.Chrome(options=options)
        print("ChromeDriver created successfully!")
        driver.quit()
        return True

    except Exception as e:
        print(f"ChromeDriver test failed: {e}")
        return False


def main():
    """Main function to diagnose ChromeDriver issues."""
    print("🔍 ChromeDriver Version Diagnostic Tool")
    print("=" * 50)

    # Get Chrome version
    chrome_version = get_chrome_version()
    if chrome_version:
        print(f"🔍 Detected Chrome version: {chrome_version}")
        major_version = chrome_version.split('.')[0]
        print(f"🔍 Major version: {major_version}")
    else:
        print("Could not detect Chrome version")
        print("   Make sure Chrome browser is installed")
        return

    # Test ChromeDriver
    if test_chromedriver_installation():
        print("\nChromeDriver is working correctly!")
        print("   No further action needed.")
    else:
        print("\nChromeDriver has issues. Here are suggestions:")
        print("\n1. Ensure you have a recent selenium version:")
        print("   pip install --upgrade selenium")

        print("\n2. Make sure Chrome browser is up to date")

        print("\n3. If problems persist, try:")
        print("   - Close all Chrome browser instances")
        print("   - Restart your computer")
        print("   - Reinstall Chrome browser")

        print(f"\n4. Manual ChromeDriver download (if needed):")
        print(f"   Download ChromeDriver version {major_version} from:")
        print("   https://chromedriver.chromium.org/")
        print("   Place it in your PATH or project directory")


if __name__ == "__main__":
    main()