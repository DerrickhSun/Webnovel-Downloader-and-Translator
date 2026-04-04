"""Browser UI entry (Selenium + ui/app.html): main menu + shared app shell."""

from __future__ import annotations

import time
from pathlib import Path

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.automated_login import shared_chrome_options
from utils.selenium_utils import create_chrome_driver_with_auto_version


def app_html_path() -> Path:
    return Path(__file__).resolve().parent / "app.html"


def app_file_url() -> str:
    path = app_html_path()
    if not path.is_file():
        raise FileNotFoundError(f"App page not found: {path}")
    return path.as_uri()


def main_menu_file_url() -> str:
    """Same document as the rest of the UI (main menu lives in app.html)."""
    return app_file_url()


def main_menu_html_path() -> Path:
    return app_html_path()


def create_menu_driver(options: Options | None = None):
    """Same Chrome setup as terminal manual_login (avoids stricter bot checks on OAuth)."""
    if options is None:
        options = shared_chrome_options()
    return create_chrome_driver_with_auto_version(options=options, debug=False)


def wait_for_main_menu_choice(driver: WebDriver) -> str:
    """
    Load app.html and block until the user picks a main action (click or keys 1–4).
    """
    driver.get(app_file_url())
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "menu-root")))
    driver.execute_script("window.App.resetMainMenu();")
    while True:
        time.sleep(0.1)
        choice = driver.find_element(By.ID, "menu-root").get_attribute("data-choice")
        if choice:
            return str(choice)
