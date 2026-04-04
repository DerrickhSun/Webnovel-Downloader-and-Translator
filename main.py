import text_utils
import dict_utils
from dotenv import load_dotenv
import scrapers.novelpiaScraper as novelpiaScraper
import scrapers.qidianScraper as qidianScraper
import scrapers.wattpadScraper as wattpadScraper
import scrapers.fsacgScraper as fsacgScraper

load_dotenv()


def _is_fsacg_url(url: str) -> bool:
    """SFACG hosts use sfacg.com; some bookmarks may say 'fsacg'."""
    u = url.lower()
    return "sfacg" in u or "fsacg" in u


def download_novel():
    url = str(input("Novel name/url: "))

    # Load dictionaries using dict_utils
    url_dict = dict_utils.load_dict("url_dict")
    context_dict = dict_utils.load_dict("context_dict")
    name_dict = dict_utils.load_dict("name_dict")
    manual_name_translation_dict = dict_utils.load_dict("manual_name_translation_dict")

    if text_utils.normalize_text(url) in url_dict.keys():
        url = url_dict[text_utils.normalize_text(url)]

    if url in context_dict.keys():
        print("Found saved context for this novel")
        context = context_dict[url]
    else:
        print("No saved context found for this novel")

    name = "unrecognized"
    if url in name_dict.keys():
        name = name_dict[url]
    # TODO: handle unrecognized names
    print("Title:", name)

    manual_name_translation = {}
    if url in manual_name_translation_dict.keys():
        print("Found manual name translation for this novel")
        manual_name_translation = manual_name_translation_dict[url]

    text_utils.ensure_directory_exists(
        "texts/inprogress_translations/" + name + "/translated"
    )
    text_utils.ensure_directory_exists(
        "texts/inprogress_translations/" + name + "/untranslated"
    )

    pickup = bool(input("Pickup from where you left off? (y/n): ").lower().strip() == "y")
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
    print("Starting from chapter", start_chapter)

    use_login = bool(input("Login first? (y/n): ").lower().strip() == "y")

    if "novelpia" in url:
        novelpiaScraper.novelpia_scrape(
            url, name, start_chapter, end_chapter, manual_name_translation, use_login=use_login
        )
    elif "qidian" in url:
        qidianScraper.qidian_scrape(
            url, name, start_chapter, end_chapter, manual_name_translation, use_login=use_login
        )
    elif "wattpad" in url:
        wattpadScraper.wattpad_scrape(
            url, name, start_chapter, end_chapter, manual_name_translation, use_login=use_login
        )
    elif _is_fsacg_url(url):
        fsacgScraper.fsacg_scrape(
            url, name, start_chapter, end_chapter, manual_name_translation, use_login=use_login
        )
    else:
        print("Unsupported site")


def update_library():
    """Add or remove novel entries (same as running dict_utils.py)."""
    print("\nUpdate library — manage titles and URLs in data/*.json")
    operation = str(input("Operation (add / remove): ")).strip().lower()
    match operation:
        case "add":
            dict_utils.add_novel()
        case "remove":
            dict_utils.remove_title()
        case _:
            print("Unknown operation. Use add or remove.")


def package_novel():
    """Build volume files from finished translations (same as text_utils.py __main__)."""
    try:
        while True:
            name = input("Enter the name of the volume: ").strip()
            if name == "" or name.lower() == "exit":
                break
            text_utils.convert_to_volume(name, "texts/finished_translations/" + name)
    except Exception as e:
        print(f"Error: {str(e)}")


def _print_main_menu():
    print()
    print("Webnovel Downloader and Translator")
    print("----------------------------------")
    print("  1) Download novel")
    print("  2) Update library (add/remove titles in data/)")
    print("  3) Package novel (finished translations → volume)")
    print("  4) Exit")
    print()
    print('You can enter the number or a phrase (e.g. "download novel", "update library").')


def main():
    while True:
        _print_main_menu()
        choice = input("What would you like to do? ").strip().lower()

        if choice in ("4", "exit", "quit", "q"):
            print("Goodbye.")
            break

        if choice in ("1", "download", "download novel"):
            download_novel()
        elif choice in ("2", "update", "update library"):
            update_library()
        elif choice in ("3", "package", "package novel"):
            package_novel()
        else:
            print("Unrecognized choice. Enter 1–4 or a matching phrase.")


if __name__ == "__main__":
    main()
