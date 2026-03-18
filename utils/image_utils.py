import os
from typing import List

import requests
from PIL import Image, ImageEnhance


def upload_to_uguu(file_path: str, debug: bool = True) -> str:
    """
    Uploads a file to uguu.se and returns the download URL.
    Files are kept for 24 hours.
    """
    try:
        if debug:
            print(f"\n=== Uploading to uguu.se ===")
            print(f"File path: {file_path}")

        filename = os.path.basename(file_path)

        files = {
            "files[]": (filename, open(file_path, "rb"), "image/jpeg")
        }
        response = requests.post("https://uguu.se/upload.php", files=files)
        response.raise_for_status()

        if debug:
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")

        data = response.json()

        if debug:
            print(f"Parsed JSON response: {data}")

        if data.get("success") and data.get("files"):
            url = data["files"][0]["url"].replace("\\/", "/")
            if debug:
                print(f"Extracted URL: {url}")
            if url.startswith("https://") and ".uguu.se/" in url:
                return url

        raise Exception(f"Invalid response format from uguu.se: {data}")

    except Exception as e:
        if debug:
            print(f"Error uploading to uguu.se: {str(e)}")
        raise e


def adjust_image(
    image_path: str,
    brightness_factor: float = 1.0,
    contrast_factor: float = 1.0,
    output_path: str = None,
    debug: bool = True,
) -> str:
    """
    Converts image to grayscale and adjusts the brightness and contrast using Pillow.
    """
    try:
        if debug:
            print(f"\n=== Adjusting Image ===")
            print(f"Input path: {image_path}")
            print(f"Brightness factor: {brightness_factor}")
            print(f"Contrast factor: {contrast_factor}")

        img = Image.open(image_path)
        img = img.convert("L")

        if debug:
            print("Converted to grayscale")

        if brightness_factor != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness_factor)
            if debug:
                print(f"Adjusted brightness by factor {brightness_factor}")

        if contrast_factor != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast_factor)
            if debug:
                print(f"Adjusted contrast by factor {contrast_factor}")

        if output_path is None:
            filename, ext = os.path.splitext(image_path)
            output_path = f"{filename}_gray_adjusted{ext}"

        img.save(output_path, quality=95)

        if debug:
            print(f"Adjusted grayscale image saved to: {output_path}")

        return output_path

    except Exception as e:
        if debug:
            print(f"Error adjusting image: {str(e)}")
        raise e


def find_white_lines(img, threshold: int = 250, min_line_width: int = 100, debug: bool = True) -> List[int]:
    """
    Find horizontal white lines in a grayscale image.
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


def split_image_at_whitespace(
    image_path: str,
    min_height: int = 100,
    max_height: int = 800,
    threshold: int = 250,
    min_line_width: int = 70,
    output_dir: str = None,
    debug: bool = True,
) -> list:
    """
    Splits an image at horizontal white lines, ensuring each part is within size constraints.
    """
    try:
        if debug:
            print(f"\n=== Splitting Image at White Lines ===")
            print(f"Input path: {image_path}")

        image_path = os.path.abspath(image_path)

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image not found: {image_path}")

        img = Image.open(image_path).convert("L")
        width, height = img.size

        if debug:
            print(f"Image dimensions: {width}x{height}")

        white_lines = find_white_lines(img, threshold, min_line_width, debug)

        if output_dir is None:
            output_dir = os.path.dirname(image_path)
            if not output_dir:
                output_dir = os.getcwd()

        output_dir = os.path.abspath(output_dir)

        if debug:
            print(f"Output directory: {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(image_path))[0]

        split_files: List[str] = []
        current_y = 0
        part_num = 1

        for next_y in white_lines + [height]:
            section_height = next_y - current_y

            if section_height < min_height:
                continue

            if section_height > max_height:
                splits = range(current_y, next_y, max_height)
                for split_start in splits:
                    split_end = min(split_start + max_height, next_y)

                    cropped = img.crop((0, split_start, width, split_end))
                    output_path = os.path.join(output_dir, f"{base_name}_part{part_num}.png")
                    cropped.save(output_path, quality=95)
                    split_files.append(output_path)

                    if debug:
                        print(f"Saved part {part_num} ({split_end - split_start}px) to: {output_path}")

                    part_num += 1
            else:
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


def analyze_image(
    image_path: str,
    prompt: str = "What text do you see in this image?",
    brightness: float = None,
    contrast: float = None,
    split: bool = False,
    min_height: int = 30,
    max_height: int = 800,
    debug: bool = True,
) -> str:
    """
    Proxy wrapper, real implementation remains in web_scraper for now.
    This is added only to keep backward compatibility if imported elsewhere.
    """
    from web_scraper import analyze_image as _analyze_image  # type: ignore

    return _analyze_image(
        image_path=image_path,
        prompt=prompt,
        brightness=brightness,
        contrast=contrast,
        split=split,
        min_height=min_height,
        max_height=max_height,
        debug=debug,
    )

