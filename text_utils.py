import re
import shutil
import string
from typing import List, Dict
from pathlib import Path

def split_by_chapter_markers(file_path: str, output_dir: str = None, debug: bool = False) -> Dict[int, str]:
    """
    Splits a text file into chapters based on Chinese chapter markers (第X).
    
    Args:
        file_path (str): Path to the input text file
        output_dir (str, optional): Directory to save individual chapter files. If None, only returns dict
        debug (bool): If True, prints debug information
        
    Returns:
        Dict[int, str]: Dictionary mapping chapter numbers to their content
    """
    try:
        if debug:
            print(f"\n=== Splitting Text by Chapter Markers ===")
            print(f"Input file: {file_path}")
            
        # Read the entire file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regular expression to match 第 followed by numbers
        # This will match both 第102 and 第56 style patterns
        pattern = r'第(\d+)'
        
        # Find all chapter markers with their positions
        markers = [(int(m.group(1)), m.start()) for m in re.finditer(pattern, content)]
        
        if debug:
            print(f"Found {len(markers)} chapter markers")
            print(f"Chapter numbers found: {[num for num, _ in markers]}")
            
        # Create dictionary to store chapters
        chapters = {}
        
        # Split content at each marker
        for i, (chapter_num, start_pos) in enumerate(markers):
            # Get the end position (either next marker or end of file)
            end_pos = markers[i + 1][1] if i < len(markers) - 1 else len(content)
            
            # Extract chapter content
            chapter_content = content[start_pos:end_pos].strip()
            chapters[chapter_num] = chapter_content
            
            if debug:
                print(f"Extracted chapter {chapter_num}: {len(chapter_content)} characters")
        
        # If output directory is specified, save individual chapter files
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            for chapter_num, content in chapters.items():
                chapter_file = output_path / f"chapter_{chapter_num}.txt"
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                if debug:
                    print(f"Saved chapter {chapter_num} to {chapter_file}")
        
        return chapters
        
    except Exception as e:
        if debug:
            print(f"Error splitting chapters: {str(e)}")
        raise e

def remove_chapter_headers(directory_path: str, debug: bool = False) -> List[str]:
    """
    Renames files by removing "Chapter X" from filenames in the given directory.
    
    Args:
        directory_path (str): Path to the directory containing text files
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were renamed (with their new names)
    """
    try:
        if debug:
            print(f"\n=== Removing Chapter Headers from Filenames ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        processed_files = []
        
        # Process each file
        for file_path in txt_files:
            if debug:
                print(f"\nProcessing: {file_path}")
            
            # Get the filename without extension
            stem = file_path.stem
            
            # Regular expression to match "Chapter" followed by numbers
            # This will match both "Chapter 28" and "Chapter 1009" patterns
            pattern = r'Chapter\s+(\d+)'
            
            # Try to find and remove "Chapter X" from filename
            match = re.search(pattern, stem)
            
            if match:
                # Create new filename using just the number
                new_name = re.sub(pattern, r'\1', stem) + file_path.suffix
                new_path = file_path.parent / new_name
                
                # Rename the file
                file_path.rename(new_path)
                processed_files.append(str(new_path))
                
                if debug:
                    print(f"Renamed: {file_path.name} -> {new_name}")
            else:
                if debug:
                    print("No chapter header found in filename")
        
        if debug:
            print(f"\nRenamed {len(processed_files)} files")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error renaming files: {str(e)}")
        raise e

def add_chapter_headers_from_filename(directory_path: str, debug: bool = False) -> List[str]:
    """
    Adds chapter headers based on filename and content format.
    Handles two filename formats:
    1. "NUMBER_title.txt" -> "Chapter NUMBER: title"
    2. "vXcY(Z)_title.txt" -> "Chapter Z: title"
    
    For both formats:
    - If content starts with ": text", formats as "Chapter X: text"
    - Otherwise, uses text after underscore as title: "Chapter X: title\n\ncontent"
    
    Examples:
        - For "101_journey.txt" with content ": begins here" -> "Chapter 101: begins here"
        - For "101_journey.txt" with content "begins here" -> "Chapter 101: journey\n\nbegins here"
        - For "v3c4(122)_The Popular Little Demon Lord.txt" with content ": begins here" -> "Chapter 122: begins here"
        - For "v3c4(122)_The Popular Little Demon Lord.txt" with content "begins here" -> 
          "Chapter 122: The Popular Little Demon Lord\n\nbegins here"
    
    Args:
        directory_path (str): Path to the directory containing files
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were modified
    """
    try:
        if debug:
            print(f"\n=== Adding Chapter Headers from Filenames ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        processed_files = []
        
        # Process each file
        for file_path in txt_files:
            if debug:
                print(f"\nProcessing: {file_path}")
            
            # Get the filename without extension
            stem = file_path.stem
            
            # Try to match both filename formats
            # First try volume-chapter format: vXcY(Z)_title
            vol_chapter_match = re.match(r'^v\d+c\d+\((\d+)\)_(.+)$', stem)
            # Then try simple number format: NUMBER_title
            simple_match = re.match(r'^(\d+)_(.+)$', stem)
            
            if vol_chapter_match or simple_match:
                # Extract chapter number and title based on which pattern matched
                if vol_chapter_match:
                    chapter_num = vol_chapter_match.group(1)
                    title_from_filename = vol_chapter_match.group(2)
                else:
                    chapter_num = simple_match.group(1)
                    title_from_filename = simple_match.group(2)
                
                # Read current content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Check if content starts with ":"
                if content.startswith(':'):
                    # Remove the leading ":" and any whitespace, then add chapter header
                    new_content = f"Chapter {chapter_num}{content}"
                else:
                    # Use filename text as title with two newlines before content
                    chapter_header = f"Chapter {chapter_num}: {title_from_filename}"
                    if not content.strip().startswith(chapter_header):
                        new_content = f"{chapter_header}\n\n{content}"
                    else:
                        if debug:
                            print(f"Header '{chapter_header}' already exists")
                        continue
                
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                processed_files.append(str(file_path))
                
                if debug:
                    print(f"Added header to file")
            else:
                if debug:
                    print("Filename doesn't match expected patterns")
        
        if debug:
            print(f"\nModified {len(processed_files)} files")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error adding chapter headers: {str(e)}")
        raise e

def remove_chapter_headers_from_content(directory_path: str, debug: bool = False) -> List[str]:
    """
    Removes chapter headers from the start of each file's content.
    Handles both formats:
    - "Chapter X: title\n\ncontent" -> "content"
    - "Chapter X: content" -> "content"
    
    Args:
        directory_path (str): Path to the directory containing files
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were modified
    """
    try:
        if debug:
            print(f"\n=== Removing Chapter Headers from Content ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        processed_files = []
        
        # Process each file
        for file_path in txt_files:
            if debug:
                print(f"\nProcessing: {file_path}")
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Regular expression to match both header formats:
            # 1. "Chapter X: title\n\ncontent"
            # 2. "Chapter X: content" (no newlines)
            pattern = r'^Chapter\s+\d+:.*?(?:\n\n|\n(?!\n)|\Z)'
            
            # Try to find and remove chapter header
            if re.match(pattern, content):
                # Remove the header and any following whitespace/newlines
                new_content = re.sub(pattern, '', content).strip()
                
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                processed_files.append(str(file_path))
                
                if debug:
                    print(f"Removed chapter header from file")
            else:
                if debug:
                    print("No chapter header found at start of file")
        
        if debug:
            print(f"\nModified {len(processed_files)} files")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error removing chapter headers: {str(e)}")
        raise e

vol_start = [1, 30, 119, 247, 391, 552, 697, 845, 990, 1250, 1386]

def add_volume_info(directory_path: str, debug: bool = False) -> List[str]:
    """
    Adds volume and chapter information to filenames based on vol_start array.
    Format: "vXcY(Z)_name.txt" where:
    - X is volume number
    - Y is chapter number within volume
    - Z is absolute chapter number
    
    Examples:
    - "0_start.txt" becomes "v0c0(0)_start.txt"
    - "1_Although.txt" becomes "v1c1(1)_Although.txt"
    - "30_Hello.txt" becomes "v2c1(30)_Hello.txt"
    
    Args:
        directory_path (str): Path to the directory containing files
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were renamed (with their new names)
    """
    try:
        if debug:
            print(f"\n=== Adding Volume Information to Filenames ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        processed_files = []
        
        # Process each file
        for file_path in txt_files:
            if debug:
                print(f"\nProcessing: {file_path}")
            
            # Get the filename
            original_name = file_path.name
            
            # Extract chapter number from start of filename
            match = re.match(r'^(\d+)_(.+\.txt)$', original_name)
            
            if match:
                chapter_num = int(match.group(1))
                rest_of_name = match.group(2)
                
                # Find volume number and chapter within volume
                volume = 0
                chapter_in_vol = chapter_num
                
                # Handle chapters before volume 1
                if chapter_num < vol_start[0]:
                    volume = 0
                    chapter_in_vol = chapter_num
                else:
                    # Find which volume this chapter belongs to
                    for i, start_chapter in enumerate(vol_start):
                        if chapter_num >= start_chapter:
                            volume = i + 1
                            # If it's not the last volume, check if we're before the next volume
                            if i + 1 < len(vol_start) and chapter_num >= vol_start[i + 1]:
                                continue
                            chapter_in_vol = chapter_num - start_chapter + 1
                            break
                
                # Create new filename
                new_name = f"v{volume}c{chapter_in_vol}({chapter_num})_{rest_of_name}"
                new_path = file_path.parent / new_name
                
                # Rename the file
                file_path.rename(new_path)
                processed_files.append(str(new_path))
                
                if debug:
                    print(f"Renamed: {original_name} -> {new_name}")
            else:
                if debug:
                    print("Filename doesn't match expected pattern (should start with number followed by underscore)")
        
        if debug:
            print(f"\nRenamed {len(processed_files)} files")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error renaming files: {str(e)}")
        raise e

def combine_by_volume(directory_paths: List[str], series_name: str, debug: bool = False) -> List[str]:
    """
    Combines files of the same volume from multiple directories into a single file named 
    "[series_name]v#(c#).txt", where the second # is the starting chapter of that volume.
    Expects filenames to be in format "vXcY(Z)_content.txt".
    Files are combined in order of their chapter numbers across all directories.
    
    Examples:
    - Volume 0: "[series_name]v0(c0).txt"
    - Volume 1: "[series_name]v1(c1).txt"
    - Volume 2: "[series_name]v2(c30).txt" (since chapter 30 starts volume 2)
    
    Args:
        directory_paths (List[str]): List of paths to directories containing files
        series_name (str): Name of the series to use in output filenames
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of created volume files
    """
    try:
        if debug:
            print(f"\n=== Combining Files by Volume ===")
            print(f"Input directories: {directory_paths}")
            print(f"Series name: {series_name}")
        
        # Dictionary to store files by volume
        volume_files = {}
        # Dictionary to store minimum chapter numbers for each volume
        volume_min_chapters = {}
        
        # Process each directory
        for directory_path in directory_paths:
            if debug:
                print(f"\nProcessing directory: {directory_path}")
            
            # Convert to Path object
            dir_path = Path(directory_path)
            
            # Get all .txt files in directory
            txt_files = list(dir_path.glob("*.txt"))
            
            if debug:
                print(f"Found {len(txt_files)} text files in {directory_path}")
            
            # Process each file
            for file_path in txt_files:
                # Extract volume and chapter numbers from filename
                match = re.match(r'^v(\d+)c\d+\((-?\d+)\)_(.+\.txt)$', file_path.name)
                
                if match:
                    volume = int(match.group(1))
                    abs_chapter = int(match.group(2))  # Can be negative for volume 0
                    
                    # Initialize list for this volume if not exists
                    if volume not in volume_files:
                        volume_files[volume] = []
                        volume_min_chapters[volume] = abs_chapter
                    else:
                        volume_min_chapters[volume] = min(volume_min_chapters[volume], abs_chapter)
                    
                    volume_files[volume].append(file_path)
                elif debug:
                    print(f"Skipping file with invalid format: {file_path.name}")
        
        # Create output directory in the first input directory
        output_dir = Path(directory_paths[0]) / "volumes"
        output_dir.mkdir(exist_ok=True)
        
        created_files = []
        
        # Process each volume
        for volume, files in sorted(volume_files.items()):
            if debug:
                print(f"\nProcessing volume {volume} ({len(files)} files)")
            
            # Sort files by chapter number (extracted from the parentheses)
            files.sort(key=lambda x: int(re.search(r'\((-?\d+)\)', x.name).group(1)))
            
            # Get the starting chapter number for this volume
            start_chapter = 0
            if volume == 0:
                # For volume 0, use the minimum chapter number found (can be negative)
                start_chapter = volume_min_chapters[0]
            elif volume <= len(vol_start):
                start_chapter = vol_start[volume - 1]
            
            # Create volume file with starting chapter number
            output_file = output_dir / f"{series_name}v{volume}(c{start_chapter}).txt"
            
            with open(output_file, 'w', encoding='utf-8') as outfile:
                # Process each file in order
                for i, file_path in enumerate(files):
                    if debug:
                        print(f"Adding: {file_path.name}")
                    
                    # Add file content with separator
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read().strip()
                        
                        # Add newlines between chapters
                        if i > 0:
                            outfile.write('\n\n\f')
                        
                        outfile.write(content)
            
            created_files.append(str(output_file))
            
            if debug:
                print(f"Created: {output_file}")
        
        if debug:
            print(f"\nCreated {len(created_files)} volume files")
        
        return created_files
        
    except Exception as e:
        if debug:
            print(f"Error combining files: {str(e)}")
        raise e

def replace_em_dashes_with_hyphens(directory_path: str, debug: bool = False) -> List[str]:
    """
    Replaces all instances of em dashes ('—') with regular hyphens ('-') in all txt files
    in the specified directory.
    
    Args:
        directory_path (str): Path to the directory containing text files
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were modified
    """
    try:
        if debug:
            print(f"\n=== Replacing Em Dashes with Hyphens ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        processed_files = []
        
        # Process each file
        for file_path in txt_files:
            if debug:
                print(f"\nProcessing: {file_path}")
            
            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count original em dashes
            original_count = content.count('—')
            
            if original_count > 0:
                # Replace em dashes with hyphens
                new_content = content.replace('—', '-')
                
                # Write back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                processed_files.append(str(file_path))
                
                if debug:
                    print(f"Replaced {original_count} em dashes in file")
            else:
                if debug:
                    print("No em dashes found in file")
        
        if debug:
            print(f"\nModified {len(processed_files)} files")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error replacing em dashes: {str(e)}")
        raise e

def clear_directory_contents(directory_path: str, debug: bool = False) -> List[str]:
    """
    Deletes all contents of a directory (files and subdirectories) while keeping the directory itself.
    
    Args:
        directory_path (str): Path to the directory to clear
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of items that were deleted (files and directories)
    """
    try:
        if debug:
            print(f"\n=== Clearing Directory Contents ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Check if directory exists
        if not dir_path.exists():
            if debug:
                print(f"Directory does not exist: {directory_path}")
            return []
        
        if not dir_path.is_dir():
            if debug:
                print(f"Path is not a directory: {directory_path}")
            return []
        
        deleted_items = []
        
        # Get all items in the directory
        items = list(dir_path.iterdir())
        
        if debug:
            print(f"Found {len(items)} items in directory")
        
        # Process each item
        for item in items:
            if debug:
                print(f"Deleting: {item}")
            
            try:
                if item.is_file():
                    # Delete file
                    item.unlink()
                    deleted_items.append(str(item))
                elif item.is_dir():
                    # Delete directory and all its contents
                    shutil.rmtree(item)
                    deleted_items.append(str(item))
                else:
                    # Handle other types (symlinks, etc.)
                    if item.is_symlink():
                        item.unlink()
                    else:
                        # For other special files, try to remove
                        item.unlink(missing_ok=True)
                    deleted_items.append(str(item))
                    
            except Exception as e:
                if debug:
                    print(f"Error deleting {item}: {str(e)}")
                # Continue with other items even if one fails
        
        if debug:
            print(f"\nSuccessfully deleted {len(deleted_items)} items")
            print(f"Directory '{directory_path}' is now empty")
        
        return deleted_items
        
    except Exception as e:
        if debug:
            print(f"Error clearing directory: {str(e)}")
        raise e

def normalize_text(text: str, debug: bool = False) -> str:
    """
    Removes punctuation (commas, apostrophes, etc.) and converts all uppercase characters to lowercase.
    
    Args:
        text (str): The text string to normalize
        debug (bool): If True, prints debug information
        
    Returns:
        str: The normalized text string
    """
    try:
        if debug:
            print(f"\n=== Normalizing Text (Removing Punctuation & Converting to Lowercase) ===")
            print(f"Original text length: {len(text)} characters")
        
        # Count original uppercase letters and punctuation
        original_uppercase = sum(1 for char in text if char.isupper())
        original_punctuation = sum(1 for char in text if char in string.punctuation)
        
        if debug:
            print(f"Found {original_uppercase} uppercase letters")
            print(f"Found {original_punctuation} punctuation marks")
        
        # Convert to lowercase and remove punctuation
        # Keep spaces and newlines, remove all other punctuation
        normalized_text = text.lower()
        # Remove punctuation but preserve spaces and newlines
        normalized_text = ''.join(char for char in normalized_text if char not in string.punctuation or char in ' \n\t')
        
        if debug:
            print(f"Normalized text length: {len(normalized_text)} characters")
            print(f"Sample of normalized text: {normalized_text[:100]}...")
        
        return normalized_text
        
    except Exception as e:
        if debug:
            print(f"Error normalizing text: {str(e)}")
        raise e

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

def replace_multiple_strings(text: str, strings_to_replace: List[str], replacement: str, debug: bool = False) -> str:
    """
    Replaces all instances of multiple strings from a list with a replacement string that includes the original text.
    Format: "[replacement][original: original_text]"
    
    Args:
        text (str): The text string to process
        strings_to_replace (List[str]): List of strings to find and replace
        replacement (str): The string to replace all found strings with
        debug (bool): If True, prints debug information
        
    Returns:
        str: The text string with all specified strings replaced in format "[replacement][original: original_text]"
    """
    try:
        if debug:
            print(f"\n=== Replacing Multiple Strings ===")
            print(f"Original text length: {len(text)} characters")
            print(f"Number of strings to replace: {len(strings_to_replace)}")
            print(f"Replacement string: '{replacement}'")
        
        result = text
        total_replacements = 0
        
        # Apply replacement for each string in the list
        for find_str in strings_to_replace:
            if find_str in result:
                count = result.count(find_str)
                # Format: [replacement][original: original_text]
                formatted_replacement = f"[{replacement}][original: {find_str}]"
                result = result.replace(find_str, formatted_replacement)
                total_replacements += count
                
                if debug:
                    print(f"Replaced '{find_str}' with '{formatted_replacement}' ({count} occurrences)")
        
        if debug:
            print(f"Total replacements made: {total_replacements}")
            print(f"Final text length: {len(result)} characters")
            if total_replacements > 0:
                print(f"Sample of result: {result[:100]}...")
        
        return result
        
    except Exception as e:
        if debug:
            print(f"Error replacing multiple strings: {str(e)}")
        raise e

def ensure_directory_exists(directory_path: str, debug: bool = False) -> bool:
    """
    Creates a directory if it doesn't exist.
    
    Args:
        directory_path (str): Path to the directory to create
        debug (bool): If True, prints debug information
        
    Returns:
        bool: True if directory exists or was created successfully, False otherwise
    """
    try:
        if debug:
            print(f"\n=== Ensuring Directory Exists ===")
            print(f"Directory path: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Check if directory already exists
        if dir_path.exists():
            if dir_path.is_dir():
                if debug:
                    print(f"Directory already exists: {directory_path}")
                return True
            else:
                if debug:
                    print(f"Path exists but is not a directory: {directory_path}")
                return False
        
        # Create directory and all parent directories
        dir_path.mkdir(parents=True, exist_ok=True)
        
        if debug:
            print(f"Successfully created directory: {directory_path}")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"Error creating directory: {str(e)}")
        return False

def replace_with_dictionary_in_directory(directory_path: str, replacement_dict: Dict[str, str], 
                                        confident: bool = False, backup: bool = True, 
                                        debug: bool = False) -> List[str]:
    """
    Applies replace_with_dictionary to all .txt files in a directory.
    
    Args:
        directory_path (str): Path to the directory containing .txt files
        replacement_dict (Dict[str, str]): Dictionary where keys are substrings to find and values are replacements
        confident (bool): If True, replaces without adding [?] markers
        backup (bool): If True, creates backup files with .bak extension before processing
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were processed successfully
    """
    try:
        if debug:
            print(f"\n=== Applying Dictionary Replacements to Directory ===")
            print(f"Directory: {directory_path}")
            print(f"Number of replacement rules: {len(replacement_dict)}")
            print(f"Confident mode: {confident}")
            print(f"Backup files: {backup}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Check if directory exists
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        processed_files = []
        total_replacements = 0
        
        # Process each file
        for file_path in txt_files:
            if debug:
                print(f"\nProcessing: {file_path.name}")
            
            try:
                # Create backup if requested
                if backup:
                    backup_path = file_path.with_suffix('.txt.bak')
                    if not backup_path.exists():  # Only create backup if it doesn't exist
                        shutil.copy2(file_path, backup_path)
                        if debug:
                            print(f"  Created backup: {backup_path.name}")
                
                # Read the file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_length = len(content)
                
                # Apply replacements
                modified_content = replace_with_dictionary(
                    content, 
                    replacement_dict, 
                    confident=confident, 
                    debug=False  # Don't debug individual file processing unless requested
                )
                
                # Count replacements made
                file_replacements = 0
                for find_str, replace_str in replacement_dict.items():
                    file_replacements += content.count(find_str)
                
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                processed_files.append(str(file_path))
                total_replacements += file_replacements
                
                if debug:
                    print(f"  Original length: {original_length} chars")
                    print(f"  Final length: {len(modified_content)} chars")
                    print(f"  Replacements made: {file_replacements}")
                    if file_replacements > 0:
                        print(f"  ✅ File processed successfully")
                    else:
                        print(f"  ⚠️  No replacements found in this file")
                
            except Exception as e:
                if debug:
                    print(f"  ❌ Error processing {file_path.name}: {str(e)}")
                # Continue with other files even if one fails
        
        if debug:
            print(f"\n=== Processing Complete ===")
            print(f"Successfully processed: {len(processed_files)} files")
            print(f"Total replacements made: {total_replacements}")
            if backup:
                print(f"Backup files created with .bak extension")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error processing directory: {str(e)}")
        raise e

def replace_with_dictionary_in_files(file_paths: List[str], replacement_dict: Dict[str, str], 
                                   confident: bool = False, backup: bool = True, 
                                   debug: bool = False) -> List[str]:
    """
    Applies replace_with_dictionary to a specific list of files.
    
    Args:
        file_paths (List[str]): List of file paths to process
        replacement_dict (Dict[str, str]): Dictionary where keys are substrings to find and values are replacements
        confident (bool): If True, replaces without adding [?] markers
        backup (bool): If True, creates backup files with .bak extension before processing
        debug (bool): If True, prints debug information
        
    Returns:
        List[str]: List of files that were processed successfully
    """
    try:
        if debug:
            print(f"\n=== Applying Dictionary Replacements to Files ===")
            print(f"Number of files to process: {len(file_paths)}")
            print(f"Number of replacement rules: {len(replacement_dict)}")
            print(f"Confident mode: {confident}")
            print(f"Backup files: {backup}")
        
        processed_files = []
        total_replacements = 0
        
        # Process each file
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            
            if debug:
                print(f"\nProcessing: {file_path.name}")
            
            # Check if file exists
            if not file_path.exists():
                if debug:
                    print(f"  ❌ File not found: {file_path}")
                continue
            
            if not file_path.is_file():
                if debug:
                    print(f"  ❌ Path is not a file: {file_path}")
                continue
            
            try:
                # Create backup if requested
                if backup:
                    backup_path = file_path.with_suffix('.txt.bak')
                    if not backup_path.exists():  # Only create backup if it doesn't exist
                        shutil.copy2(file_path, backup_path)
                        if debug:
                            print(f"  Created backup: {backup_path.name}")
                
                # Read the file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_length = len(content)
                
                # Apply replacements
                modified_content = replace_with_dictionary(
                    content, 
                    replacement_dict, 
                    confident=confident, 
                    debug=False  # Don't debug individual file processing unless requested
                )
                
                # Count replacements made
                file_replacements = 0
                for find_str, replace_str in replacement_dict.items():
                    file_replacements += content.count(find_str)
                
                # Write the modified content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                processed_files.append(str(file_path))
                total_replacements += file_replacements
                
                if debug:
                    print(f"  Original length: {original_length} chars")
                    print(f"  Final length: {len(modified_content)} chars")
                    print(f"  Replacements made: {file_replacements}")
                    if file_replacements > 0:
                        print(f"  ✅ File processed successfully")
                    else:
                        print(f"  ⚠️  No replacements found in this file")
                
            except Exception as e:
                if debug:
                    print(f"  ❌ Error processing {file_path.name}: {str(e)}")
                # Continue with other files even if one fails
        
        if debug:
            print(f"\n=== Processing Complete ===")
            print(f"Successfully processed: {len(processed_files)} files")
            print(f"Total replacements made: {total_replacements}")
            if backup:
                print(f"Backup files created with .bak extension")
        
        return processed_files
        
    except Exception as e:
        if debug:
            print(f"Error processing files: {str(e)}")
        raise e

def get_last_chapter_number(directory_path: str, debug: bool = False) -> int:
    """
    Scans a directory for files with format "v[x]c[y]([z])_[name].txt" and returns the highest "z" number.
    
    Args:
        directory_path (str): Path to the directory to scan
        debug (bool): If True, prints debug information
        
    Returns:
        int: The highest chapter number found, or -1 if no matching files found
        
    Examples:
        - "v1c140(140)_PLUS The Mirror World.txt" -> extracts 140
        - "v1c139(139)_PLUS Mom.txt" -> extracts 139
        - "v0c0(0)_Free #0. The SilverHaired Beautiful Girl Became an SClass Hunter.txt" -> extracts 0
    """
    try:
        if debug:
            print(f"\n=== Getting Last Chapter Number ===")
            print(f"Directory: {directory_path}")
        
        # Convert to Path object
        dir_path = Path(directory_path)
        
        # Check if directory exists
        if not dir_path.exists():
            if debug:
                print(f"Directory does not exist: {directory_path}")
            return -1
        
        if not dir_path.is_dir():
            if debug:
                print(f"Path is not a directory: {directory_path}")
            return -1
        
        # Get all .txt files in directory
        txt_files = list(dir_path.glob("*.txt"))
        
        if debug:
            print(f"Found {len(txt_files)} text files")
        
        max_chapter = -1
        matching_files = []
        
        # Process each file
        for file_path in txt_files:
            filename = file_path.name
            
            # Regular expression to match "v[x]c[y]([z])_[name].txt" format
            # This matches: v1c140(140)_PLUS The Mirror World.txt, v0c0(0)_title.txt, etc.
            # The [name] part can be any text after the underscore
            pattern = r'^v\d+c\d+\((-?\d+)\)_.*\.txt$'
            match = re.match(pattern, filename)
            
            if match:
                chapter_num = int(match.group(1))
                matching_files.append((filename, chapter_num))
                
                if chapter_num > max_chapter:
                    max_chapter = chapter_num
                
                if debug:
                    print(f"Found matching file: {filename} (chapter {chapter_num})")
            elif debug:
                print(f"Skipping non-matching file: {filename}")
        
        if debug:
            print(f"\nFound {len(matching_files)} files with matching format")
            if matching_files:
                print(f"Chapter numbers found: {[num for _, num in matching_files]}")
                print(f"Highest chapter number: {max_chapter}")
            else:
                print("No files with matching format found")
        
        return max_chapter
        
    except Exception as e:
        if debug:
            print(f"Error getting last chapter number: {str(e)}")
        raise e

if __name__ == "__main__":
    # Example usage
    try:
        #directory = "Loner Outcast Vampire/translated"
        # Split chapters example
        #input_file = "sample.txt"
        #output_dir = "chapters"
        
        #chapters = split_by_chapter_markers(input_file, output_dir, debug=True)
        #print(f"\nSuccessfully split into {len(chapters)} chapters")
        
        # Remove chapter headers example
        #processed_files = remove_chapter_headers("txtChapters", debug=True)
        #print(f"\nSuccessfully processed {len(processed_files)} files")
        
        directory = "I Became a Member of My Favorite Group/translated"
        
        # Add volume information example
        #processed_files = add_volume_info("txtChapters", debug=True)
        #print(f"\nSuccessfully processed {len(processed_files)} files")

        # Add chapter headers from filenames example
        processed_files = add_chapter_headers_from_filename(directory, debug=True)
        print(f"\nSuccessfully processed {len(processed_files)} files")
        
        replace_em_dashes_with_hyphens(directory, debug=True)      

        # Combine files by volume example
        processed_files = combine_by_volume([directory], "I Became a Member of My Favorite Group", debug=True)
        print(f"\nSuccessfully created {len(processed_files)} volume files")
        
        # Remove chapter headers from content example
        processed_files = remove_chapter_headers_from_content(directory, debug=True)
        print(f"\nSuccessfully processed {len(processed_files)} files")

        
    except Exception as e:
        print(f"Error: {str(e)}") 