import json
from collections.abc import Callable
from pathlib import Path

import text_utils

# context_dict: {url: {character/term: description}}
# name_dict: {url: main title}
# volume_dict: {title: starting volume}, not always used
# url_dict: {title: url}
# manual_name_translation_dict: {url: {character/term: translation}}

DATA_DIR = Path("data")

def _ensure_data_dir():
    """Create the data directory if it does not exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def save_dict(dict, filename):
    _ensure_data_dir()
    path = DATA_DIR / (filename + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict, f, indent=4)

def load_dict(filename):
    _ensure_data_dir()
    path = DATA_DIR / (filename + ".json")
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def add_novel(
    *,
    read_str: Callable[[str], str] | None = None,
    read_yes_no: Callable[[str], bool] | None = None,
    echo: Callable[[str], None] | None = None,
) -> None:
    context_dict = load_dict("context_dict")
    name_dict = load_dict("name_dict")
    volume_dict = load_dict("volume_dict")
    url_dict = load_dict("url_dict")
    manual_name_translation_dict = load_dict("manual_name_translation_dict")

    line_in = read_str or input

    def yes_no(prompt: str) -> bool:
        if read_yes_no is not None:
            return read_yes_no(prompt)
        return input(prompt).lower().strip() == "y"

    log = echo or print

    title = str(line_in("Novel name: "))
    title = text_utils.normalize_text(title)
    url = str(line_in("Novel url: "))
    if url in url_dict.keys():
        set_output = yes_no("Set this name as main name? (y/n): ")
        if set_output:
            name_dict[url] = title
    else:
        log("New novel")
        name_dict[url] = title

    if title in url_dict.keys():
        warn = yes_no("This title already exists. Overwrite? (y/n): ")
        if warn:
            url_dict[title] = url
    else:
        url_dict[title] = url

    save_dict(context_dict, "context_dict")
    save_dict(name_dict, "name_dict")
    save_dict(volume_dict, "volume_dict")
    save_dict(url_dict, "url_dict")
    save_dict(manual_name_translation_dict, "manual_name_translation_dict")


def remove_title(
    *,
    read_str: Callable[[str], str] | None = None,
    echo: Callable[[str], None] | None = None,
) -> None:
    context_dict = load_dict("context_dict")
    name_dict = load_dict("name_dict")
    volume_dict = load_dict("volume_dict")
    url_dict = load_dict("url_dict")
    manual_name_translation_dict = load_dict("manual_name_translation_dict")

    line_in = read_str or input
    log = echo or print

    title = str(line_in("Title: "))
    title = text_utils.normalize_text(title)

    if title in url_dict.keys():
        del url_dict[title]
    else:
        log("Title not found")
    
    save_dict(context_dict, 'context_dict')
    save_dict(name_dict, 'name_dict')
    save_dict(volume_dict, 'volume_dict')
    save_dict(url_dict, 'url_dict')
    save_dict(manual_name_translation_dict, 'manual_name_translation_dict')

if __name__ == "__main__":
    operation = str(input("Operation: "))
    match operation:
        case "add":
            add_novel()
        case "remove":
            remove_title()
    
    
    
    

