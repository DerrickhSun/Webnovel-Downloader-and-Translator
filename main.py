import utils.automated_login as automated_login
import scrapers.helpers as helpers
import text_utils
import re
from dspyBot import Translator, NameCorrector
import dict_utils
import dspy
from dotenv import load_dotenv
import os
import scrapers.novelpiaScraper as novelpiaScraper
import scrapers.qidianScraper as qidianScraper

# Import Selenium exceptions for better error handling
try:
    from selenium.common.exceptions import (
        WebDriverException, 
        NoSuchWindowException, 
        SessionNotCreatedException,
        TimeoutException,
        WebDriverException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

load_dotenv()

def download_novel():
    url = str(input("Novel name/url: "))

    # Load dictionaries using dict_utils
    url_dict = dict_utils.load_dict('url_dict')
    context_dict = dict_utils.load_dict('context_dict')
    name_dict = dict_utils.load_dict('name_dict')
    manual_name_translation_dict = dict_utils.load_dict('manual_name_translation_dict')

    if (text_utils.normalize_text(url) in url_dict.keys()):
        url = url_dict[text_utils.normalize_text(url)]

    if (url in context_dict.keys()):
        print("Found saved context for this novel")
        context = context_dict[url]
    else:
        print("No saved context found for this novel")


    name = "unrecognized"
    if url in name_dict.keys():
        name = name_dict[url]
    #TODO: handle unrecognized names
    print("Title:", name)

    manual_name_translation = {}
    if url in manual_name_translation_dict.keys():
        print("Found manual name translation for this novel")
        manual_name_translation = manual_name_translation_dict[url]
    

    text_utils.ensure_directory_exists("texts/inprogress_translations/" + name + "/translated")
    text_utils.ensure_directory_exists("texts/inprogress_translations/" + name + "/untranslated")
    
    pickup = bool(input("Pickup from where you left off? (y/n): ").lower().strip() == 'y')
    if pickup:
        start_chapter = text_utils.get_last_chapter_number(name + "/translated", debug=False) + 1
        end_chapter = 9999
    else:
        start_chapter = 0
        end_chapter = 9999
    print("Starting from chapter", start_chapter)

    if "novelpia" in url:
        novelpiaScraper.novelpia_scrape(url, name, start_chapter, end_chapter, manual_name_translation)
    elif "qidian" in url:
        qidianScraper.qidian_scrape(url, name, start_chapter, end_chapter, manual_name_translation)
    else:
        print("Unsupported site")
    

def manage_dict():
    return False #TODO: implement text_utils

if __name__ == "__main__":
    download_novel()
    