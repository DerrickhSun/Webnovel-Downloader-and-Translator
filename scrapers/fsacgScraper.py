"""FSACG/SFACG scraper - handles book.sfacg.com (etc.) novel scraping, including VIP image chapters."""
import os
from urllib.parse import urlparse

import dspy
import web_scraper
import dict_utils
import text_utils
import utils.automated_login as automated_login
from translators import Translator, NameCorrector


def _login_url_from_novel_url(novel_url: str) -> str:
    """Open the same host as the catalog URL so session cookies match requests."""
    p = urlparse(novel_url.strip())
    if p.scheme and p.netloc:
        return f"{p.scheme}://{p.netloc}/"
    return "https://book.sfacg.com/"


def _apply_driver_cookies_to_web_scraper_session(driver) -> None:
    """Copy Selenium cookies into web_scraper.session_manager for HTTP fetches."""
    web_scraper.session_manager.clear_cookies()
    session = web_scraper.session_manager.get_session()
    for c in driver.get_cookies():
        name = c.get("name")
        value = c.get("value")
        if not name or value is None:
            continue
        domain = c.get("domain")
        path = c.get("path") or "/"
        try:
            if domain:
                session.cookies.set(name, value, domain=domain, path=path)
            else:
                session.cookies.set(name, value, path=path)
        except Exception:
            session.cookies.set(name, value)
    web_scraper.session_manager.save_cookies()


def fsacg_scrape(
    url,
    name,
    start_chapter,
    end_chapter,
    manual_name_translation=None,
    use_login=True,
    browser_driver=None,
):
    """
    Fetch and translate an FSACG novel: manual browser login (optional), then HTTP
    requests using cookies copied from Chrome.

    start_chapter / end_chapter are linear indices matching filenames: v* c* (n)_
    where n is the running chapter counter (1-based). Use start_chapter=0 to begin at 1.

    If use_login is True, opens Chrome on the novel site's origin so you can sign in
    (or navigates browser_driver there if passed from the app UI). Cookies are then
    synced into web_scraper.session_manager. If False and no browser_driver, opens
    Chrome without the wait loop — you are unlikely to be logged in.
    """
    if manual_name_translation is None:
        manual_name_translation = {}

    login_url = _login_url_from_novel_url(url)
    driver = None
    reuse_app_browser = browser_driver is not None
    try:
        if use_login:
            login_result = automated_login.manual_login(
                url=login_url,
                wait_time=120,
                debug=False,
                existing_driver=browser_driver,
            )
        else:
            login_result = automated_login.get_driver_no_login(
                debug=False, existing_driver=browser_driver
            )
        driver = login_result.get("driver")
        if not driver:
            print("Could not start browser for FSACG login.")
            return
        _apply_driver_cookies_to_web_scraper_session(driver)
    finally:
        if driver and not reuse_app_browser:
            try:
                driver.quit()
            except Exception:
                pass

    context_dict = dict_utils.load_dict("context_dict")
    if url in context_dict:
        context = context_dict[url]
    else:
        context = []

    last_chapter_summary = ""
    trust_ocr = True
    l2_index = 0
    volume_dict = dict_utils.load_dict("volume_dict")
    if url in volume_dict:
        l2_index = volume_dict[url]

    base = os.path.join("texts", "inprogress_translations", name)
    text_utils.ensure_directory_exists(base)
    text_utils.ensure_directory_exists(os.path.join(base, "translated"))
    text_utils.ensure_directory_exists(os.path.join(base, "untranslated"))
    text_utils.ensure_directory_exists("temp")

    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm, max_tokens=10000)

    rag = Translator(context)
    name_corrector = NameCorrector(context)

    brightness_factor = 1.1
    contrast_factor = 2

    def scrape_fsacg_vip_chapter(img_url, vol, chap, count):
        nonlocal last_chapter_summary
        try:
            vip_path = os.path.join("temp", f"vipImage{count}.png")
            web_scraper.download_image(img_url, vip_path, debug=False)
            ocr_text = web_scraper.analyze_image(
                vip_path,
                brightness=brightness_factor,
                contrast=contrast_factor,
                split=True,
                prompt="Please extract the exact Chinese text from this image using OCR (optical character recognition). Extract the text and include nothing else.",
                debug=False,
            )
            untranslated_path = os.path.join(
                base, "untranslated", f"v{vol}c{chap}({count})_untranslated.txt"
            )
            with open(untranslated_path, "w", encoding="utf-8") as text_file:
                text_file.write(ocr_text)

            print("Translating")
            with dspy.context(lm=dspy.LM("openai/gpt-4o-mini")):
                answer = rag(ocr_text, last_chapter_summary, glossary=manual_name_translation)
            chapter = answer.translation
            text_utils.clear_directory_contents("temp")

            if not trust_ocr:
                raw_path = os.path.join(
                    base, "translated", f"v{vol}c{chap}({count})_raw.txt"
                )
                with open(raw_path, "w", encoding="utf-8") as text_file:
                    text_file.write(chapter)

                print("Correcting names")
                with dspy.context(
                    lm=dspy.LM("openai/o3-mini", temperature=1.0, max_tokens=20000)
                ):
                    answer2 = name_corrector(answer.translation, last_chapter_summary)
                chapter = answer2.corrected_chapter

            with dspy.context(lm=dspy.LM("openai/gpt-4o-mini")):
                last_chapter_summary = dspy.Predict("chapter -> summary")(
                    chapter=chapter
                ).summary

            out_path = os.path.join(
                base,
                "translated",
                f"v{vol}c{chap}({count})_{web_scraper.sanitize_filename(answer.title)}.txt",
            )
            with open(out_path, "w", encoding="utf-8") as text_file:
                text_file.write(chapter)
            return 1
        except Exception as e:
            print("Exception:", e)
            return 0

    lis = web_scraper.fetch_lists_from_url(
        url, list_class="clearfix", parent_div_class="catalog-list", debug=False
    )
    lis2 = lis[l2_index:]

    vol = 1
    chap = 1
    count = 1

    while vol <= len(lis2):
        chap = 1
        while chap <= len(lis2[vol - 1]):
            if count < start_chapter:
                chap += 1
                count += 1
                continue
            if end_chapter < 9999 and count > end_chapter:
                vol = 999999
                break

            item = lis2[vol - 1][chap - 1]
            target_url = item["href"]
            print("translating volume", vol, "chapter", chap, "(", count, ")")
            img_url = web_scraper.fetch_image_url(
                target_url, img_id="vipImage", debug=False
            )

            if img_url is None:
                print("Public chapter")
                script = web_scraper.fetch_div_content(
                    target_url, "ChapterBody", debug=False
                )
                print(script)
                answer = rag(
                    script, last_chapter_summary, glossary=manual_name_translation
                )
                with dspy.context(lm=dspy.LM("openai/gpt-4o-mini")):
                    last_chapter_summary = dspy.Predict("chapter -> summary")(
                        chapter=answer.translation
                    ).summary
                out_path = os.path.join(
                    base,
                    "translated",
                    f"v{vol}c{chap}({count})_{web_scraper.sanitize_filename(answer.title)}.txt",
                )
                with open(out_path, "w", encoding="utf-8") as text_file:
                    text_file.write(answer.translation)
            else:
                print("VIP chapter")
                success = False
                for i in range(4):
                    if scrape_fsacg_vip_chapter(img_url, vol, chap, count) == 1:
                        success = True
                        break
                    print("Failure", i + 1)
                if not success:
                    print("Failed to scrape chapter", vol, chap, "(" + str(count) + ")")
                    return

            chap += 1
            count += 1
            cost = sum(
                x["cost"] for x in lm.history if x["cost"] is not None
            )
            print(cost)
        vol += 1

    cost = sum(x["cost"] for x in lm.history if x["cost"] is not None)
    print(cost)


if __name__ == "__main__":
    from dotenv import load_dotenv
    from text_utils import normalize_text

    load_dotenv()

    url_in = str(input("Novel name/url: "))
    url_dict = dict_utils.load_dict("url_dict")
    context_dict = dict_utils.load_dict("context_dict")
    name_dict = dict_utils.load_dict("name_dict")
    manual_name_translation_dict = dict_utils.load_dict(
        "manual_name_translation_dict"
    )

    if normalize_text(url_in) in url_dict:
        url = url_dict[normalize_text(url_in)]
    else:
        url = url_in

    name = "unrecognized"
    if url in name_dict:
        name = name_dict[url]

    manual_name_translation = manual_name_translation_dict.get(url, {})

    sc = int(input("Start chapter index (0 = from first, matches v*c*(n)_ n): ") or "0")
    ec = int(input("End chapter index (9999 for all): ") or "9999")
    use_login = (
        input("Login in browser first? (y/n): ").lower().strip() == "y"
    )

    fsacg_scrape(url, name, sc, ec, manual_name_translation, use_login=use_login)
