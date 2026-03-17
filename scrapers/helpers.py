import re
import shutil
import string
from typing import List, Dict, Optional
from pathlib import Path

# Default language of each supported site (used to skip translation when target matches)
SITE_DEFAULT_LANGUAGES: Dict[str, str] = {
    "fsacg": "chinese",
    "qidian": "chinese",
    "novelpia": "korean",
    "wattpad": "english",
}

# Target output language (currently only English; extend later for other targets)
TARGET_LANGUAGE: str = "english"


def get_site_from_url(url: str) -> Optional[str]:
    """Detect which site a URL belongs to."""
    url_lower = url.lower()
    for site in SITE_DEFAULT_LANGUAGES:
        if site in url_lower:
            return site
    return None


def get_site_default_language(url: str) -> Optional[str]:
    """Get the default language of the site for the given URL."""
    site = get_site_from_url(url)
    return SITE_DEFAULT_LANGUAGES.get(site) if site else None


def needs_translation(url: str, target_language: Optional[str] = None) -> bool:
    """
    Return True if we need to translate (site default != target).
    When target matches site default, we skip the translator.
    """
    target = target_language if target_language is not None else TARGET_LANGUAGE
    default = get_site_default_language(url)
    if default is None:
        return True  # Unknown site: translate to be safe
    return default.lower() != target.lower()


def sanitize_filename(input_string: str) -> str:
    """
    Sanitizes a string to be used as a filename by removing invalid characters.
    
    Args:
        input_string (str): The string to sanitize
        
    Returns:
        str: A valid filename string
    """
    # Define invalid characters (Windows and Unix systems)
    invalid_chars = '<>:"/\\|?*\x00-\x1f'
    
    # Remove invalid characters
    sanitized = re.sub(f'[{re.escape(invalid_chars)}]', '', input_string)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    # If the string is empty after sanitization, return a default name
    if not sanitized:
        return "unnamed_file"
        
    # Limit length to 255 characters (common filesystem limit)
    return sanitized[:255]

def replace_with_dictionary(text: str, replacement_dict: Dict[str, str], confident = False, debug: bool = False) -> str:
    """
    Replaces substrings in a text string using a dictionary of replacements.
    
    Args:
        text (str): The text string to process
        replacement_dict (Dict[str, str]): Dictionary where keys are substrings to find and values are replacements
        debug (bool): If True, prints debug information
        
    Returns:
        str: The text string with replacements applied
    """
    try:
        if debug:
            print(f"\n=== Replacing Substrings with Dictionary ===")
            print(f"Original text length: {len(text)} characters")
            print(f"Number of replacement rules: {len(replacement_dict)}")
        
        result = text
        replacements_made = 0
        
        # Apply each replacement from the dictionary
        for find_str, replace_str in replacement_dict.items():
            if find_str in result:
                count = result.count(find_str)
                if confident:
                    result = result.replace(find_str, replace_str)
                else:
                    result = result.replace(find_str, replace_str+"[?]")
                replacements_made += count
                
                if debug:
                    print(f"Replaced '{find_str}' with '{replace_str}' ({count} occurrences)")
        
        if debug:
            print(f"Total replacements made: {replacements_made}")
            print(f"Final text length: {len(result)} characters")
            if replacements_made > 0:
                print(f"Sample of result: {result[:100]}...")
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error replacing with dictionary: {str(e)}")
        raise e
