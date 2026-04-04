"""
Wattpad scraper: chapter list from ul[aria-label="story-parts"], chapter text from pre > p.
"""
import utils.automated_login as automated_login
import scrapers.helpers as helpers
import utils.selenium_utils as selenium_utils
from urllib.parse import urljoin
from translators import Translator
import dspy

try:
    from selenium.common.exceptions import (
        WebDriverException,
        NoSuchWindowException,
        SessionNotCreatedException,
        TimeoutException,
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

STORY_PARTS_SELECTOR = 'ul[aria-label="story-parts"]'  # TOC: chapter links
CHAPTER_CONTENT_SELECTOR = 'pre'  # Chapter text: pre > p elements


def _ensure_story_url(url: str) -> str:
    """Ensure URL is a full Wattpad story or chapter URL."""
    url = url.strip()
    if not url.startswith("http"):
        url = "https://www.wattpad.com" + (url if url.startswith("/") else "/" + url)
    return url


def wattpad_scrape(
    url,
    name,
    start_chapter,
    end_chapter,
    manual_name_translation=None,
    use_login=True,
    browser_driver=None,
):
    if manual_name_translation is None:
        manual_name_translation = {}
    try:
        url = _ensure_story_url(url)
        # Use story root for TOC: Wattpad story URLs are like /story/ID-title
        if "/story/" in url:
            story_base = url.split("?")[0].rstrip("/")
        else:
            # Chapter URL like /123456789-chapter-title -> story is same origin
            story_base = url.split("?")[0].rstrip("/")
            if "/story/" not in story_base:
                # Heuristic: chapter URLs often have form /number-title; story is /story/number-title
                parts = story_base.replace("https://www.wattpad.com", "").strip("/").split("/")
                if parts and parts[0].split("-")[0].isdigit():
                    story_base = "https://www.wattpad.com/story/" + parts[0]

        if use_login:
            login_result = automated_login.manual_login(
                url="https://www.wattpad.com/", debug=False, existing_driver=browser_driver
            )
        else:
            login_result = automated_login.get_driver_no_login(
                debug=False, existing_driver=browser_driver
            )
        driver = login_result["driver"]

        # Fetch story page: get chapter list from ul[aria-label="story-parts"]
        result = selenium_utils.fetch_with_existing_driver_css(
            driver, story_base, STORY_PARTS_SELECTOR, wait_time=5, timeout=30, debug=False
        )
        if not result or not result.get("success"):
            print("Could not load story parts list from Wattpad.")
            return

        chapter_urls = result.get("urls") or []
        # Resolve relative hrefs
        chapter_urls = [urljoin(story_base + "/", href) for href in chapter_urls if href]
        # If no links, treat the page content as a single chapter
        if not chapter_urls and result.get("content"):
            chapter_urls = [story_base]

        lm = dspy.LM("openai/gpt-4o-mini", max_tokens=16000, temperature=0.8)
        dspy.configure(lm=lm)
        tl = Translator()
        last_chapter_summary = ""

        for i in range(len(chapter_urls)):
            if i < start_chapter:
                continue
            if i > end_chapter:
                break
            print("Translating chapter", i + 1, "of", len(chapter_urls))
            chapter_url = chapter_urls[i]
            chap_result = selenium_utils.fetch_with_existing_driver_css(
                driver, chapter_url, CHAPTER_CONTENT_SELECTOR, wait_time=5, timeout=30, debug=False
            )
            if not chap_result or not chap_result.get("success") or not chap_result.get("content"):
                chapter_text = f"Chapter {i + 1} is not available."
            else:
                chapter_text = (chap_result["content"] or "").strip()

            # Save untranslated
            with open(
                f"texts/inprogress_translations/{name}/untranslated/v1c{i}({i + 1})_.txt",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(chapter_text)

            raw_title = chap_result.get("page_info", {}).get("title", f"Chapter {i + 1}")
            if helpers.needs_translation(url):
                answer = tl(chapter_text, last_chapter_summary, glossary=manual_name_translation)
                chapter_text = helpers.replace_with_dictionary(
                    answer.translation, manual_name_translation, confident=True
                )
                with dspy.context(lm=dspy.LM("openai/gpt-4o-mini")):
                    last_chapter_summary = dspy.Predict("chapter, last_chapter_summary -> summary")(
                        chapter=chapter_text, last_chapter_summary=last_chapter_summary
                    ).summary
                title = dspy.Predict("prompt, title -> translation")(
                    prompt="Please translate this title to English.",
                    title=raw_title,
                ).translation
            else:
                chapter_text = helpers.replace_with_dictionary(
                    chapter_text, manual_name_translation, confident=True
                )
                last_chapter_summary = ""
                title = raw_title
            safe_title = helpers.sanitize_filename(title)
            with open(
                f"texts/inprogress_translations/{name}/translated/v1c{i}({i + 1})_{safe_title}.txt",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(chapter_text)

        cost = sum(
            (x.get("cost") or 0) for x in lm.history if x.get("cost") is not None
        )
        print("Cost:", cost)
    except (NoSuchWindowException, SessionNotCreatedException):
        print("ERROR: Browser was closed or session was lost.")
        print("   Restart the script to continue from where you left off.")
    except WebDriverException:
        print("ERROR: Browser error occurred.")
        print("   The process was interrupted due to a browser-related issue.")
    except TimeoutException:
        print("ERROR: Timeout error occurred.")
        print("   Slow connection or website loading issues.")
    except KeyboardInterrupt:
        print("\nERROR: Scraping was interrupted by user (Ctrl+C).")
    except Exception as e:
        print("ERROR: An unexpected error occurred:")
        print(f"   {e}")
