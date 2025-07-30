from website_viewer import analyze_website
import automated_login
import web_scraper
import selenium_utils
import text_utils
import re
from dspyBot import Translator, NameCorrector
import dict_utils
import dspy
from dotenv import load_dotenv
import os

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

def is_single_english_word(text):
    """
    Check if a string is a single word containing only English characters and numbers.
    
    Args:
        text (str): The string to check
        
    Returns:
        bool: True if the string is a single English word/number, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
    
    # Strip whitespace
    text = text.strip()
    
    # Check if it's empty after stripping
    if not text:
        return False
    
    # Check if it contains only English letters, numbers, and common word characters
    # This regex matches: letters (a-z, A-Z), numbers (0-9), hyphens (-), apostrophes (')
    english_word_pattern = r'^[a-zA-Z0-9\-\']+$'
    
    return bool(re.match(english_word_pattern, text))


def is_token_string(text, min_length=20):
    """
    Check if a string looks like a token (long string of random characters).
    
    Args:
        text (str): The string to check
        min_length (int): Minimum length to consider as a token
        
    Returns:
        bool: True if the string looks like a token, False otherwise
    """
    if not text or not isinstance(text, str):
        return False
    
    text = text.strip()
    
    # Check if it's long enough to be a token
    if len(text) < min_length:
        return False
    
    # Check if it contains only alphanumeric characters (no spaces, punctuation, etc.)
    alphanumeric_pattern = r'^[a-zA-Z0-9]+$'
    
    return bool(re.match(alphanumeric_pattern, text))


def filter_tokens_from_text(text, debug=False):
    """
    Filter out token-like strings from text content.
    
    Args:
        text (str): The text to filter
        debug (bool): If True, prints debug information
        
    Returns:
        str: Text with tokens filtered out
    """
    if not text:
        return ""
    
    if debug:
        print(f"Original text length: {len(text)}")
        print("Original text preview:")
        print(text[:200] + "..." if len(text) > 200 else text)
    
    # Split text into words
    words = text.split()
    filtered_words = []
    removed_tokens = []
    
    for word in words:
        # Check if this word looks like a token
        if is_token_string(word):
            removed_tokens.append(word)
            if debug:
                print(f"Removed token: {word}")
        else:
            filtered_words.append(word)
    
    # Reconstruct text
    filtered_text = ' '.join(filtered_words)
    
    if debug:
        print(f"\nRemoved {len(removed_tokens)} tokens:")
        for token in removed_tokens[:5]:  # Show first 5 tokens
            print(f"  - {token}")
        if len(removed_tokens) > 5:
            print(f"  ... and {len(removed_tokens) - 5} more")
        
        print(f"\nFiltered text length: {len(filtered_text)}")
        print("Filtered text preview:")
        print(filtered_text[:200] + "..." if len(filtered_text) > 200 else filtered_text)
    
    return filtered_text


def clean_novel_text(text, remove_chars=None, debug=False):
    """
    Clean up novel text by removing unwanted characters and formatting.
    
    Args:
        text (str): The raw text to clean
        remove_chars (list): List of characters to remove from the start of lines
        debug (bool): If True, prints debug information
    
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    if debug:
        print(f"Original text length: {len(text)}")
        print("Original text preview:")
        print(text[:500] + "..." if len(text) > 500 else text)
    
    # Default characters to remove from start of lines
    if remove_chars is None:
        remove_chars = [
            '<font class="line" data-line="', 
            '" id="line_',
            '">',
            '</font>',
            ', ',
            '   '  # Multiple spaces
        ]
    
    # Split into lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        cleaned_line = line
        
        # Remove specified characters from the start of the line
        for char in remove_chars:
            if cleaned_line.startswith(char):
                cleaned_line = cleaned_line[len(char):]
        
        # Remove specified characters from anywhere in the line
        for char in ['<font class="line" data-line="', '" id="line_', '">', '</font>', ', ']:
            cleaned_line = cleaned_line.replace(char, '')
        
        # Clean up extra whitespace
        cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()
        
        # Only add non-empty lines
        if cleaned_line:
            cleaned_lines.append(cleaned_line)
        
        if debug and original_line != cleaned_line:
            print(f"Line {i+1}:")
            print(f"  Original: {repr(original_line)}")
            print(f"  Cleaned:  {repr(cleaned_line)}")
    
    # Join lines back together
    cleaned_text = '\n'.join(cleaned_lines)
    
    if debug:
        print(f"\nCleaned text length: {len(cleaned_text)}")
        print("Cleaned text preview:")
        print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
    
    return cleaned_text


def clean_novel_text_advanced(text, debug=False):
    """
    Advanced text cleaning function that handles various formatting issues.
    
    Args:
        text (str): The raw text to clean
        debug (bool): If True, prints debug information
    
    Returns:
        str: Cleaned text
    """
    if not text:
        return ""
    
    if debug:
        print(f"Advanced cleaning - Original text length: {len(text)}")
    
    # Remove HTML-like formatting
    text = re.sub(r'<font[^>]*>', '', text)
    text = re.sub(r'</font>', '', text)
    text = re.sub(r'<[^>]*>', '', text)  # Remove any remaining HTML tags
    
    # Remove line numbers and formatting
    text = re.sub(r'data-line="\d+"', '', text)
    text = re.sub(r'id="line_\d+"', '', text)
    text = re.sub(r'class="[^"]*"', '', text)
    
    # Clean up quotes and commas
    text = text.replace('", ', '')
    text = text.replace(', "', '')
    text = text.replace('",', '')
    text = text.replace(',"', '')
    
    # Remove extra whitespace and normalize
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Strip whitespace and clean up
        cleaned_line = re.sub(r'\s+', ' ', line).strip()
        
        # Remove empty lines or lines with only punctuation
        if cleaned_line and not re.match(r'^[,\s]*$', cleaned_line):
            cleaned_lines.append(cleaned_line)
    
    cleaned_text = '\n'.join(cleaned_lines)
    
    if debug:
        print(f"Advanced cleaning - Cleaned text length: {len(cleaned_text)}")
        print("Advanced cleaned text preview:")
        print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
    
    return cleaned_text


def novelpia_scrape(url, name, start_chapter, end_chapter, manual_name_translation={}):
    try:
        links = []
        titles = []
        last_chapter_summary = ""
        url_header = "https://novelpia.com/viewer/"


        login_result = automated_login.manual_login(debug=False) 
        output = selenium_utils.fetch_with_existing_driver_div(login_result['driver'], url, div_class="page-link", debug=False)


        page = 2
        while True:
            table = selenium_utils.interact_with_episode_table(login_result['driver'], debug=False)['episodes']
            for o in table:
                links.append(url_header + str(o['episode_no']))
                titles.append(o['title'])
            pagination = selenium_utils.interact_with_pagination(login_result['driver'], page_number=page, wait_time=1, debug=False)
            if not pagination['click_success']:
                break
            page += 1

        #print(links)
        lm = dspy.LM('openai/gpt-4o-mini', max_tokens=16000, temperature=0.8)
        dspy.configure(lm=lm)
        tl = Translator()


        for i in range(len(links)):
            if (i < start_chapter):
                continue
            print("Translating chapter", i, "of", len(links))

            chapter = selenium_utils.fetch_with_existing_driver_custom(login_result['driver'], links[i], element_type="font", element_class="line", debug=False)['content']
            if chapter == None:
                print("Chapter", i, "is not available")
                chapter = ["Chapter " + str(i) + " is not available"]

            chapter_text = ""
            for line in chapter:
                # Filter out tokens from each line
                filtered_line = filter_tokens_from_text(line, debug=False)
                if filtered_line.strip():  # Only add non-empty lines
                    chapter_text += filtered_line + "\n\n"
            
            #save untranslated chapter
            with open(name+"/untranslated/v"+str(1)+"c"+str(i)+"("+str(i)+")_"+".txt", "w", encoding="utf-8") as text_file:
                    text_file.write(chapter_text)

            #translate chapter
            answer = tl(chapter_text, last_chapter_summary, glossary = manual_name_translation)
            chapter_text = text_utils.replace_with_dictionary(answer.translation, manual_name_translation, confident=True)
            #get summary to use for next chapter
            with dspy.context(lm=dspy.LM('openai/gpt-4o-mini')):
                last_chapter_summary = dspy.Predict('chapter, last_chapter_summary -> summary')(chapter = chapter_text, last_chapter_summary = last_chapter_summary).summary
            
            #save translated chapter
            title = dspy.Predict('prompt, title -> translation')(prompt="Please translate this title to English.", title=titles[i]).translation
            with open(name+"/translated/v"+str(1)+"c"+str(i)+"("+str(i)+")_"+web_scraper.sanitize_filename(title)+".txt", "w", encoding="utf-8") as text_file:
                    text_file.write(chapter_text)

        cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
        print("Cost:", cost)
    except (NoSuchWindowException, SessionNotCreatedException) as e:
        print("❌ Browser was closed or session was lost.")
        print("   The scraping process was interrupted because the browser window was closed.")
        print("   You can restart the script to continue from where you left off.")
        #print(f"   Technical details: {str(e)}")
    except WebDriverException as e:
        print("❌ Browser error occurred.")
        print("   The scraping process was interrupted due to a browser-related issue.")
        print("   This might be due to the browser being closed or a connection problem.")
        #print(f"   Technical details: {str(e)}")
    except TimeoutException as e:
        print("❌ Timeout error occurred.")
        print("   The scraping process was interrupted due to a timeout.")
        print("   This might be due to slow internet connection or website loading issues.")
        #print(f"   Technical details: {str(e)}")
    except KeyboardInterrupt:
        print("\n❌ Scraping was interrupted by user (Ctrl+C).")
        print("   The process was manually stopped.")
    except Exception as e:
        print("❌ An unexpected error occurred:")
        print(f"   {str(e)}")
        print("   Scraping failed or was interrupted.")


if __name__ == "__main__":
    url = str(input("Novel name/url: "))#"theres no way a temp magical girl like me could be cute right"

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
    print("Title:", name)

    manual_name_translation = {}
    if url in manual_name_translation_dict.keys():
        print("Found manual name translation for this novel")
        manual_name_translation = manual_name_translation_dict[url]
    

    text_utils.ensure_directory_exists(name + "/translated")
    text_utils.ensure_directory_exists(name + "/untranslated")
    
    pickup = bool(input("Pickup from where you left off? (y/n): ").lower().strip() == 'y')
    if pickup:
        start_chapter = text_utils.get_last_chapter_number(name + "/translated", debug=False) + 1
        end_chapter = 9999
    else:
        start_chapter = 0
        end_chapter = 9999
    print("Starting from chapter", start_chapter)

    novelpia_scrape(url, name,start_chapter, end_chapter, manual_name_translation)
    