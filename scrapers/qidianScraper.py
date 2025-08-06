import utils.automated_login as automated_login
import scrapers.helpers as helpers
import utils.selenium_utils as selenium_utils
import re
from dspyBot import Translator, NameCorrector
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


def qidian_scrape(url, name, start_chapter, end_chapter, manual_name_translation={}):
    try:
        links = []
        titles = []
        last_chapter_summary = ""


        login_result = automated_login.manual_login(url="https://www.qidian.com/", debug=False) 
        #output = selenium_utils.fetch_with_existing_driver_div(login_result['driver'], url, div_class="page-link", debug=False)

        lis = selenium_utils.fetch_with_existing_driver_list(login_result['driver'], url, list_class="volume-chapters", parent_div_class="catalog-volume", debug=False)
        print(lis.keys())
        zero_volume = False

        vol = 0 if zero_volume else 1
        chap = 1
        count = 1
        lis2 = lis["urls"]
        print(lis2)

        #print(links)
        lm = dspy.LM('openai/gpt-4o-mini', max_tokens=16000, temperature=0.8)
        dspy.configure(lm=lm)
        tl = Translator()

        while (vol <= len(lis2)):
            chap = 1
            while (chap <= len(lis2[vol if zero_volume else vol - 1])):
                if (count < start_chapter):
                    chap += 1
                    count += 1
                    continue
                target_url = lis2[vol if zero_volume else vol - 1][chap - 1]
                print("translating volume", vol, "chapter", chap,"(", count, ")")
                index = target_url.find("www.qidian.com")
                chapter_text = selenium_utils.fetch_with_existing_driver_custom(
                    login_result['driver'], 'https://' + target_url[index:], element_type="main", element_class="content", debug=False)['content']
                
                title = selenium_utils.fetch_with_existing_driver_custom(
                    login_result['driver'], 'https://' + target_url[index:], element_type="h1", element_class="title", debug=False)['content']
                title = dspy.Predict('prompt, title -> translation')(prompt="Please translate this title.", title = title).translation
            
                if not chapter_text:
                    flag = False
                    print("VIP chapter, using selenium")
                    for i in range(1):
                        print("Attempting to fetch chapter text, attempt", i + 1)
                        try:
                            chapter_text = selenium_utils.fetch_with_existing_driver_custom(
                                login_result['driver'], 'https://' + target_url[index:], element_type="main", element_class="content", debug=False)['content']
                            flag = True
                            break
                        except:
                            print("Failed to fetch chapter text, retrying...")
                    if (flag == False):
                        print("Failed to fetch chapter text, quitting...")
                        quit()
                else:
                    print("Public chapter")
                answer = tl(chapter_text, last_chapter_summary)

                with dspy.context(lm=dspy.LM('openai/gpt-4o-mini')):
                    last_chapter_summary = dspy.Predict('chapter -> summary')(chapter = answer.translation).summary

                #chapter_text = replace_with_dictionary(answer.translation, manual_name_translation, confident=True)

                with open("texts/inprogress_translations/" + name+"/translated/v"+str(vol)+"c"+str(chap)+"("+str(count)+")_"+helpers.sanitize_filename(title)+".txt", "w", encoding="utf-8") as text_file:
                        text_file.write(chapter_text)
                chap += 1
                count += 1

        cost = sum([x['cost'] for x in lm.history if x['cost'] is not None])  # in USD, as calculated by LiteLLM for certain providers
        print("Cost:", cost)
    except (NoSuchWindowException, SessionNotCreatedException) as e:
        print("❌ Browser was closed or session was lost.")
        print("   The scraping process was interrupted because the browser window was closed.")
        print("   You can restart the script to continue from where you left off.")
        print(f"   Technical details: {str(e)}")
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
    '''except Exception as e:
        print("❌ An unexpected error occurred:")
        print(f"   {str(e)}")
        print("   Scraping failed or was interrupted.")'''