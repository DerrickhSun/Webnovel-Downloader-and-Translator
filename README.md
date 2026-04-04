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

**Download novel** needs **Google Chrome** installed if you answer **yes** to **Login first?** (the browser opens so you can sign in; every supported site uses that same prompt).

---

## Using `main.py`

Run from the project root so imports resolve:

```bash
python main.py
```

You get a short menu:

| Choice | What it does |
|--------|----------------|
| **1) Download novel** | Scrape and translate (see below). |
| **2) Update library** | Same as `dict_utils.py`: **add** or **remove** titles/URLs in `data/`. |
| **3) Package novel** | Same as `text_utils.py` CLI: build volumes from `texts/finished_translations/<name>/`. |
| **4) Exit** | Quit. |

You can type the number (**1**–**4**) or a phrase like **`download novel`**, **`update library`**, **`package novel`**.

### Download novel (option 1)

1. Asks for a **novel name or URL** (names are resolved via `dict_utils` / `url_dict` when present).
2. Ensures output folders exist under `texts/inprogress_translations/<title>/`.
3. Asks whether to **pick up** from the last translated chapter.
4. Asks whether to **log in** in Chrome first (recommended when content is paywalled or needs a session).
5. Picks the scraper from the URL: **`novelpia`**, **`qidian`**, **`wattpad`**, or **`sfacg` / `fsacg`** (SFACG novels use `*.sfacg.com` URLs) must appear in the URL string (same idea as the other sites).

If nothing matches, you see **“Unsupported site”**.

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

The same operations are available from **`main.py`** → **Update library** (option 2).

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

### From **Download novel** (all supported sites)

Chapters are written under:

```
texts/inprogress_translations/<name>/
├── untranslated/   # raw chapter text (where the scraper writes it)
└── translated/     # translated `.txt` files
```

- **Novelpia**, **Wattpad**, **FSACG**, and **Qidian** all use this layout for **translated** output.
- **Novelpia**, **Wattpad**, and **FSACG** may also write **untranslated** files depending on chapter type; **Qidian** currently writes **translated** only (see `scrapers/qidianScraper.py`).

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
| **FSACG / SFACG** | `sfacg` or `fsacg` in URL | `scrapers/fsacgScraper.py` |

All four sites use the same **Download novel** flow in `main.py`: pickup, **Login first?** (optional Chrome sign-in), then scraping. Answer **no** to **Login first?** only if you do not need an authenticated session for that title.

---

## `requirements.txt` packages (summary)

`requests`, `beautifulsoup4`, `selenium`, `python-dotenv`, `openai`, `Pillow`, `dspy` — see `requirements.txt` for version pins.
