"""
Open ui/app.html in Chrome and print each main-menu button press.

Run from the project root (recommended):
    python ui/menu_selenium_demo.py

Press Ctrl+C in the terminal to stop. Choosing Exit prints and closes the browser.
"""

from __future__ import annotations

import sys
import time

from ui import menu_browser


def main() -> None:
    if not menu_browser.main_menu_html_path().is_file():
        print(f"Missing menu file: {menu_browser.main_menu_html_path()}", file=sys.stderr)
        sys.exit(1)

    driver = menu_browser.create_menu_driver()
    try:
        driver.get(menu_browser.main_menu_file_url())

        print(f"Opened {menu_browser.main_menu_file_url()}")
        print("Click buttons in the browser; choices are printed here. Ctrl+C to quit.\n")

        seen = 0
        labels = {
            "download": "Download novel",
            "update_library": "Update library",
            "package": "Package novel",
            "exit": "Exit",
        }

        while True:
            time.sleep(0.15)
            presses: list = driver.execute_script("return window.__menuPresses || [];")
            while seen < len(presses):
                choice = presses[seen]
                seen += 1
                label = labels.get(choice, choice)
                print(f"Button pressed: {choice!r} ({label})")
                if choice == "exit":
                    print("Exit chosen — closing browser.")
                    return
    except KeyboardInterrupt:
        print("\nStopped (Ctrl+C).")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
