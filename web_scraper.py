import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Callable, Dict, Union
from urllib.parse import urlparse
import time
import re
import string
import os
import json
from pathlib import Path
import base64
from openai import OpenAI
from PIL import Image, ImageEnhance
import random
import socket
from urllib3.exceptions import ProtocolError, MaxRetryError


class NoDuplicatesCookieJar(requests.cookies.RequestsCookieJar):
    """A CookieJar that prevents duplicate cookies by overwriting existing ones."""
    
    def set_cookie(self, cookie, *args, **kwargs):
        # Remove any existing cookies with the same name, domain, and path
        to_remove = []
        for domain in self._cookies:
            for path in self._cookies[domain]:
                for cookie_name in list(self._cookies[domain][path].keys()):
                    if cookie_name == cookie.name:
                        to_remove.append((domain, path, cookie_name))
        
        # Remove the old cookies
        for domain, path, cookie_name in to_remove:
            del self._cookies[domain][path][cookie_name]
        
        # Set the new cookie
        super().set_cookie(cookie, *args, **kwargs)

class SessionManager:
    def __init__(self, cookies_file: str = "cookies.json"):
        """
        Initialize the session manager with a cookies file.
        
        Args:
            cookies_file (str): Path to the JSON file storing cookies
        """
        self.cookies_file = cookies_file
        self.session = requests.Session()
        # Replace the default cookie jar with our custom one
        self.session.cookies = NoDuplicatesCookieJar()
        self.load_cookies()
    
    def save_cookies(self):
        """Save current session cookies to file"""
        # Convert cookies to simple name-value pairs
        cookies_dict = {}
        for cookie in self.session.cookies:
            # Skip any duplicate .SFCommunity cookies
            if cookie.name == '.SFCommunity' and cookie.name in cookies_dict:
                continue
            cookies_dict[cookie.name] = cookie.value
        
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies_dict, f)
    
    def load_cookies(self):
        """Load cookies from file if it exists"""
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)
                # Clear existing cookies first
                self.session.cookies.clear()
                # Add cookies as simple name-value pairs
                for name, value in cookies.items():
                    self.session.cookies.set(name, value)
        except (FileNotFoundError, json.JSONDecodeError):
            pass  # No cookies file or invalid format
    
    def set_cookies(self, cookies: Dict[str, str]):
        """
        Set cookies manually and save them.
        
        Args:
            cookies (Dict[str, str]): Dictionary of cookie name-value pairs
        """
        # Clear existing cookies first
        self.session.cookies.clear()
        
        # Add new cookies
        for name, value in cookies.items():
            # Special handling for .SFCommunity cookie
            if name == '.SFCommunity':
                # Ensure we only set it once
                if not any(c.name == '.SFCommunity' for c in self.session.cookies):
                    self.session.cookies.set(name, value)
            else:
                self.session.cookies.set(name, value)
        
        self.save_cookies()
    
    def get_session(self) -> requests.Session:
        """Get the current session with cookies"""
        return self.session
    
    def clear_cookies(self):
        """Clear all cookies and save empty state"""
        self.session.cookies.clear()
        self.save_cookies()
    
    def print_cookies(self):
        """Print all current cookies for debugging"""
        print("\nCurrent cookies:")
        for cookie in self.session.cookies:
            print(f"Name: {cookie.name}, Value: {cookie.value}, Domain: {cookie.domain}, Path: {cookie.path}")
        
        # Special check for .SFCommunity cookie
        sf_cookies = [c for c in self.session.cookies if c.name == '.SFCommunity']
        if len(sf_cookies) > 1:
            print(f"\nWARNING: Found {len(sf_cookies)} .SFCommunity cookies!")

# Create a global session manager
session_manager = SessionManager()

# Global confirmed working headers that bypass WAF
CONFIRMED_HEADERS = {
    'Host': 'www.qidian.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://book.qidian.com/',
    'Connection': 'keep-alive',
    'Cookie': 'newstatisticUUID=1749074184_557066739; _csrfToken=7a6b5022-bb1e-479e-a64f-e44ba7ad5a5a; fu=138564886; _ga_FZMMH98S83=GS2.1.s1750827610$o20$g1$t1750829182$j60$l0$h0; _ga=GA1.2.1005620528.1749074184; _ga_PFYW0QLV3P=GS2.1.s1750827610$o20$g1$t1750829183$j60$l0$h0; Hm_lvt_f00f67093ce2f38f215010b699629083=1749074186,1749699072; e1=%7B%22pid%22%3A%22qd_P_mycenter%22%2C%22eid%22%3A%22qd_H_mall_bottomaddownload%22%2C%22l7%22%3A%22hddl%22%7D; e2=%7B%22pid%22%3A%22qd_P_mycenter%22%2C%22eid%22%3A%22qd_H_mall_bottomaddownload%22%2C%22l7%22%3A%22hddl%22%7D; _gid=GA1.2.614213141.1750571536; traffic_search_engine=; supportWebp=false; traffic_utm_referer=; se_ref=; Hm_lpvt_f00f67093ce2f38f215010b699629083=1750829183; HMACCOUNT=98ECCFD5575F572E; ywkey=ykata4KHFPdu; ywguid=120482424609; ywopenid=3E4D05BAF58C8A6FA8DFD9D72E930A88; w_tsfp=ltvuV0MF2utBvS0Q7KrhlkKpFjEgcjA4h0wpEaR0f5thQLErU5mA0Y54t8z2MHbW48xnvd7DsZoyJTLYCJI3dwNCQ5+VcoAZ2giZkYB3iogQUBhlEsjUUV9KJ7lwvjgSf3hCNxS00jA8eIUd379yilkMsyN1zap3TO14fstJ019E6KDQmI5uDW3HlFWQRzaLbjcMcuqPr6g18L5a5WrZtAipJQ8mUutG0EPA1XlOBn9y4xO7IO8LNR2kIsr5SqA=',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-User': '?1',
    'Priority': 'u=0, i',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache'
}

# Enhanced headers to mimic a real browser more convincingly
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Referer': 'https://www.google.com/',
    'X-Requested-With': 'XMLHttpRequest'
}

def set_login_cookies(cookies: Dict[str, str]):
    """
    Set login cookies for future requests.
    
    Args:
        cookies (Dict[str, str]): Dictionary of cookie name-value pairs
    """
    session_manager.set_cookies(cookies)

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

def combine_txt_files(directory_path: str, output_filename: str = "combined_output.txt", 
                     sort_files: bool = True, key_func: Optional[Callable[[Path], any]] = None) -> str:
    """
    Combines all .txt files in the specified directory into a single file.
    
    Args:
        directory_path (str): Path to the directory containing .txt files
        output_filename (str): Name of the output file (default: combined_output.txt)
        sort_files (bool): Whether to sort files by name before combining (default: True)
        key_func (Callable[[Path], any], optional): A function that takes a Path object and returns 
            a value to sort by. For example, to sort by file creation time: 
            lambda p: p.stat().st_ctime
    
    Returns:
        str: Path to the combined output file
        
    Raises:
        FileNotFoundError: If the directory doesn't exist
        Exception: If no .txt files are found or if there's an error during processing
    """
    # Convert to Path object for easier handling
    dir_path = Path(directory_path)
    
    # Check if directory exists
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    # Get all .txt files
    txt_files = list(dir_path.glob("*.txt"))
    
    if not txt_files:
        raise Exception(f"No .txt files found in {directory_path}")
    
    # Sort files if requested
    if sort_files:
        txt_files.sort(key=key_func)
    
    # Create output file path
    output_path = dir_path / output_filename
    
    try:
        # Combine all files
        with open(output_path, 'w', encoding='utf-8') as outfile:
            for i, txt_file in enumerate(txt_files):
                # Add a separator between files
                if i > 0:
                    outfile.write("\n\n\f")
                outfile.write("[[["+txt_file.name+"]]]"+"\n\n")
                
                # Read and write content
                with open(txt_file, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
        
        return str(output_path)
        
    except Exception as e:
        raise Exception(f"Error combining files: {str(e)}")

def fetch_lists_from_url(url: str, list_class: Optional[str] = None, parent_div_class: Optional[str] = None, debug: bool = True) -> List[List[Dict[str, str]]]:
    """
    Fetches all lists (both ordered and unordered) from a given URL.
    Can filter lists by their class name and/or their parent div's class.
    Returns href links and text content from list items.
    
    Args:
        url (str): The URL of the website to scrape
        list_class (str, optional): If provided, only fetch lists with this class name
        parent_div_class (str, optional): If provided, only fetch lists inside divs with this class
        debug (bool): If True, prints debug information
        
    Returns:
        List[List[Dict[str, str]]]: A list of lists, where each inner list contains dictionaries
        with 'text' and 'href' keys for each list item
    """
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Add a small delay to be respectful
        time.sleep(1)
        
        # Send HTTP request with headers and session
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        if debug:
            print("\n=== Debug Information ===")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Current Cookies: {dict(session.cookies)}")
            print("\nFirst 500 characters of response content:")
            print(response.text[:500])
            print("\n=== End Debug Info ===\n")
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if debug:
            print("\n=== HTML Structure ===")
            if parent_div_class:
                print(f"\nLooking for divs with class: {parent_div_class}")
                parent_divs = soup.find_all('div', class_=parent_div_class)
                print(f"Found {len(parent_divs)} divs with class '{parent_div_class}'")
                for div in parent_divs[:3]:  # Show first 3 for debugging
                    lists_in_div = div.find_all(['ul', 'ol'])
                    print(f"- Div contains {len(lists_in_div)} lists")
                    for lst in lists_in_div[:2]:  # Show first 2 lists in each div
                        print(f"  - {lst.name} with classes: {lst.get('class', [])}")
                        # Show sample of links in the list
                        for li in lst.find_all('li')[:2]:
                            a_tag = li.find('a')
                            if a_tag and a_tag.get('href'):
                                print(f"    Link found: {a_tag.get_text(strip=True)} -> {a_tag.get('href')}")
            
            if list_class:
                print(f"\nLooking for lists with class: {list_class}")
                elements_with_class = soup.find_all(['ul', 'ol'], class_=list_class)
                print(f"Found {len(elements_with_class)} lists with class '{list_class}'")
                for elem in elements_with_class[:5]:  # Show first 5 for debugging
                    print(f"- {elem.name} tag with classes: {elem.get('class', [])}")
            
            print("\nAll lists found:")
            all_lists = soup.find_all(['ul', 'ol'])
            for lst in all_lists[:5]:  # Show first 5 for debugging
                parent_div_classes = lst.find_parent('div', class_=True)
                if parent_div_classes:
                    print(f"- {lst.name} with classes {lst.get('class', [])} inside div with classes {parent_div_classes.get('class', [])}")
                else:
                    print(f"- {lst.name} with classes {lst.get('class', [])} (no parent div with class)")
            print("=== End HTML Structure ===\n")
        
        # Find all lists (both ordered and unordered)
        all_lists = []
        
        # Function to process lists based on class and parent div
        def process_list(list_tag):
            # Check if list has the required class
            if list_class:
                tag_classes = list_tag.get('class', [])
                if list_class not in tag_classes:
                    return None
            
            # Check if list is inside a div with the required class
            if parent_div_class:
                parent_div = list_tag.find_parent('div', class_=parent_div_class)
                if not parent_div:
                    return None
            
            # Get items with their href links if they exist
            items = []
            for li in list_tag.find_all('li'):
                a_tag = li.find('a')
                if a_tag:
                    # If there's a link, get both href and text
                    href = a_tag.get('href')
                    if href:
                        # Make URL absolute if it's relative
                        if not href.startswith(('http://', 'https://')):
                            parsed_base = urlparse(url)
                            base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
                            href = base_url + ('' if href.startswith('/') else '/') + href
                        
                        items.append({
                            'text': a_tag.get_text(strip=True),
                            'href': href
                        })
                else:
                    # If no link, just get the text
                    text = li.get_text(strip=True)
                    if text:
                        items.append({
                            'text': text,
                            'href': None
                        })
            
            return items if items else None
        
        # First try to find lists within the specified parent div
        if parent_div_class:
            parent_divs = soup.find_all('div', class_=parent_div_class)
            for div in parent_divs:
                for list_tag in div.find_all(['ul', 'ol']):
                    items = process_list(list_tag)
                    if items:
                        all_lists.append(items)
        else:
            # If no parent div specified, search all lists
            for list_tag in soup.find_all(['ul', 'ol']):
                items = process_list(list_tag)
                if items:
                    all_lists.append(items)
        
        return all_lists
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def fetch_div_content(url: str, div_id: str = None, div_class: str = None, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches the content of div(s) from a given URL using either ID or class name.
    Preserves line breaks by converting <br> and <p> tags to newlines.
    
    Args:
        url (str): The URL of the website to scrape
        div_id (str, optional): The ID of the div to find (for single div)
        div_class (str, optional): The class name of divs to find (for multiple divs)
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[Union[str, List[str]]]: 
            - Single string if div_id is provided and found
            - List of strings if div_class is provided and found
            - None if no matching divs found
    """
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if div_id is None and div_class is None:
        raise ValueError("Either div_id or div_class must be provided")
    if div_id is not None and div_class is not None:
        raise ValueError("Only one of div_id or div_class should be provided")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Use the enhanced request function with retry logic
        response = make_request_with_retry(session, url, headers, max_retries=5, debug=debug)
        
        # If we're still getting 202 responses, try the persistent 202 handler
        if response.status_code == 202:
            if debug:
                print("Normal retry logic failed, trying persistent 202 handler...")
            response = handle_persistent_202(url, headers, max_attempts=3, debug=debug)
            if response is None:
                if debug:
                    print("All strategies failed for persistent 202 responses")
                return None
        
        if debug:
            print("\n=== Debug Information ===")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Current Cookies: {dict(session.cookies)}")
            print("\nFirst 500 characters of response content:")
            print(response.text[:500])
            print("\n=== End Debug Info ===\n")
        
        # Check if we got a captcha challenge
        if response.status_code == 202 or 'captcha' in response.text.lower():
            if debug:
                print("WARNING: Captcha challenge detected. You may need to:")
                print("1. Wait a few minutes before trying again")
                print("2. Use a different IP address")
                print("3. Solve the captcha manually in a browser")
            return None
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        def process_div_content(div_element):
            """Helper function to process div content consistently"""
            if not div_element:
                return None
                
            # Replace <br> tags with newlines
            for br in div_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in div_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = div_element.get_text()
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            return content.strip()
        
        if div_id is not None:
            # Find div by ID (single div)
            target_div = soup.find('div', id=div_id)
            
            if debug:
                print("\n=== HTML Structure (ID Search) ===")
                print(f"Looking for div with id: {div_id}")
                if target_div:
                    print("Found target div!")
                    print(f"Div tag structure: {target_div.name} {target_div.attrs}")
                else:
                    print("Target div not found.")
                    # Print all div IDs to help identify the correct one
                    all_divs = soup.find_all('div', id=True)
                    if all_divs:
                        print("\nAvailable div IDs:")
                        for div in all_divs:
                            print(f"- {div.get('id')}")
                    else:
                        print("No divs with IDs found in the page.")
                print("=== End HTML Structure ===\n")
            
            return process_div_content(target_div)
            
        else:
            # Find divs by class (multiple divs)
            target_divs = soup.find_all('div', class_=div_class)
            
            if debug:
                print("\n=== HTML Structure (Class Search) ===")
                print(f"Looking for divs with class: {div_class}")
                print(f"Found {len(target_divs)} divs with class '{div_class}'")
                
                if not target_divs:
                    # Print all div classes to help identify the correct one
                    all_divs = soup.find_all('div', class_=True)
                    if all_divs:
                        print("\nAvailable div classes:")
                        classes_found = set()
                        for div in all_divs:
                            div_classes = div.get('class', [])
                            if isinstance(div_classes, list):
                                classes_found.update(div_classes)
                            else:
                                classes_found.add(div_classes)
                        for class_name in sorted(classes_found):
                            print(f"- {class_name}")
                    else:
                        print("No divs with classes found in the page.")
                else:
                    for i, div in enumerate(target_divs):
                        print(f"Div {i+1}: {div.name} {div.attrs}")
                print("=== End HTML Structure ===\n")
            
            if not target_divs:
                return None
            
            # Process all found divs
            results = []
            for i, div in enumerate(target_divs):
                content = process_div_content(div)
                if content:
                    results.append(content)
                    if debug:
                        print(f"Processed div {i+1}: {len(content)} characters")
            
            return results if results else None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def fetch_image_url(url: str, img_id: str, debug: bool = True) -> Optional[str]:
    """
    Fetches the image URL from an element with the specified ID.
    Works with both <img> tags and elements containing background-image style.
    
    Args:
        url (str): The URL of the website to scrape
        img_id (str): The ID of the element containing the image
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[str]: The absolute URL of the image if found, None otherwise
    """
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Add a small delay to be respectful
        time.sleep(1)
        
        # Send HTTP request with headers and session
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        if debug:
            print("\n=== Debug Information ===")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Current Cookies: {dict(session.cookies)}")
            print("\nFirst 500 characters of response content:")
            print(response.text[:500])
            print("\n=== End Debug Info ===\n")
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the element with the specified ID
        element = soup.find(id=img_id)
        
        if debug:
            print("\n=== HTML Structure ===")
            print(f"Looking for element with id: {img_id}")
            if element:
                print("Found element!")
                print(f"Tag: {element.name}")
                print(f"Attributes: {element.attrs}")
            else:
                print("Element not found.")
                # Print all elements with IDs to help identify the correct one
                elements_with_id = soup.find_all(id=True)
                if elements_with_id:
                    print("\nAvailable element IDs:")
                    for elem in elements_with_id:
                        print(f"- {elem.get('id')}")
                else:
                    print("No elements with IDs found in the page.")
            print("=== End HTML Structure ===\n")
        
        if not element:
            return None
            
        image_url = None
        
        # Check if the element is an img tag
        if element.name == 'img':
            # Try src attribute first, then data-src if src is not available
            image_url = element.get('src') or element.get('data-src')
        
        # If no image URL found, check for background-image in style attribute
        if not image_url:
            style = element.get('style', '')
            if 'background-image' in style:
                # Extract URL from background-image: url('...')
                match = re.search(r"background-image:\s*url\(['\"](.*?)['\"]\)", style)
                if match:
                    image_url = match.group(1)
        
        # If still no image URL found, look for img tag inside the element
        if not image_url and element.find('img'):
            img_tag = element.find('img')
            image_url = img_tag.get('src') or img_tag.get('data-src')
        
        if image_url:
            # Make URL absolute if it's relative
            if not image_url.startswith(('http://', 'https://')):
                parsed_base = urlparse(url)
                base_url = f"{parsed_base.scheme}://{parsed_base.netloc}"
                image_url = base_url + ('' if image_url.startswith('/') else '/') + image_url
            
            if debug:
                print(f"Found image URL: {image_url}")
            
            return image_url
        
        if debug:
            print("No image URL found in the element.")
        return None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def download_image(image_url: str, save_path: str, debug: bool = True) -> bool:
    """
    Downloads an image from the given URL using the current session's cookies.
    
    Args:
        image_url (str): The URL of the image to download
        save_path (str): The path where the image should be saved
        debug (bool): If True, prints debug information
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Validate URL
        result = urlparse(image_url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
            
        # Create directory if it doesn't exist
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # Get session with cookies
        session = session_manager.get_session()
        
        # Add image-specific headers
        img_headers = headers.copy()
        img_headers.update({
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Referer': image_url,  # Add referer header
        })
        
        if debug:
            print(f"\n=== Downloading Image ===")
            print(f"URL: {image_url}")
            print(f"Save path: {save_path}")
            print(f"Using cookies: {dict(session.cookies)}")
            print(f"Headers: {img_headers}")
        
        # First make a HEAD request to check headers without downloading
        try:
            head_response = session.head(image_url, headers=img_headers, timeout=10)
            head_response.raise_for_status()
            content_type = head_response.headers.get('content-type', '')
            content_length = int(head_response.headers.get('content-length', 0))
            
            if debug:
                print(f"HEAD request successful")
                print(f"Content Type from HEAD: {content_type}")
                print(f"Content Length from HEAD: {content_length} bytes")
        except:
            if debug:
                print("HEAD request failed, will try direct GET request")
            content_type = ''
            content_length = 0
        
        # Stream the response to handle large files efficiently
        response = session.get(image_url, headers=img_headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # If we didn't get content type from HEAD request, try from GET response
        if not content_type:
            content_type = response.headers.get('content-type', '')
            content_length = int(response.headers.get('content-length', 0))
            
            if debug:
                print(f"Content Type from GET: {content_type}")
                print(f"Content Length from GET: {content_length} bytes")
        
        # If still no content type, try to verify by checking first few bytes
        first_bytes = None
        if not content_type:
            if debug:
                print("No content-type header, checking file signature...")
            # Get first few bytes to check file signature
            for chunk in response.iter_content(chunk_size=8):
                first_bytes = chunk
                break
            
            # Common image file signatures
            image_signatures = {
                b'\xFF\xD8\xFF': 'image/jpeg',
                b'\x89\x50\x4E\x47': 'image/png',
                b'GIF8': 'image/gif',
                b'RIFF': 'image/webp'
            }
            
            # Check file signature
            if first_bytes:
                for signature, img_type in image_signatures.items():
                    if first_bytes.startswith(signature):
                        content_type = img_type
                        if debug:
                            print(f"Detected image type from signature: {content_type}")
                        break
        
        # Verify it's an image either by content-type or file signature
        is_image = content_type.startswith('image/') if content_type else False
        if not is_image and not any(first_bytes.startswith(sig) for sig in image_signatures.keys()):
            raise ValueError(f"URL does not appear to point to a valid image. Content-type: {content_type}")
        
        # Download the image
        with open(save_path, 'wb') as f:
            if first_bytes:  # Write the first bytes we already read
                f.write(first_bytes)
            # Continue with the rest of the file
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify the downloaded file
        if os.path.getsize(save_path) == 0:
            os.remove(save_path)
            raise ValueError("Downloaded file is empty")
        
        if debug:
            print(f"Image successfully downloaded to: {save_path}")
            print(f"File size: {os.path.getsize(save_path)} bytes")
            print("=== Download Complete ===\n")
        
        return True
        
    except requests.RequestException as e:
        if debug:
            print(f"Error downloading image: {str(e)}")
            print(f"Response status code: {getattr(e.response, 'status_code', 'N/A')}")
            print(f"Response headers: {getattr(e.response, 'headers', {})}")
        return False
    except Exception as e:
        if debug:
            print(f"Error: {str(e)}")
        return False

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def upload_to_uguu(file_path: str, debug: bool = True) -> str:
    """
    Uploads a file to uguu.se and returns the download URL.
    Files are kept for 24 hours.
    
    Args:
        file_path (str): Path to the file to upload
        debug (bool): If True, prints debug information
        
    Returns:
        str: The download URL for the uploaded file
    """
    try:
        if debug:
            print(f"\n=== Uploading to uguu.se ===")
            print(f"File path: {file_path}")
        
        # Get the filename from the path
        filename = os.path.basename(file_path)
        
        # Upload the file
        files = {
            'files[]': (filename, open(file_path, 'rb'), 'image/jpeg')
        }
        response = requests.post('https://uguu.se/upload.php', files=files)
        response.raise_for_status()
        
        if debug:
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")
        
        # Parse the JSON response
        data = response.json()
        
        if debug:
            print(f"Parsed JSON response: {data}")
        
        if data.get('success') and data.get('files'):
            url = data['files'][0]['url'].replace('\\/', '/')  # Fix escaped slashes
            if debug:
                print(f"Extracted URL: {url}")
            if url.startswith('https://') and '.uguu.se/' in url:
                return url
            
        raise Exception(f"Invalid response format from uguu.se: {data}")
                
    except Exception as e:
        if debug:
            print(f"Error uploading to uguu.se: {str(e)}")
        raise e

def adjust_image(image_path: str, brightness_factor: float = 1.0, contrast_factor: float = 1.0, output_path: str = None, debug: bool = True) -> str:
    """
    Converts image to grayscale and adjusts the brightness and contrast using Pillow.
    
    Args:
        image_path (str): Path to the input image
        brightness_factor (float): Factor to adjust brightness. 1.0 is original, >1 is brighter, <1 is darker
        contrast_factor (float): Factor to adjust contrast. 1.0 is original, >1 is more contrast, <1 is less
        output_path (str, optional): Path to save the adjusted image. If None, will modify original filename
        debug (bool): If True, prints debug information
        
    Returns:
        str: Path to the adjusted image
    """
    try:
        if debug:
            print(f"\n=== Adjusting Image ===")
            print(f"Input path: {image_path}")
            print(f"Brightness factor: {brightness_factor}")
            print(f"Contrast factor: {contrast_factor}")
        
        # Open the image
        img = Image.open(image_path)
        
        # Convert to grayscale
        img = img.convert('L')
        
        if debug:
            print("Converted to grayscale")
        
        # Adjust brightness
        if brightness_factor != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_factor)
            if debug:
                print(f"Adjusted brightness by factor {brightness_factor}")
        
        # Adjust contrast
        if contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)
            if debug:
                print(f"Adjusted contrast by factor {contrast_factor}")
        
        # Generate output path if not provided
        if output_path is None:
            filename, ext = os.path.splitext(image_path)
            output_path = f"{filename}_gray_adjusted{ext}"
        
        # Save the adjusted image with high quality
        img.save(output_path, quality=95)
        
        if debug:
            print(f"Adjusted grayscale image saved to: {output_path}")
        
        return output_path
        
    except Exception as e:
        if debug:
            print(f"Error adjusting image: {str(e)}")
        raise e

def find_white_lines(img, threshold=250, min_line_width=100, debug=True):
    """
    Find horizontal white lines in a grayscale image.
    
    Args:
        img: PIL Image in grayscale mode
        threshold (int): Brightness threshold (0-255) to consider a pixel as white
        min_line_width (int): Minimum width of consecutive white pixels to consider as a line
        debug (bool): If True, prints debug information
        
    Returns:
        list: Y-coordinates where white lines are found
    """
    width, height = img.size
    pixels = img.load()
    white_lines = []
    
    for y in range(height):
        white_count = 0
        is_white_line = True
        
        for x in range(width):
            if pixels[x, y] >= threshold:
                white_count += 1
            else:
                if white_count < min_line_width:
                    is_white_line = False
                    break
                white_count = 0
                
        if is_white_line and white_count >= min_line_width:
            white_lines.append(y)
    
    if debug:
        print(f"Found {len(white_lines)} white lines at positions: {white_lines}")
    
    return white_lines

def split_image_at_whitespace(image_path: str, min_height: int = 100, max_height: int = 800, threshold: int = 250, min_line_width: int = 70, output_dir: str = None, debug: bool = True) -> list:
    """
    Splits an image at horizontal white lines, ensuring each part is within size constraints.
    
    Args:
        image_path (str): Path to the input image
        min_height (int): Minimum height for a split section
        max_height (int): Maximum height for a split section
        threshold (int): Brightness threshold (0-255) to consider a pixel as white
        min_line_width (int): Minimum width of consecutive white pixels to consider as a line
        output_dir (str, optional): Directory to save split images. If None, uses same directory as input
        debug (bool): If True, prints debug information
        
    Returns:
        list: Paths to the split image files
    """
    try:
        from PIL import Image
        import os
        
        if debug:
            print(f"\n=== Splitting Image at White Lines ===")
            print(f"Input path: {image_path}")
        
        # Get absolute path of input image
        image_path = os.path.abspath(image_path)
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")
        
        # Open and convert to grayscale
        img = Image.open(image_path).convert('L')
        width, height = img.size
        
        if debug:
            print(f"Image dimensions: {width}x{height}")
        
        # Find white lines
        white_lines = find_white_lines(img, threshold, min_line_width, debug)
        
        # Prepare output directory
        if output_dir is None:
            # Use the same directory as the input file
            output_dir = os.path.dirname(image_path)
            if not output_dir:  # If still empty, use current directory
                output_dir = os.getcwd()
        
        # Make sure output_dir is absolute
        output_dir = os.path.abspath(output_dir)
        
        if debug:
            print(f"Output directory: {output_dir}")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get base filename without extension
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        
        # Split image at white lines
        split_files = []
        current_y = 0
        part_num = 1
        
        for next_y in white_lines + [height]:
            section_height = next_y - current_y
            
            # Skip if section is too small
            if section_height < min_height:
                continue
                
            # If section is too large, force split at max_height
            if section_height > max_height:
                splits = range(current_y, next_y, max_height)
                for split_start in splits:
                    split_end = min(split_start + max_height, next_y)
                    
                    # Create the cropped image
                    cropped = img.crop((0, split_start, width, split_end))
                    output_path = os.path.join(output_dir, f"{base_name}_part{part_num}.png")
                    cropped.save(output_path, quality=95)
                    split_files.append(output_path)
                    
                    if debug:
                        print(f"Saved part {part_num} ({split_end-split_start}px) to: {output_path}")
                    
                    part_num += 1
            else:
                # Create the cropped image
                cropped = img.crop((0, current_y, width, next_y))
                output_path = os.path.join(output_dir, f"{base_name}_part{part_num}.png")
                cropped.save(output_path, quality=95)
                split_files.append(output_path)
                
                if debug:
                    print(f"Saved part {part_num} ({section_height}px) to: {output_path}")
                
                part_num += 1
            
            current_y = next_y
        
        if debug:
            print(f"Split into {len(split_files)} parts")
            print(f"Split files saved in: {output_dir}")
        
        return split_files
        
    except Exception as e:
        if debug:
            print(f"Error splitting image: {str(e)}")
        raise e

def filter_response(response_text: str, debug: bool = True) -> str:
    """
    Filters out lines that contain error indicators like "I'm sorry" or "unable".
    
    Args:
        response_text (str): The response text to filter
        debug (bool): If True, prints debug information about filtered lines
        
    Returns:
        str: The filtered response text
    """
    if not response_text:
        return response_text
    
    # Define error indicators
    error_indicators = ["i'm sorry", "unable", "cannot", "sorry,", "apologize", "Sorry", "I'm sorry"]
    
    # Split into lines and filter
    lines = response_text.split('\n')
    filtered_lines = []
    filtered_count = 0
    
    for line in lines:
        line_lower = line.lower().strip()
        should_filter = any(indicator in line_lower for indicator in error_indicators)
        
        if should_filter:
            filtered_count += 1
            if debug:
                print(f"Filtered out line: {line.strip()}")
        else:
            filtered_lines.append(line)
    
    if debug and filtered_count > 0:
        print(f"Filtered out {filtered_count} lines containing error indicators")
    
    return '\n'.join(filtered_lines)

def analyze_image(image_path: str, prompt: str = "What text do you see in this image?", brightness: float = None, contrast: float = None, split: bool = False, min_height: int = 30, max_height: int = 800, debug: bool = True) -> str:
    """
    Sends an image to GPT-4o for analysis using uguu.se as intermediary.
    Can optionally adjust image brightness/contrast and split at white lines.
    
    Args:
        image_path (str): Path to the image file
        prompt (str): The prompt to send to GPT-4o
        brightness (float, optional): Brightness adjustment factor. >1 is brighter, <1 is darker
        contrast (float, optional): Contrast adjustment factor. >1 is more contrast, <1 is less
        split (bool): Whether to split the image at white lines before analysis
        min_height (int): Minimum height for split sections (if split=True)
        max_height (int): Maximum height for split sections (if split=True)
        debug (bool): If True, prints debug information
        
    Returns:
        str: The response from GPT-4o
    """
    try:
        # Initialize the OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        if debug:
            print(f"\n=== Analyzing Image ===")
            print(f"Image path: {image_path}")
            print(f"Prompt: {prompt}")
        
        # Check if file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Adjust image if requested
        if brightness is not None or contrast is not None:
            image_path = adjust_image(
                image_path,
                brightness_factor=brightness if brightness is not None else 1.0,
                contrast_factor=contrast if contrast is not None else 1.0,
                debug=debug
            )
        
        # Split image if requested
        if split:
            image_parts = split_image_at_whitespace(
                image_path,
                min_height=min_height,
                max_height=max_height,
                debug=debug
            )
            
            # Analyze each part
            responses = []
            for part_path in image_parts:
                # Upload to uguu.se to get a public URL
                public_url = upload_to_uguu(part_path, debug)
                
                if debug:
                    print(f"Image part uploaded to: {public_url}")
                
                # Create the payload for the API
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": public_url
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.3
                )
                responses.append(response.choices[0].message.content)
            
            # Combine responses and filter
            # small optimization, last response is usually empty
            combined_response = "\n\n".join(responses[:-1])
            filtered_response = filter_response(combined_response, debug)
            
            if debug:
                print("Analysis of all parts complete!")
                print("=== End Analysis ===\n")
            
            return filtered_response
            
        else:
            # Process single image as before
            public_url = upload_to_uguu(image_path, debug)
            
            if debug:
                print(f"Image uploaded to: {public_url}")
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": public_url
                                }
                            }
                        ]
                    }
                ],
                temperature=0.3
            )
            
            # Filter the response
            filtered_response = filter_response(response.choices[0].message.content, debug)
            
            if debug:
                print("Analysis complete!")
                print("=== End Analysis ===\n")
            
            return filtered_response
        
    except Exception as e:
        if debug:
            print(f"Error analyzing image: {str(e)}")
        raise e

def analyze_image_from_url(url: str, div_id: str = None, prompt: str = "What text do you see in this image?", debug: bool = True) -> str:
    """
    Downloads an image from a URL and sends it to GPT-4 Vision for analysis.
    
    Args:
        url (str): URL of the webpage or direct image
        div_id (str, optional): If provided, looks for an image in this div
        prompt (str): The prompt to send to GPT-4 Vision
        debug (bool): If True, prints debug information
        
    Returns:
        str: The response from GPT-4 Vision
    """
    try:
        temp_dir = "temp_images"
        os.makedirs(temp_dir, exist_ok=True)
        temp_image_path = os.path.join(temp_dir, "temp_image.jpg")
        
        if div_id:
            # If div_id is provided, try to find image in that div
            image_url = fetch_image_url(url, div_id, debug)
            if not image_url:
                raise ValueError(f"No image found in div with id: {div_id}")
        else:
            # If no div_id, assume url is direct image link
            image_url = url
        
        # Download the image
        success = download_image(image_url, temp_image_path, debug)
        if not success:
            raise Exception("Failed to download image")
        
        # Analyze the image
        result = analyze_image(temp_image_path, prompt, debug)
        
        # Clean up
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error processing image from URL: {str(e)}")
        raise e

def fetch_main_content(url: str, main_id: str = None, main_class: str = None, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches the content of main element(s) from a given URL using either ID or class name.
    Preserves line breaks by converting <br> and <p> tags to newlines.
    
    Args:
        url (str): The URL of the website to scrape
        main_id (str, optional): The ID of the main element to find (for single main)
        main_class (str, optional): The class name of main elements to find (for multiple mains)
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[Union[str, List[str]]]: 
            - Single string if main_id is provided and found
            - List of strings if main_class is provided and found
            - None if no matching main elements found
    """
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if main_id is None and main_class is None:
        raise ValueError("Either main_id or main_class must be provided")
    if main_id is not None and main_class is not None:
        raise ValueError("Only one of main_id or main_class should be provided")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Use the enhanced request function with retry logic
        response = make_request_with_retry(session, url, headers, max_retries=5, debug=debug)
        
        # If we're still getting 202 responses, try the persistent 202 handler
        if response.status_code == 202:
            if debug:
                print("Normal retry logic failed, trying persistent 202 handler...")
            response = handle_persistent_202(url, headers, max_attempts=3, debug=debug)
            if response is None:
                if debug:
                    print("All strategies failed for persistent 202 responses")
                return None
        
        if debug:
            print("\n=== Debug Information ===")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Current Cookies: {dict(session.cookies)}")
            print("\nFirst 500 characters of response content:")
            print(response.text[:500])
            print("\n=== End Debug Info ===\n")
        
        # Check if we got a captcha challenge
        if response.status_code == 202 or 'captcha' in response.text.lower():
            if debug:
                print("WARNING: Captcha challenge detected. You may need to:")
                print("1. Wait a few minutes before trying again")
                print("2. Use a different IP address")
                print("3. Solve the captcha manually in a browser")
            return None
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        def process_main_content(main_element):
            """Helper function to process main content consistently"""
            if not main_element:
                if debug:
                    print("❌ Main element is None")
                return None
            
            if debug:
                print(f"🔍 Processing main element: {main_element.name} {main_element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(main_element))}")
            
            # Replace <br> tags with newlines
            for br in main_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in main_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = main_element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        if main_id is not None:
            # Find main by ID (single main)
            target_main = soup.find('main', id=main_id)
            
            if debug:
                print("\n=== HTML Structure (Main ID Search) ===")
                print(f"Looking for main with id: {main_id}")
                if target_main:
                    print("Found target main!")
                    print(f"Main tag structure: {target_main.name} {target_main.attrs}")
                else:
                    print("Target main not found.")
                    # Print all main IDs to help identify the correct one
                    all_mains = soup.find_all('main', id=True)
                    if all_mains:
                        print("\nAvailable main IDs:")
                        for main_elem in all_mains:
                            print(f"- {main_elem.get('id')}")
                    else:
                        print("No main elements with IDs found in the page.")
                print("=== End HTML Structure ===\n")
            
            return process_main_content(target_main)
            
        else:
            # Find mains by class (multiple mains)
            target_mains = soup.find_all('main', class_=main_class)
            
            if debug:
                print(f"\nLooking for main elements with class: {main_class}")
                print(f"Found {len(target_mains)} main elements with class '{main_class}'")
                
                # Show details of each found main element
                for i, main_elem in enumerate(target_mains):
                    print(f"Main {i+1}: {main_elem.name} {main_elem.attrs}")
                    print(f"  HTML length: {len(str(main_elem))}")
                    print(f"  Text content length: {len(main_elem.get_text())}")
                    print(f"  First 100 chars: {repr(main_elem.get_text()[:100])}")
            
            if not target_mains:
                return None
            
            # Process all found main elements
            results = []
            for i, main_elem in enumerate(target_mains):
                if debug:
                    print(f"\n--- Processing main {i+1} ---")
                content = process_main_content(main_elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed main {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ Main {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            return results if results else None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def handle_waf_response(response, session, debug: bool = True) -> bool:
    """
    Handles WAF (Web Application Firewall) responses and captcha challenges.
    Also processes and sets cookies from 202 responses.
    
    Args:
        response: The HTTP response object
        session: The requests session object
        debug (bool): If True, prints debug information
        
    Returns:
        bool: True if response should be retried, False if it's a captcha challenge
    """
    if debug:
        print(f"\n=== WAF Response Analysis ===")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
    
    # Check for 202 status code and handle Set-Cookie headers
    if response.status_code == 202:
        if debug:
            print("Status 202 detected - checking for Set-Cookie headers")
        
        # Check for Set-Cookie headers - handle multiple headers properly
        set_cookie_headers = []
        for header_name, header_value in response.headers.items():
            if header_name.lower() == 'set-cookie':
                set_cookie_headers.append(header_value)
        
        if set_cookie_headers:
            if debug:
                print(f"Found {len(set_cookie_headers)} Set-Cookie headers")
            
            # Process each Set-Cookie header
            for cookie_header in set_cookie_headers:
                if debug:
                    print(f"Processing cookie: {cookie_header}")
                
                try:
                    # Parse the cookie header more comprehensively
                    # Format: name=value; Domain=domain; Path=path; Expires=date; HttpOnly; Secure
                    cookie_parts = [part.strip() for part in cookie_header.split(';')]
                    
                    # Extract name=value from the first part
                    if cookie_parts and '=' in cookie_parts[0]:
                        name_value = cookie_parts[0]
                        cookie_name, cookie_value = name_value.split('=', 1)
                        cookie_name = cookie_name.strip()
                        cookie_value = cookie_value.strip()
                        
                        # Parse additional attributes - only use supported ones
                        cookie_kwargs = {}
                        for part in cookie_parts[1:]:
                            if '=' in part:
                                attr_name, attr_value = part.split('=', 1)
                                attr_name = attr_name.strip().lower()
                                attr_value = attr_value.strip()
                                
                                if attr_name == 'domain':
                                    cookie_kwargs['domain'] = attr_value
                                elif attr_name == 'path':
                                    cookie_kwargs['path'] = attr_value
                                elif attr_name == 'expires':
                                    cookie_kwargs['expires'] = attr_value
                                # Note: max-age is not supported by requests.cookies.set()
                                # We'll handle it by converting to expires if needed
                            else:
                                # Handle flags like HttpOnly, Secure
                                attr_name = part.strip().lower()
                                if attr_name == 'httponly':
                                    cookie_kwargs['httponly'] = True
                                elif attr_name == 'secure':
                                    cookie_kwargs['secure'] = True
                                # Note: samesite is not supported by requests.cookies.set()
                        
                        # Set the cookie in the session with supported attributes only
                        session.cookies.set(cookie_name, cookie_value, **cookie_kwargs)
                        
                        if debug:
                            print(f"Set cookie: {cookie_name} = {cookie_value}")
                            if cookie_kwargs:
                                print(f"  Attributes: {cookie_kwargs}")
                            
                            # Check for duplicate cookies after setting
                            duplicate_count = 0
                            for c in session.cookies:
                                if c.name == cookie_name:
                                    duplicate_count += 1
                            
                            if duplicate_count > 1:
                                print(f"  WARNING: Found {duplicate_count} cookies with name '{cookie_name}'")
                        
                        # Also update the session manager's cookies
                        session_manager.save_cookies()
                        
                except Exception as e:
                    if debug:
                        print(f"Error processing cookie header '{cookie_header}': {str(e)}")
        
        # Clean up any duplicate cookies after processing all Set-Cookie headers
        cleanup_duplicate_cookies(session, debug)
        
        # After processing cookies, check if we should retry the request
        if debug:
            print("202 response processed - will retry request with new cookies")
        
        # For 202 responses, we typically want to retry after processing cookies
        # unless there are clear WAF indicators
        waf_indicators = [
            'x-waf-captcha',
            'cf-ray',
            'cloudflare',
            'captcha',
            'challenge'
        ]
        
        response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        for indicator in waf_indicators:
            if any(indicator in header.lower() for header in response_headers_lower.keys()):
                if debug:
                    print(f"WAF detected in 202 response: {indicator}")
                return False  # Don't retry, this is a captcha challenge
        
        # If we get here, it's a 202 with cookies but no captcha
        # This might be a temporary redirect or challenge that we can retry
        if debug:
            print("202 response with cookies processed - will retry")
        return True
    
    # Check for common WAF indicators in other responses
    waf_indicators = [
        'x-waf-captcha',
        'cf-ray',
        'cloudflare',
        'captcha',
        'challenge'
    ]
    
    response_headers_lower = {k.lower(): v for k, v in response.headers.items()}
    
    for indicator in waf_indicators:
        if any(indicator in header.lower() for header in response_headers_lower.keys()):
            if debug:
                print(f"WAF detected: {indicator}")
            return False  # Don't retry, this is a captcha challenge
    
    # Check response content for captcha indicators
    content_lower = response.text.lower()
    captcha_indicators = [
        'captcha',
        'challenge',
        'verify you are human',
        'security check',
        'cloudflare'
    ]
    
    for indicator in captcha_indicators:
        if indicator in content_lower:
            if debug:
                print(f"Captcha content detected: {indicator}")
            return False
    
    return True  # Response looks normal, can retry

def handle_202_response_flow(session, url: str, response, debug: bool = True):
    """
    Properly handles 202 responses by following the expected server flow.
    
    Args:
        session: The requests session
        url (str): The original URL
        response: The 202 response
        debug (bool): If True, prints debug information
        
    Returns:
        requests.Response: The follow-up response or the original 202 response
    """
    if debug:
        print(f"\n=== Handling 202 Response Flow ===")
        print(f"Original URL: {url}")
        print(f"202 Response Headers: {dict(response.headers)}")
    
    # Step 1: Process cookies from the 202 response
    if debug:
        print("Step 1: Processing cookies from 202 response")
    
    set_cookie_headers = []
    for header_name, header_value in response.headers.items():
        if header_name.lower() == 'set-cookie':
            set_cookie_headers.append(header_value)
    
    if set_cookie_headers:
        if debug:
            print(f"Found {len(set_cookie_headers)} Set-Cookie headers")
        
        # Process each Set-Cookie header
        for cookie_header in set_cookie_headers:
            if debug:
                print(f"Processing cookie: {cookie_header}")
            
            try:
                # Parse the cookie header
                cookie_parts = [part.strip() for part in cookie_header.split(';')]
                
                if cookie_parts and '=' in cookie_parts[0]:
                    name_value = cookie_parts[0]
                    cookie_name, cookie_value = name_value.split('=', 1)
                    cookie_name = cookie_name.strip()
                    cookie_value = cookie_value.strip()
                    
                    # Parse additional attributes
                    cookie_kwargs = {}
                    for part in cookie_parts[1:]:
                        if '=' in part:
                            attr_name, attr_value = part.split('=', 1)
                            attr_name = attr_name.strip().lower()
                            attr_value = attr_value.strip()
                            
                            if attr_name == 'domain':
                                cookie_kwargs['domain'] = attr_value
                            elif attr_name == 'path':
                                cookie_kwargs['path'] = attr_value
                            elif attr_name == 'expires':
                                cookie_kwargs['expires'] = attr_value
                        else:
                            attr_name = part.strip().lower()
                            if attr_name == 'httponly':
                                cookie_kwargs['httponly'] = True
                            elif attr_name == 'secure':
                                cookie_kwargs['secure'] = True
                    
                    # Set the cookie
                    session.cookies.set(cookie_name, cookie_value, **cookie_kwargs)
                    
                    if debug:
                        print(f"Set cookie: {cookie_name} = {cookie_value}")
                    
                    # Update session manager
                    session_manager.save_cookies()
                    
            except Exception as e:
                if debug:
                    print(f"Error processing cookie: {str(e)}")
    
    # Clean up duplicate cookies
    cleanup_duplicate_cookies(session, debug)
    
    # Step 2: Wait for server processing (202 means "Accepted" - server is processing)
    wait_time = 5  # Wait 5 seconds for server to process
    if debug:
        print(f"Step 2: Waiting {wait_time} seconds for server processing...")
    time.sleep(wait_time)
    
    # Step 3: Make follow-up request with the same URL but updated cookies
    if debug:
        print("Step 3: Making follow-up request with processed cookies")
        print(f"Current cookies: {dict(session.cookies)}")
    
    # Create headers for follow-up request
    follow_up_headers = create_realistic_browser_headers(url, debug=debug)
    
    # Add headers that indicate this is a follow-up request
    follow_up_headers.update({
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Site': 'same-origin',  # This is a follow-up to the same site
    })
    
    if debug:
        print("Follow-up Request Headers:")
        for key, value in follow_up_headers.items():
            print(f"  {key}: {value}")
    
    try:
        follow_up_response = session.get(url, headers=follow_up_headers, timeout=30)
        
        if debug:
            print(f"Follow-up response status: {follow_up_response.status_code}")
        
        return follow_up_response
        
    except Exception as e:
        if debug:
            print(f"Error in follow-up request: {str(e)}")
        return response  # Return original 202 response if follow-up fails

def make_request_with_retry(session, url: str, headers: dict, max_retries: int = 3, debug: bool = True):
    """
    Makes an HTTP request with retry logic and WAF handling.
    
    Args:
        session: The requests session
        url (str): The URL to request
        headers (dict): Request headers
        max_retries (int): Maximum number of retries
        debug (bool): If True, prints debug information
        
    Returns:
        requests.Response: The HTTP response
    """
    for attempt in range(max_retries):
        if debug:
            print(f"\n=== Request Attempt {attempt + 1}/{max_retries} ===")
            print(f"URL: {url}")
            print(f"Current cookies: {dict(session.cookies)}")
        
        try:
            # Add progressive delay between requests
            if attempt == 0:
                delay = 3  # First attempt: 3 seconds
            else:
                delay = 5 + (attempt * 3)  # Progressive delay: 8, 11, 14 seconds
            
            if debug:
                print(f"Waiting {delay} seconds before request...")
            time.sleep(delay)
            
            # Add some randomization to headers to appear more human-like
            current_headers = create_realistic_browser_headers(url, debug=debug)
            
            if debug:
                print("Request Headers:")
                for key, value in current_headers.items():
                    print(f"  {key}: {value}")
            
            response = session.get(url, headers=current_headers, timeout=25)
            
            if debug:
                print(f"Response Status: {response.status_code}")
            
            # Handle 202 responses properly
            if response.status_code == 202:
                if debug:
                    print("202 response received - following proper 202 flow")
                
                # Follow the proper 202 response flow
                follow_up_response = handle_202_response_flow(session, url, response, debug)
                
                # If follow-up was successful, return it
                if follow_up_response.status_code == 200:
                    if debug:
                        print("Follow-up request successful!")
                    return follow_up_response
                elif follow_up_response.status_code == 202:
                    if debug:
                        print("Follow-up also returned 202 - continuing retry loop")
                    # Continue to next attempt
                    continue
                else:
                    if debug:
                        print(f"Follow-up returned status {follow_up_response.status_code}")
                    return follow_up_response
            
            # Check if this is a WAF response that needs handling
            should_retry = handle_waf_response(response, session, debug)
            
            if not should_retry:
                if debug:
                    print("WAF/Captcha challenge detected. Stopping retries.")
                return response
            
            # If we get here, response looks normal
            if response.status_code == 200:
                if debug:
                    print("Successful response received")
                return response
            else:
                if debug:
                    print(f"Non-200 status code: {response.status_code}")
                
                # For 4xx/5xx errors, don't retry
                if response.status_code >= 400 and response.status_code != 202:
                    if debug:
                        print("Client/Server error - not retrying")
                    return response
                
        except requests.RequestException as e:
            if debug:
                print(f"Request error on attempt {attempt + 1}: {str(e)}")
            
            if attempt == max_retries - 1:
                raise e
    
    # If we get here, all retries failed
    raise Exception(f"All {max_retries} request attempts failed")

def handle_persistent_202(url: str, headers: dict, max_attempts: int = 3, debug: bool = True):
    """
    Handles persistent 202 responses by trying different strategies.
    
    Args:
        url (str): The URL to request
        headers (dict): Request headers
        max_attempts (int): Maximum number of attempts with different strategies
        debug (bool): If True, prints debug information
        
    Returns:
        requests.Response: The HTTP response or None if all attempts failed
    """
    if debug:
        print(f"\n=== Handling Persistent 202 Responses ===")
        print(f"URL: {url}")
    
    for attempt in range(max_attempts):
        if debug:
            print(f"\n--- Strategy {attempt + 1}/{max_attempts} ---")
        
        if attempt == 0:
            # Strategy 1: Clear all cookies and try fresh
            if debug:
                print("Strategy 1: Clearing all cookies and trying fresh session")
            session_manager.clear_cookies()
            session = session_manager.get_session()
            
            # Use realistic browser simulation
            response = simulate_browser_navigation(url, debug=debug)
            
        elif attempt == 1:
            # Strategy 2: Use different browser fingerprint
            if debug:
                print("Strategy 2: Using different browser fingerprint")
            session = session_manager.get_session()
            
            # Create headers with different browser characteristics
            modified_headers = create_realistic_browser_headers(url, debug=debug)
            # Force different Chrome version
            modified_headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            
            response = session.get(url, headers=modified_headers, timeout=30)
            
        else:
            # Strategy 3: Use Firefox simulation
            if debug:
                print("Strategy 3: Using Firefox simulation")
            session = session_manager.get_session()
            
            # Create Firefox-like headers
            firefox_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'DNT': '1',
                'Sec-GPC': '1',
                'Connection': 'keep-alive',
                #'Cookie': 'newstatisticUUID=1750629686_1426193254; _csrfToken=7kpnjFL4O5V5G9xTMNU8YjzWxokwpvpDXz5WUFD6; fu=1116195350; supportWebp=false; _ga_FZMMH98S83=GS2.1.s1750629687$o1$g1$t1750631423$j53$l0$h0; _ga=GA1.1.914561028.1750629687; _ga_PFYW0QLV3P=GS2.1.s1750629687$o1$g1$t1750631423$j53$l0$h0; traffic_utm_referer=; se_ref=; w_tsfp=ltvuV0MF2utBvS0Q7Krvl0qnEz8gdDw4h0wpEaR0f5thQLErU5mA0YB5v8LxM3TW5sxnvd7DsZoyJTLYCJI3dwMSTMjFIIgWjFiYw4kh2N0QU0QzGZrUD1ZLcb0nujZFfnhCNxS00jA8eIUd379yilkMsyN1zap3TO14fstJ019E6KDQmI5uDW3HlFWQRzaLbjcMcuqPr6g18L5a5Wne4QnyKlN0V7sTgkzH0y8cXyty6EC4d+BYN0mrdcetSqA=',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Priority': 'u=0, i',
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
            }
            
            response = session.get(url, headers=firefox_headers, timeout=30)
        
        if debug:
            print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            if debug:
                print("Success! Got 200 response")
            return response
        elif response.status_code == 202:
            if debug:
                print("Still getting 202 response, trying next strategy...")
            # Process cookies and continue to next strategy
            handle_waf_response(response, session, debug)
            continue
        else:
            if debug:
                print(f"Got status {response.status_code}, trying next strategy...")
            continue
    
    if debug:
        print("All strategies failed for persistent 202 responses")
    return None

def cleanup_duplicate_cookies(session, debug: bool = True):
    """
    Removes duplicate cookies from the session, keeping only the most recent one for each name.
    
    Args:
        session: The requests session
        debug (bool): If True, prints debug information
    """
    if debug:
        print("Cleaning up duplicate cookies...")
    
    # Get all cookies and group by name
    cookie_groups = {}
    for cookie in session.cookies:
        if cookie.name not in cookie_groups:
            cookie_groups[cookie.name] = []
        cookie_groups[cookie.name].append(cookie)
    
    # Remove duplicates, keeping only the most recent
    for cookie_name, cookies in cookie_groups.items():
        if len(cookies) > 1:
            if debug:
                print(f"Found {len(cookies)} cookies with name '{cookie_name}', keeping most recent")
            
            # Sort by creation time (if available) or keep the last one
            # For simplicity, we'll keep the last one added
            cookies_to_remove = cookies[:-1]  # All except the last one
            
            for cookie in cookies_to_remove:
                # Remove the cookie by setting it with an expired date
                session.cookies.set(
                    cookie.name, 
                    cookie.value, 
                    domain=cookie.domain,
                    path=cookie.path,
                    expires='Thu, 01 Jan 1970 00:00:00 GMT'  # Expire immediately
                )
                if debug:
                    print(f"  Removed duplicate cookie: {cookie.name}")

def create_realistic_browser_headers(url: str, referer: str = None, debug: bool = True) -> dict:
    """
    Creates realistic browser headers that mimic a real browser more convincingly.
    
    Args:
        url (str): The target URL
        referer (str, optional): The referer URL. If None, will use a search engine
        debug (bool): If True, prints debug information
        
    Returns:
        dict: Realistic browser headers
    """
    # Parse the target URL to get domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Set referer - browsers typically come from search engines or direct navigation
    if referer is None:
        referers = [
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://www.baidu.com/',
            'https://www.yahoo.com/',
            'https://duckduckgo.com/',
            'https://www.google.com/search?q=site:' + domain,
            'https://www.bing.com/search?q=site:' + domain
        ]
        referer = random.choice(referers)
    
    # Randomize viewport and screen dimensions
    viewport_widths = [1920, 1366, 1440, 1536, 1280, 1600, 1680]
    viewport_heights = [1080, 768, 900, 864, 720, 900, 1050]
    screen_widths = [1920, 1366, 1440, 1536, 1280, 1600, 1680, 2560]
    screen_heights = [1080, 768, 900, 864, 720, 900, 1050, 1440]
    
    viewport_width = random.choice(viewport_widths)
    viewport_height = random.choice(viewport_heights)
    screen_width = random.choice(screen_widths)
    screen_height = random.choice(screen_heights)
    
    # Randomize color depth and pixel ratio
    color_depth = random.choice([24, 32])
    pixel_ratio = random.choice([1, 1.25, 1.5, 2])
    
    # Randomize Accept-Language with realistic variations
    languages = [
        'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'en-US,en;q=0.9,zh;q=0.8,zh-CN;q=0.7',
        'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.6',
        'en-US,en;q=0.9,ja;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'en-US,en;q=0.9,ko;q=0.8,zh-CN;q=0.7,zh;q=0.6'
    ]
    
    # Randomize User-Agent with realistic Chrome versions
    chrome_versions = ['120.0.0.0', '119.0.0.0', '118.0.0.0', '117.0.0.0']
    chrome_version = random.choice(chrome_versions)
    
    # Create comprehensive headers
    headers = {
        'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': random.choice(languages),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site' if 'google.com' in referer or 'bing.com' in referer else 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-ch-ua-platform-version': '"15.0.0"',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-full-version': f'"{chrome_version}"',
        'sec-ch-ua-full-version-list': f'"Not_A Brand";v="8.0.0.0", "Chromium";v"{chrome_version}", "Google Chrome";v"{chrome_version}"',
        'sec-ch-ua-bitness': '"64"',
        'sec-ch-ua-wow64': '?0',
        'Referer': referer,
        'X-Requested-With': 'XMLHttpRequest',
        'Viewport-Width': str(viewport_width),
        'Sec-CH-UA-Viewport-Width': str(viewport_width),
        'Sec-CH-UA-Viewport-Height': str(viewport_height),
        'Sec-CH-UA-Screen-Width': str(screen_width),
        'Sec-CH-UA-Screen-Height': str(screen_height),
        'Sec-CH-UA-Color-Depth': str(color_depth),
        'Sec-CH-UA-Pixel-Ratio': str(pixel_ratio),
        'Sec-CH-UA-Memory': str(random.choice([4, 8, 16, 32])),
        'Sec-CH-UA-Cores': str(random.choice([4, 6, 8, 12, 16])),
        'Sec-CH-UA-Arch': '"x86"',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Model': '""',
        'Sec-CH-UA-Bitness': '"64"',
        'Sec-CH-UA-WoW64': '?0',
        'Sec-CH-UA-Full-Version': f'"{chrome_version}"',
        'Sec-CH-UA-Full-Version-List': f'"Not_A Brand";v="8.0.0.0", "Chromium";v"{chrome_version}", "Google Chrome";v"{chrome_version}"',
        'Sec-CH-UA-Platform-Version': '"15.0.0"',
        'Sec-CH-UA-Viewport-Width': str(viewport_width),
        'Sec-CH-UA-Viewport-Height': str(viewport_height),
        'Sec-CH-UA-Screen-Width': str(screen_width),
        'Sec-CH-UA-Screen-Height': str(screen_height),
        'Sec-CH-UA-Color-Depth': str(color_depth),
        'Sec-CH-UA-Pixel-Ratio': str(pixel_ratio),
        'Sec-CH-UA-Memory': str(random.choice([4, 8, 16, 32])),
        'Sec-CH-UA-Cores': str(random.choice([4, 6, 8, 12, 16])),
        'Sec-CH-UA-Arch': '"x86"',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Model': '""',
        'Sec-CH-UA-Bitness': '"64"',
        'Sec-CH-UA-WoW64': '?0',
        'Sec-CH-UA-Full-Version': f'"{chrome_version}"',
        'Sec-CH-UA-Full-Version-List': f'"Not_A Brand";v="8.0.0.0", "Chromium";v"{chrome_version}", "Google Chrome";v"{chrome_version}"',
        'Sec-CH-UA-Platform-Version': '"15.0.0"'
    }
    
    if debug:
        print(f"Created realistic browser headers:")
        print(f"  User-Agent: {headers['User-Agent']}")
        print(f"  Referer: {headers['Referer']}")
        print(f"  Viewport: {viewport_width}x{viewport_height}")
        print(f"  Screen: {screen_width}x{screen_height}")
        print(f"  Color Depth: {color_depth}")
        print(f"  Pixel Ratio: {pixel_ratio}")
    
    return headers

def simulate_browser_navigation(url: str, debug: bool = True):
    """
    Simulates realistic browser navigation patterns.
    
    Args:
        url (str): The target URL
        debug (bool): If True, prints debug information
        
    Returns:
        requests.Response: The HTTP response
    """
    if debug:
        print(f"\n=== Simulating Browser Navigation ===")
        print(f"Target URL: {url}")
    
    # Step 1: Visit a search engine first (like a real browser)
    search_engines = [
        'https://www.google.com/',
        'https://www.bing.com/',
        'https://www.baidu.com/'
    ]
    
    session = session_manager.get_session()
    
    # Step 1: Visit search engine
    search_url = random.choice(search_engines)
    if debug:
        print(f"Step 1: Visiting search engine: {search_url}")
    
    search_headers = create_realistic_browser_headers(search_url, debug=debug)
    try:
        search_response = session.get(search_url, headers=search_headers, timeout=15)
        if debug:
            print(f"Search engine response: {search_response.status_code}")
        time.sleep(random.uniform(1, 3))  # Realistic delay
    except:
        if debug:
            print("Search engine visit failed, continuing...")
    
    # Step 2: Visit the target URL with proper referer
    if debug:
        print(f"Step 2: Visiting target URL with referer: {search_url}")
    
    target_headers = create_realistic_browser_headers(url, referer=search_url, debug=debug)
    
    # Add some randomization to timing
    time.sleep(random.uniform(0.5, 2.0))
    
    response = session.get(url, headers=target_headers, timeout=25)
    
    if debug:
        print(f"Target response: {response.status_code}")
    
    return response

def create_firefox_headers(url: str, cookies: dict = None, debug: bool = True) -> dict:
    """
    Creates Firefox headers that match the working request pattern.
    Based on actual browser developer tools analysis.
    
    Args:
        url (str): The target URL
        cookies (dict, optional): Specific cookies to include
        debug (bool): If True, prints debug information
        
    Returns:
        dict: Firefox headers that match the working pattern
    """
    # Parse URL to get host
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    
    # Create Firefox headers that match the working pattern
    firefox_headers = {
        'Host': host,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=0, i',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
    
    # Add cookies if provided
    if cookies:
        cookie_string = '; '.join([f"{name}={value}" for name, value in cookies.items()])
        firefox_headers['Cookie'] = cookie_string
    
    if debug:
        print(f"Created Firefox headers for {host}")
        print("Firefox Headers:")
        for key, value in firefox_headers.items():
            print(f"  {key}: {value}")
    
    return firefox_headers

def fetch_with_firefox_headers(url: str, div_id: str = None, div_class: str = None, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches content using Firefox headers that match the working pattern.
    
    Args:
        url (str): The URL to fetch
        div_id (str, optional): The ID of the div to find
        div_class (str, optional): The class name of divs to find
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[Union[str, List[str]]]: The fetched content
    """
    if debug:
        print(f"\n=== Fetching with Firefox Headers ===")
        print(f"URL: {url}")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if div_id is None and div_class is None:
        raise ValueError("Either div_id or div_class must be provided")
    if div_id is not None and div_class is not None:
        raise ValueError("Only one of div_id or div_class should be provided")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Create Firefox headers
        firefox_headers = create_firefox_headers(url, debug=debug)
        
        if debug:
            print(f"Current cookies: {dict(session.cookies)}")
        
        # Make the request with Firefox headers
        response = session.get(url, headers=firefox_headers, timeout=30)
        
        if debug:
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Content Length: {len(response.text)}")
        
        # Check for success
        if response.status_code == 200:
            if debug:
                print("✅ Firefox headers request successful!")
        else:
            if debug:
                print(f"❌ Firefox headers request failed: {response.status_code}")
            return None
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        def process_div_content(div_element):
            """Helper function to process div content consistently"""
            if not div_element:
                return None
                
            # Replace <br> tags with newlines
            for br in div_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in div_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = div_element.get_text()
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            return content.strip()
        
        if div_id is not None:
            # Find div by ID (single div)
            target_div = soup.find('div', id=div_id)
            
            if debug:
                print(f"\nLooking for div with id: {div_id}")
                if target_div:
                    print("✅ Found target div!")
                else:
                    print("❌ Target div not found.")
            
            return process_div_content(target_div)
            
        else:
            # Find divs by class (multiple divs)
            target_divs = soup.find_all('div', class_=div_class)
            
            if debug:
                print(f"\nLooking for divs with class: {div_class}")
                print(f"Found {len(target_divs)} divs with class '{div_class}'")
            
            if not target_divs:
                return None
            
            # Process all found divs
            results = []
            for i, div in enumerate(target_divs):
                content = process_div_content(div)
                if content:
                    results.append(content)
                    if debug:
                        print(f"Processed div {i+1}: {len(content)} characters")
            
            return results if results else None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def fetch_with_confirmed_headers(url: str, main_id: str = None, main_class: str = None, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches content using the exact confirmed working headers.
    No header generation or modification - uses the exact headers that work.
    
    Args:
        url (str): The URL to fetch
        main_id (str, optional): The ID of the main element to find
        main_class (str, optional): The class name of main elements to find
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[Union[str, List[str]]]: The fetched content
    """
    if debug:
        print(f"\n=== Fetching with Confirmed Working Headers ===")
        print(f"URL: {url}")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if main_id is None and main_class is None:
        raise ValueError("Either main_id or main_class must be provided")
    if main_id is not None and main_class is not None:
        raise ValueError("Only one of main_id or main_class should be provided")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Use the global confirmed working headers
        if debug:
            print("Using confirmed working headers:")
            for key, value in CONFIRMED_HEADERS.items():
                print(f"  {key}: {value}")
        
        # Make the request with confirmed headers
        response = session.get(url, headers=CONFIRMED_HEADERS, timeout=30)
        
        if debug:
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Content Length: {len(response.text)}")
        
        # Check for success
        if response.status_code == 200:
            if debug:
                print("✅ Confirmed headers request successful!")
        else:
            if debug:
                print(f"❌ Confirmed headers request failed: {response.status_code}")
            return None
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        def process_main_content(main_element):
            """Helper function to process main content consistently"""
            if not main_element:
                if debug:
                    print("❌ Main element is None")
                return None
            
            if debug:
                print(f"🔍 Processing main element: {main_element.name} {main_element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(main_element))}")
            
            # Replace <br> tags with newlines
            for br in main_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in main_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = main_element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        if main_id is not None:
            # Find main by ID (single main)
            target_main = soup.find('main', id=main_id)
            
            if debug:
                print(f"\nLooking for main with id: {main_id}")
                if target_main:
                    print("✅ Found target main!")
                else:
                    print("❌ Target main not found.")
            
            return process_main_content(target_main)
            
        else:
            # Find mains by class (multiple mains)
            target_mains = soup.find_all('main', class_=main_class)
            
            if debug:
                print(f"\nLooking for main elements with class: {main_class}")
                print(f"Found {len(target_mains)} main elements with class '{main_class}'")
                
                # Show details of each found main element
                for i, main_elem in enumerate(target_mains):
                    print(f"Main {i+1}: {main_elem.name} {main_elem.attrs}")
                    print(f"  HTML length: {len(str(main_elem))}")
                    print(f"  Text content length: {len(main_elem.get_text())}")
                    print(f"  First 100 chars: {repr(main_elem.get_text()[:100])}")
            
            if not target_mains:
                return None
            
            # Process all found main elements
            results = []
            for i, main_elem in enumerate(target_mains):
                if debug:
                    print(f"\n--- Processing main {i+1} ---")
                content = process_main_content(main_elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed main {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ Main {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            return results if results else None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def update_confirmed_headers(new_headers: Dict[str, str]):
    """
    Update the global confirmed headers with new values.
    Useful for updating cookies or other headers when they expire.
    
    Args:
        new_headers (Dict[str, str]): New header values to update
    """
    global CONFIRMED_HEADERS
    CONFIRMED_HEADERS.update(new_headers)
    print(f"Updated confirmed headers with: {list(new_headers.keys())}")

def fetch_h1_with_confirmed_headers(url: str, h1_id: str = None, h1_class: str = None, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches h1 content using the exact confirmed working headers.
    Similar to fetch_with_confirmed_headers but targets h1 elements instead of main elements.
    
    Args:
        url (str): The URL to fetch
        h1_id (str, optional): The ID of the h1 element to find
        h1_class (str, optional): The class name of h1 elements to find
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[Union[str, List[str]]]: The fetched h1 content
    """
    if debug:
        print(f"\n=== Fetching H1 with Confirmed Working Headers ===")
        print(f"URL: {url}")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if h1_id is None and h1_class is None:
        raise ValueError("Either h1_id or h1_class must be provided")
    if h1_id is not None and h1_class is not None:
        raise ValueError("Only one of h1_id or h1_class should be provided")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Use the global confirmed working headers
        if debug:
            print("Using confirmed working headers:")
            for key, value in CONFIRMED_HEADERS.items():
                print(f"  {key}: {value}")
        
        # Make the request with confirmed headers
        response = session.get(url, headers=CONFIRMED_HEADERS, timeout=30)
        
        if debug:
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Content Length: {len(response.text)}")
        
        # Check for success
        if response.status_code == 200:
            if debug:
                print("✅ Confirmed headers request successful!")
        else:
            if debug:
                print(f"❌ Confirmed headers request failed: {response.status_code}")
            return None
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        def process_h1_content(h1_element):
            """Helper function to process h1 content consistently"""
            if not h1_element:
                if debug:
                    print("❌ H1 element is None")
                return None
            
            if debug:
                print(f"🔍 Processing h1 element: {h1_element.name} {h1_element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(h1_element))}")
            
            # Replace <br> tags with newlines
            for br in h1_element.find_all(['br']):
                br.replace_with('\n')
            
            # Get all text content
            content = h1_element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        if h1_id is not None:
            # Find h1 by ID (single h1)
            target_h1 = soup.find('h1', id=h1_id)
            
            if debug:
                print(f"\nLooking for h1 with id: {h1_id}")
                if target_h1:
                    print("✅ Found target h1!")
                else:
                    print("❌ Target h1 not found.")
                    # Show all h1 elements with IDs
                    all_h1s = soup.find_all('h1', id=True)
                    if all_h1s:
                        print("Available h1 IDs:")
                        for h1_elem in all_h1s:
                            print(f"  - {h1_elem.get('id')}")
            
            return process_h1_content(target_h1)
            
        else:
            # Find h1s by class (multiple h1s)
            target_h1s = soup.find_all('h1', class_=h1_class)
            
            if debug:
                print(f"\nLooking for h1 elements with class: {h1_class}")
                print(f"Found {len(target_h1s)} h1 elements with class '{h1_class}'")
                
                # Show details of each found h1 element
                for i, h1_elem in enumerate(target_h1s):
                    print(f"H1 {i+1}: {h1_elem.name} {h1_elem.attrs}")
                    print(f"  HTML length: {len(str(h1_elem))}")
                    print(f"  Text content length: {len(h1_elem.get_text())}")
                    print(f"  First 100 chars: {repr(h1_elem.get_text()[:100])}")
            
            if not target_h1s:
                return None
            
            # Process all found h1 elements
            results = []
            for i, h1_elem in enumerate(target_h1s):
                if debug:
                    print(f"\n--- Processing h1 {i+1} ---")
                content = process_h1_content(h1_elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed h1 {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ H1 {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            return results if results else None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

def make_request_with_connection_retry(session, url: str, headers: dict, max_retries: int = 5, debug: bool = True):
    """
    Makes an HTTP request with enhanced retry logic specifically for connection errors.
    Handles 'Connection aborted', 'RemoteDisconnected', and other connection-related issues.
    
    Args:
        session: The requests session
        url (str): The URL to request
        headers (dict): Request headers
        max_retries (int): Maximum number of retries
        debug (bool): If True, prints debug information
        
    Returns:
        requests.Response: The HTTP response
    """
    import socket
    from urllib3.exceptions import ProtocolError, MaxRetryError
    
    # Connection-specific error patterns
    connection_errors = [
        'Connection aborted',
        'RemoteDisconnected',
        'Connection reset by peer',
        'Broken pipe',
        'Connection refused',
        'Timeout',
        'Max retries exceeded',
        'ProtocolError'
    ]
    
    for attempt in range(max_retries):
        if debug:
            print(f"\n=== Connection Retry Attempt {attempt + 1}/{max_retries} ===")
            print(f"URL: {url}")
        
        try:
            # Progressive delay with exponential backoff for connection errors
            if attempt == 0:
                delay = 2  # First attempt: 2 seconds
            else:
                delay = min(30, 2 ** (attempt + 1))  # Exponential backoff: 4, 8, 16, 30, 30...
            
            if debug:
                print(f"Waiting {delay} seconds before request...")
            time.sleep(delay)
            
            # Create a fresh session for each attempt to avoid connection pooling issues
            if attempt > 0:
                if debug:
                    print("Creating fresh session to avoid connection pooling issues...")
                # Create a new session but preserve cookies
                old_cookies = dict(session.cookies)
                session.close()  # Close old session
                session = requests.Session()
                session.cookies = NoDuplicatesCookieJar()
                for name, value in old_cookies.items():
                    session.cookies.set(name, value)
            
            # Add connection-specific headers
            connection_headers = headers.copy()
            connection_headers.update({
                'Connection': 'close',  # Force new connection each time
                'Keep-Alive': 'timeout=5, max=1',  # Short keep-alive
            })
            
            if debug:
                print("Request Headers:")
                for key, value in connection_headers.items():
                    print(f"  {key}: {value}")
            
            # Use shorter timeout for connection attempts
            timeout = min(15 + (attempt * 5), 45)  # Progressive timeout: 15, 20, 25, 30, 35...
            
            if debug:
                print(f"Using timeout: {timeout} seconds")
            
            response = session.get(url, headers=connection_headers, timeout=timeout)
            
            if debug:
                print(f"Response Status: {response.status_code}")
            
            # If we get a successful response, return it
            if response.status_code == 200:
                if debug:
                    print("✅ Connection retry successful!")
                return response
            
            # Handle 202 responses (WAF challenges)
            if response.status_code == 202:
                if debug:
                    print("202 response received - following proper 202 flow")
                follow_up_response = handle_202_response_flow(session, url, response, debug)
                if follow_up_response.status_code == 200:
                    return follow_up_response
            
            # For other status codes, check if we should retry
            should_retry = handle_waf_response(response, session, debug)
            if not should_retry:
                return response
            
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
                socket.error,
                ProtocolError,
                MaxRetryError) as e:
            
            error_str = str(e).lower()
            is_connection_error = any(err.lower() in error_str for err in connection_errors)
            
            if debug:
                print(f"Connection error on attempt {attempt + 1}: {str(e)}")
                print(f"Is connection-specific error: {is_connection_error}")
            
            # If it's a connection-specific error, continue retrying
            if is_connection_error:
                if attempt == max_retries - 1:
                    if debug:
                        print("Max connection retries reached")
                    raise e
                continue
            else:
                # For non-connection errors, raise immediately
                raise e
                
        except requests.RequestException as e:
            if debug:
                print(f"Request error on attempt {attempt + 1}: {str(e)}")
            
            if attempt == max_retries - 1:
                raise e
    
    # If we get here, all retries failed
    raise Exception(f"All {max_retries} connection retry attempts failed")

def fetch_with_robust_connection(url: str, main_id: str = None, main_class: str = None, debug: bool = True) -> Optional[Union[str, List[str]]]:
    """
    Fetches content using robust connection handling with enhanced retry logic.
    Specifically designed to handle connection aborts and remote disconnections.
    
    Args:
        url (str): The URL to fetch
        main_id (str, optional): The ID of the main element to find
        main_class (str, optional): The class name of main elements to find
        debug (bool): If True, prints debug information
        
    Returns:
        Optional[Union[str, List[str]]]: The fetched content
    """
    if debug:
        print(f"\n=== Fetching with Robust Connection Handling ===")
        print(f"URL: {url}")
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            raise ValueError("Invalid URL format")
    except Exception as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Validate parameters
    if main_id is None and main_class is None:
        raise ValueError("Either main_id or main_class must be provided")
    if main_id is not None and main_class is not None:
        raise ValueError("Only one of main_id or main_class should be provided")

    try:
        # Get session with cookies
        session = session_manager.get_session()
        
        # Use the global confirmed working headers
        if debug:
            print("Using confirmed working headers with robust connection handling:")
            for key, value in CONFIRMED_HEADERS.items():
                print(f"  {key}: {value}")
        
        # Make the request with robust connection handling
        response = make_request_with_connection_retry(session, url, CONFIRMED_HEADERS, max_retries=5, debug=debug)
        
        if debug:
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Content Length: {len(response.text)}")
        
        # Check for success
        if response.status_code == 200:
            if debug:
                print("✅ Robust connection request successful!")
        else:
            if debug:
                print(f"❌ Robust connection request failed: {response.status_code}")
            return None
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        def process_main_content(main_element):
            """Helper function to process main content consistently"""
            if not main_element:
                if debug:
                    print("❌ Main element is None")
                return None
            
            if debug:
                print(f"🔍 Processing main element: {main_element.name} {main_element.attrs}")
                print(f"🔍 Raw HTML length: {len(str(main_element))}")
            
            # Replace <br> tags with newlines
            for br in main_element.find_all(['br']):
                br.replace_with('\n')
            
            # Replace <p> tags with double newlines
            for p in main_element.find_all(['p']):
                # Add newlines before and after paragraph content
                p.insert_before('\n')
                p.append('\n')
            
            # Get all text content
            content = main_element.get_text()
            
            if debug:
                print(f"🔍 Raw text content length: {len(content)}")
                print(f"🔍 Raw text content (first 200 chars): {repr(content[:200])}")
            
            # Clean up the text:
            # 1. Split into lines and strip each line
            # 2. Remove empty lines
            # 3. Join with single newlines
            lines = [line.strip() for line in content.splitlines()]
            
            if debug:
                print(f"🔍 Lines after stripping: {len(lines)}")
                print(f"🔍 First few lines: {lines[:5]}")
            
            # Remove empty lines while preserving intentional paragraph breaks
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line:  # If line is not empty
                    cleaned_lines.append(line)
                    prev_empty = False
                elif not prev_empty:  # If line is empty and previous line wasn't empty
                    cleaned_lines.append('')  # Add one empty line for paragraph break
                    prev_empty = True
            
            if debug:
                print(f"🔍 Cleaned lines: {len(cleaned_lines)}")
                print(f"🔍 First few cleaned lines: {cleaned_lines[:5]}")
            
            # Join lines with newlines
            content = '\n'.join(cleaned_lines)
            
            if debug:
                print(f"🔍 Content after joining: {len(content)} chars")
                print(f"🔍 Content (first 200 chars): {repr(content[:200])}")
            
            # Remove any leading/trailing whitespace while preserving internal formatting
            final_content = content.strip()
            
            if debug:
                print(f"🔍 Final content length: {len(final_content)}")
                if final_content:
                    print(f"🔍 Final content (first 200 chars): {repr(final_content[:200])}")
                else:
                    print("❌ Final content is empty after processing")
            
            return final_content
        
        if main_id is not None:
            # Find main by ID (single main)
            target_main = soup.find('main', id=main_id)
            
            if debug:
                print(f"\nLooking for main with id: {main_id}")
                if target_main:
                    print("✅ Found target main!")
                else:
                    print("❌ Target main not found.")
            
            return process_main_content(target_main)
            
        else:
            # Find mains by class (multiple mains)
            target_mains = soup.find_all('main', class_=main_class)
            
            if debug:
                print(f"\nLooking for main elements with class: {main_class}")
                print(f"Found {len(target_mains)} main elements with class '{main_class}'")
                
                # Show details of each found main element
                for i, main_elem in enumerate(target_mains):
                    print(f"Main {i+1}: {main_elem.name} {main_elem.attrs}")
                    print(f"  HTML length: {len(str(main_elem))}")
                    print(f"  Text content length: {len(main_elem.get_text())}")
                    print(f"  First 100 chars: {repr(main_elem.get_text()[:100])}")
            
            if not target_mains:
                return None
            
            # Process all found main elements
            results = []
            for i, main_elem in enumerate(target_mains):
                if debug:
                    print(f"\n--- Processing main {i+1} ---")
                content = process_main_content(main_elem)
                if content:
                    results.append(content)
                    if debug:
                        print(f"✅ Processed main {i+1}: {len(content)} characters")
                else:
                    if debug:
                        print(f"❌ Main {i+1} returned no content after processing")
            
            if debug:
                print(f"\nFinal results: {len(results)} non-empty contents")
            
            return results if results else None
        
    except requests.RequestException as e:
        raise requests.RequestException(f"Error fetching webpage: {str(e)}")
    except Exception as e:
        raise Exception(f"Error processing webpage: {str(e)}")

