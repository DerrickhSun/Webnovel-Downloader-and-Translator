"""Syosetu (Shousetsuka ni Narou, ncode.syosetu.com) scraper.

Chapter list lives at https://ncode.syosetu.com/{ncode}/ (paginated via ?p=N for
long novels), one row per chapter as div.p-eplist__sublist > a.p-eplist__subtitle.
Chapter pages hold the title in h1.p-novel__title and the body in
div.p-novel__body, made of one or more div.js-novel-text blocks (preface / main
text / afterword) containing <p id="L..."> paragraphs. No login is required for
all-ages content on this domain, so this scraper talks to the site over plain
HTTP rather than driving a browser.
"""
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import dspy

import scrapers.helpers as helpers
from translators import Translator

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.8,en;q=0.6",
}

REQUEST_DELAY_SECONDS = 1


def _ncode_from_url(url: str) -> str:
    """Extract the novel code (e.g. 'n6931lm') from any syosetu URL."""
    match = re.search(r"/(n[0-9a-z]+)/?", urlparse(url.strip()).path, re.IGNORECASE)
    if not match:
        raise ValueError(f"Could not find a syosetu novel code (ncode) in URL: {url}")
    return match.group(1).lower()


def _toc_url(ncode: str, page: int = 1) -> str:
    base = f"https://ncode.syosetu.com/{ncode}/"
    return base if page <= 1 else f"{base}?p={page}"


def _get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")


def _ruby_to_inline_text(container) -> None:
    """Rewrite <ruby>base<rt>reading</rt></ruby> to 'base(reading)' plain text in place."""
    for ruby in container.find_all("ruby"):
        rt = ruby.find("rt")
        reading = rt.get_text(strip=True) if rt else ""
        for rp in ruby.find_all("rp"):
            rp.decompose()
        if rt:
            rt.decompose()
        base = ruby.get_text()
        ruby.replace_with(f"{base}({reading})" if reading else base)


def _extract_chapter_title(soup: BeautifulSoup, fallback: str) -> str:
    h1 = soup.find("h1", class_=lambda c: c and "p-novel__title" in c)
    return h1.get_text(strip=True) if h1 else fallback


def _extract_chapter_text(soup: BeautifulSoup) -> str:
    body = soup.find("div", class_="p-novel__body")
    if not body:
        return ""
    blocks = []
    for block in body.find_all("div", class_="js-novel-text"):
        _ruby_to_inline_text(block)
        for br in block.find_all("br"):
            br.replace_with("\n")
        paragraphs = [p.get_text().strip() for p in block.find_all("p")]
        blocks.append("\n".join(paragraphs))
    return "\n\n".join(block for block in blocks if block)


def _fetch_chapter_links(ncode: str) -> list[tuple[str, str]]:
    """Returns [(title, chapter_url), ...] across all TOC pages.

    Falls back to treating the index page itself as the single chapter for
    tanpen (one-shot) novels, which have no episode list.
    """
    links: list[tuple[str, str]] = []
    page = 1
    while True:
        soup = _get_soup(_toc_url(ncode, page))
        rows = soup.find_all("div", class_="p-eplist__sublist")

        if not rows:
            if page == 1 and soup.find("div", class_="p-novel__body"):
                title = _extract_chapter_title(soup, ncode)
                return [(title, _toc_url(ncode))]
            break

        for row in rows:
            a = row.find("a", class_="p-eplist__subtitle")
            if not a or not a.get("href"):
                continue
            href = a["href"]
            if not href.startswith("http"):
                href = "https://ncode.syosetu.com" + href
            links.append((a.get_text(strip=True), href))

        if len(rows) < 100:
            break
        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return links


def syosetu_scrape(
    url,
    name,
    start_chapter,
    end_chapter,
    manual_name_translation=None,
    use_login=True,
    browser_driver=None,
):
    """Fetch and translate a Syosetu novel.

    use_login / browser_driver are accepted for signature parity with the other
    scrapers but are unused: all-ages content on ncode.syosetu.com needs no
    authentication, so chapters are fetched with plain HTTP requests.
    """
    if manual_name_translation is None:
        manual_name_translation = {}
    try:
        ncode = _ncode_from_url(url)
        chapters = _fetch_chapter_links(ncode)
        if not chapters:
            print("No chapters found for this novel.")
            return

        lm = dspy.LM("openai/gpt-4o-mini", max_tokens=16000, temperature=0.8)
        dspy.configure(lm=lm)
        tl = Translator()
        last_chapter_summary = ""

        for i, (raw_title, chapter_url) in enumerate(chapters):
            if i < start_chapter:
                continue
            if i > end_chapter:
                break
            print("Translating chapter", i, "of", len(chapters))

            soup = _get_soup(chapter_url)
            chapter_text = _extract_chapter_text(soup)
            title = _extract_chapter_title(soup, raw_title)
            if not chapter_text:
                chapter_text = f"Chapter {i} is not available."

            with open(
                f"texts/inprogress_translations/{name}/untranslated/v1c{i}({i})_.txt",
                "w",
                encoding="utf-8",
            ) as text_file:
                text_file.write(chapter_text)

            if helpers.needs_translation(url):
                answer = tl(chapter_text, last_chapter_summary, glossary=manual_name_translation)
                chapter_text = helpers.replace_with_dictionary(
                    answer.translation, manual_name_translation, confident=True
                )
                with dspy.context(lm=dspy.LM("openai/gpt-4o-mini")):
                    last_chapter_summary = dspy.Predict(
                        "chapter, last_chapter_summary -> summary"
                    )(chapter=chapter_text, last_chapter_summary=last_chapter_summary).summary
                translated_title = dspy.Predict("prompt, title -> translation")(
                    prompt="Please translate this title to English.", title=title
                ).translation
            else:
                chapter_text = helpers.replace_with_dictionary(
                    chapter_text, manual_name_translation, confident=True
                )
                last_chapter_summary = ""
                translated_title = title

            safe_title = helpers.sanitize_filename(translated_title)
            with open(
                f"texts/inprogress_translations/{name}/translated/v1c{i}({i})_{safe_title}.txt",
                "w",
                encoding="utf-8",
            ) as text_file:
                text_file.write(chapter_text)

            time.sleep(REQUEST_DELAY_SECONDS)

        cost = sum(x["cost"] for x in lm.history if x["cost"] is not None)
        print("Cost:", cost)
    except KeyboardInterrupt:
        print("\nERROR: Scraping was interrupted by user (Ctrl+C).")
    except requests.RequestException as e:
        print("ERROR: A network error occurred while fetching from Syosetu.")
        print(f"   {e}")
    except Exception as e:
        print("ERROR: An unexpected error occurred:")
        print(f"   {e}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    import dict_utils
    import text_utils

    load_dotenv()

    url_in = str(input("Novel name/url: "))
    url_dict = dict_utils.load_dict("url_dict")
    name_dict = dict_utils.load_dict("name_dict")
    manual_name_translation_dict = dict_utils.load_dict("manual_name_translation_dict")

    if text_utils.normalize_text(url_in) in url_dict:
        url_in = url_dict[text_utils.normalize_text(url_in)]

    name_in = name_dict.get(url_in, "unrecognized")
    manual_name_translation_in = manual_name_translation_dict.get(url_in, {})

    text_utils.ensure_directory_exists(f"texts/inprogress_translations/{name_in}/translated")
    text_utils.ensure_directory_exists(f"texts/inprogress_translations/{name_in}/untranslated")

    sc = int(input("Start chapter index (0 = from first): ") or "0")
    ec = int(input("End chapter index (9999 for all): ") or "9999")

    syosetu_scrape(url_in, name_in, sc, ec, manual_name_translation_in)
