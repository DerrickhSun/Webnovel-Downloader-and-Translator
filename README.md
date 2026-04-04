# Webnovel Downloader and Translator

## Install dependencies

From the project root (where `requirements.txt` lives):

```bash
python -m pip install -r requirements.txt
```

Use a virtual environment if you prefer:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Translation features use **DSPy / OpenAI**; configure credentials via **`.env`** (loaded by `main.py` with `python-dotenv`) as required by your setup.

Selenium-based scrapers need **Google Chrome** installed; the login flow may open a real browser window.

---

## Using `main.py`

Run from the project root so imports resolve:

```bash
python main.py
```

This starts **`download_novel()`**, which interactively:

1. Asks for a **novel name or URL** (names are resolved via `dict_utils` / `url_dict` when present).
2. Ensures output folders exist under `texts/inprogress_translations/<title>/`.
3. Asks whether to **pick up** from the last translated chapter.
4. Asks whether to **log in** in the browser first (needed for paywalled or session-gated content on some sites).
5. Dispatches to the scraper whose URL matches **`novelpia`**, **`qidian`**, **`wattpad`**, or **`fsacg`** in the URL string.

If the URL does not match any of those, you will see **“Unsupported site”**.

**FSACG** also uses the **“Login first?”** prompt: if you choose yes, Chrome opens on the same host as your novel URL; after you sign in, session cookies are copied into the HTTP client and the browser closes before downloading chapters.

---

## Using `dict_utils.py`

`dict_utils` stores JSON dictionaries under **`data/`** (files like `data/url_dict.json`).

Run the small CLI:

```bash
python dict_utils.py
```

Enter an operation:

- **`add`** — prompts for novel title and URL, updates `url_dict` and `name_dict` (and re-saves the other dict files).
- **`remove`** — prompts for a normalized title and removes it from `url_dict` if found.

In code you can use:

- **`dict_utils.load_dict('filename_without_extension')`** — returns a `dict` (empty if the file is missing).
- **`dict_utils.save_dict(python_dict, 'filename_without_extension')`** — writes `data/<filename>.json`.

Relevant keys (see comments in `dict_utils.py`):

| File (in `data/`) | Role |
|-------------------|------|
| `url_dict.json` | Normalized title → URL |
| `name_dict.json` | URL → display / folder title |
| `context_dict.json` | URL → character/term context |
| `volume_dict.json` | URL → starting volume (optional) |
| `manual_name_translation_dict.json` | URL → manual name translations |

---

## Where outputs go

### From `main.py` (Novelpia, Qidian, Wattpad, FSACG)

Chapters are written under:

```
texts/inprogress_translations/<name>/
├── untranslated/   # raw chapter text (where the scraper writes it)
└── translated/     # translated `.txt` files
```

- **Novelpia**, **Wattpad**, and **FSACG** (VIP OCR path) write **untranslated** and/or **translated** files there.
- **Qidian** currently writes **translated** chapters only under that tree (see `scrapers/qidianScraper.py`).

`<name>` comes from `name_dict` for the novel URL when set; otherwise it may show as **`unrecognized`** until you add the novel in `dict_utils`.

### `dict_utils` outputs

All updates go to **`data/*.json`** (created on first use).

---

## Sites supported by `main.py`

| Site | URL hint (in the novel URL) | Scraper module |
|------|-----------------------------|----------------|
| **Novelpia** | `novelpia` | `scrapers/novelpiaScraper.py` |
| **Qidian** | `qidian` | `scrapers/qidianScraper.py` |
| **Wattpad** | `wattpad` | `scrapers/wattpadScraper.py` |
| **FSACG** | `fsacg` | `scrapers/fsacgScraper.py` |

**FSACG** uses the same **manual Chrome login** as the other sites when you answer **yes** to “Login first?”; cookies from the browser are applied to `web_scraper`’s `requests` session (and saved via `cookies.json` like other flows that use the session manager). Answer **no** only if you do not need an authenticated session.

---

## `requirements.txt` packages (summary)

`requests`, `beautifulsoup4`, `selenium`, `python-dotenv`, `openai`, `Pillow`, `dspy` — see `requirements.txt` for version pins.
