import re
import shutil
import string
from typing import List, Dict
from pathlib import Path

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
