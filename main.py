import text_utils
import dict_utils
from dotenv import load_dotenv
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from collections.abc import Callable
from typing import Protocol

from ui import menu_browser
from ui.browser_prompts import PromptCancelled, WebPrompts
import scrapers.novelpiaScraper as novelpiaScraper
import scrapers.qidianScraper as qidianScraper
import scrapers.wattpadScraper as wattpadScraper
import scrapers.fsacgScraper as fsacgScraper

load_dotenv()


class Prompts(Protocol):
    def info(self, message: str) -> None: ...

    def text(self, message: str, *, placeholder: str = "", default: str = "") -> str: ...

    def yes_no(self, message: str) -> bool: ...

    def choice(self, message: str, options: list[tuple[str, str]]) -> str: ...


class TerminalPrompts:
    """Original stdin/stdout prompts for terminal_main.py."""

    def info(self, message: str) -> None:
        print(message)

    def text(self, message: str, *, placeholder: str = "", default: str = "") -> str:
        return input(message)

    def yes_no(self, message: str) -> bool:
        return input(message).lower().strip() == "y"

    def choice(self, message: str, options: list[tuple[str, str]]) -> str:
        print(message)
        for i, (_oid, lab) in enumerate(options, start=1):
            print(f"  {i}) {lab}")
        raw = input("Your choice (id or number): ").strip().lower()
        ids = [o[0] for o in options]
        if raw in ids:
            return raw
        if raw == "1" and len(options) >= 1:
            return options[0][0]
        if raw == "2" and len(options) >= 2:
            return options[1][0]
        return raw


def _is_fsacg_url(url: str) -> bool:
    """SFACG hosts use sfacg.com; some bookmarks may say 'fsacg'."""
    u = url.lower()
    return "sfacg" in u or "fsacg" in u


def download_novel(*, prompts: Prompts, scrape_driver=None) -> None:
    url = str(prompts.text("Novel name or URL: "))

    url_dict = dict_utils.load_dict("url_dict")
    context_dict = dict_utils.load_dict("context_dict")
    name_dict = dict_utils.load_dict("name_dict")
    manual_name_translation_dict = dict_utils.load_dict("manual_name_translation_dict")

    if text_utils.normalize_text(url) in url_dict.keys():
        url = url_dict[text_utils.normalize_text(url)]

    if url in context_dict.keys():
        prompts.info("Found saved context for this novel")
    else:
        prompts.info("No saved context found for this novel")

    name = "unrecognized"
    if url in name_dict.keys():
        name = name_dict[url]
    prompts.info("Title: " + name)

    manual_name_translation = {}
    if url in manual_name_translation_dict.keys():
        prompts.info("Found manual name translation for this novel")
        manual_name_translation = manual_name_translation_dict[url]

    text_utils.ensure_directory_exists(
        "texts/inprogress_translations/" + name + "/translated"
    )
    text_utils.ensure_directory_exists(
        "texts/inprogress_translations/" + name + "/untranslated"
    )

    pickup = prompts.yes_no("Pickup from where you left off? (y/n): ")
    if pickup:
        start_chapter = (
            text_utils.get_last_chapter_number(
                "texts/inprogress_translations/" + name + "/translated", debug=False
            )
            + 1
        )
        end_chapter = 9999
    else:
        start_chapter = 0
        end_chapter = 9999
    prompts.info("Starting from chapter " + str(start_chapter))

    use_login = prompts.yes_no("Login first? (y/n): ")
    if scrape_driver is not None and use_login:
        prompts.info("The same browser window will open the novel site so you can sign in.")

    if "novelpia" in url:
        novelpiaScraper.novelpia_scrape(
            url,
            name,
            start_chapter,
            end_chapter,
            manual_name_translation,
            use_login=use_login,
            browser_driver=scrape_driver,
        )
    elif "qidian" in url:
        qidianScraper.qidian_scrape(
            url,
            name,
            start_chapter,
            end_chapter,
            manual_name_translation,
            use_login=use_login,
            browser_driver=scrape_driver,
        )
    elif "wattpad" in url:
        wattpadScraper.wattpad_scrape(
            url,
            name,
            start_chapter,
            end_chapter,
            manual_name_translation,
            use_login=use_login,
            browser_driver=scrape_driver,
        )
    elif _is_fsacg_url(url):
        fsacgScraper.fsacg_scrape(
            url,
            name,
            start_chapter,
            end_chapter,
            manual_name_translation,
            use_login=use_login,
            browser_driver=scrape_driver,
        )
    else:
        prompts.info("Unsupported site")


def update_library(*, prompts: Prompts) -> None:
    op = prompts.choice(
        "Update library — choose an operation:",
        [("add", "Add novel"), ("remove", "Remove title")],
    )
    match op:
        case "add":
            dict_utils.add_novel(
                read_str=lambda p: prompts.text(p),
                read_yes_no=prompts.yes_no,
                echo=prompts.info,
            )
        case "remove":
            dict_utils.remove_title(
                read_str=lambda p: prompts.text(p),
                echo=prompts.info,
            )
        case _:
            prompts.info("Unknown operation. Use add or remove.")


def package_novel(*, prompts: Prompts) -> None:
    try:
        while True:
            name = prompts.text(
                "Enter the name of the volume (folder under texts/finished_translations/), "
                "or leave blank / type exit to finish: "
            ).strip()
            if name == "" or name.lower() == "exit":
                break
            text_utils.convert_to_volume(name, "texts/finished_translations/" + name)
    except Exception as e:
        prompts.info(f"Error: {str(e)}")


def _run_browser_action(driver, fn: Callable[[], None]) -> None:
    driver.execute_script("App.beginWizard();")
    try:
        fn()
    except PromptCancelled:
        print("Cancelled.")
    finally:
        # Download may navigate the same window to the novel site; reload app.html so
        # window.App exists again (endWizard alone would fail off-origin).
        try:
            driver.get(menu_browser.app_file_url())
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "menu-root"))
            )
            driver.execute_script("App.resetMainMenu();")
        except WebDriverException:
            pass


def main() -> None:
    print("Opening the app in your browser (menu and prompts).")
    print("Logs from scrapers may still appear in this terminal.\n")

    driver = None
    try:
        driver = menu_browser.create_menu_driver()
        while True:
            try:
                choice = menu_browser.wait_for_main_menu_choice(driver)
            except WebDriverException:
                print("Browser was closed. Goodbye.")
                break

            if choice == "exit":
                print("Goodbye.")
                break

            if choice == "download":
                _run_browser_action(
                    driver,
                    lambda: download_novel(
                        prompts=WebPrompts(driver), scrape_driver=driver
                    ),
                )
            elif choice == "update_library":
                _run_browser_action(
                    driver, lambda: update_library(prompts=WebPrompts(driver))
                )
            elif choice == "package":
                _run_browser_action(
                    driver, lambda: package_novel(prompts=WebPrompts(driver))
                )
            else:
                print(f"Unknown menu action: {choice!r}. Choose again in the browser.")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except WebDriverException:
                pass


if __name__ == "__main__":
    main()
