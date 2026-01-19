"""
Image Viewer Utilities.

Provides multiple ways to display images:
1. PIL (Pillow) - Simple image viewer
2. Web browser - Opens image in default browser
3. System default app - Uses OS image viewer
"""

import webbrowser
from pathlib import Path
from typing import Optional, Union
import subprocess
import sys


def view_image_pil(image_path: Union[str, Path]):
    """
    View an image using PIL/Pillow.

    Args:
        image_path: Path to the image file

    Requires:
        pip install pillow
    """
    try:
        from PIL import Image

        img = Image.open(image_path)
        img.show()
        print(f"[Image Viewer] Opened with PIL: {Path(image_path).name}")

    except ImportError:
        print("[Image Viewer] PIL not installed. Run: pip install pillow")
    except Exception as e:
        print(f"[Image Viewer] Error opening image: {e}")


def view_image_browser(image_path: Union[str, Path]):
    """
    View an image in the default web browser.

    Args:
        image_path: Path to the image file
    """
    image_path = Path(image_path).absolute()

    if not image_path.exists():
        print(f"[Image Viewer] Image not found: {image_path}")
        return

    # Convert to file:// URL
    file_url = image_path.as_uri()

    try:
        webbrowser.open(file_url)
        print(f"[Image Viewer] Opened in browser: {image_path.name}")
    except Exception as e:
        print(f"[Image Viewer] Error opening browser: {e}")


def view_image_system(image_path: Union[str, Path]):
    """
    View an image using the system's default image viewer.

    Args:
        image_path: Path to the image file
    """
    image_path = Path(image_path).absolute()

    if not image_path.exists():
        print(f"[Image Viewer] Image not found: {image_path}")
        return

    try:
        if sys.platform == 'win32':
            # Windows
            subprocess.run(['start', '', str(image_path)], shell=True, check=True)
        elif sys.platform == 'darwin':
            # macOS
            subprocess.run(['open', str(image_path)], check=True)
        else:
            # Linux
            subprocess.run(['xdg-open', str(image_path)], check=True)

        print(f"[Image Viewer] Opened with system viewer: {image_path.name}")

    except Exception as e:
        print(f"[Image Viewer] Error opening with system viewer: {e}")


def view_image_auto(
    image_path: Union[str, Path],
    prefer: str = "system"
):
    """
    Automatically view an image using the best available method.

    Args:
        image_path: Path to the image file
        prefer: Preferred method ("system", "browser", or "pil")
    """
    methods = {
        "system": view_image_system,
        "browser": view_image_browser,
        "pil": view_image_pil,
    }

    method = methods.get(prefer, view_image_system)

    try:
        method(image_path)
    except Exception as e:
        print(f"[Image Viewer] Primary method failed: {e}")
        # Try fallback
        print("[Image Viewer] Trying fallback method...")
        try:
            view_image_browser(image_path)
        except:
            print("[Image Viewer] All methods failed")


def create_html_gallery(
    image_paths: list[Union[str, Path]],
    output_path: Optional[Path] = None,
    title: str = "Image Gallery"
) -> Path:
    """
    Create an HTML gallery from multiple images.

    Args:
        image_paths: List of image file paths
        output_path: Where to save the HTML file (default: temp location)
        title: Gallery title

    Returns:
        Path to the created HTML file
    """
    if output_path is None:
        from tempfile import NamedTemporaryFile
        output_path = Path(NamedTemporaryFile(suffix='.html', delete=False).name)

    # Convert all paths to absolute file:// URLs
    image_urls = [Path(p).absolute().as_uri() for p in image_paths]

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #2b2b2b;
            color: #e0e0e0;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            color: #4CAF50;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            padding: 20px;
        }}
        .gallery-item {{
            background: #3c3c3c;
            border-radius: 8px;
            padding: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        .gallery-item img {{
            width: 100%;
            height: 300px;
            object-fit: cover;
            border-radius: 4px;
        }}
        .gallery-item p {{
            margin: 10px 0 0 0;
            text-align: center;
            font-size: 12px;
            color: #888;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="gallery">
"""

    for i, url in enumerate(image_urls, 1):
        filename = Path(image_paths[i-1]).name
        html_content += f"""
        <div class="gallery-item">
            <img src="{url}" alt="{filename}">
            <p>{i}. {filename}</p>
        </div>
"""

    html_content += """
    </div>
</body>
</html>
"""

    output_path.write_text(html_content, encoding='utf-8')
    print(f"[Image Viewer] Created gallery: {output_path}")

    return output_path


def view_images_gallery(
    image_paths: list[Union[str, Path]],
    title: str = "Image Gallery",
    auto_open: bool = True
) -> Path:
    """
    Create and optionally open an HTML gallery of images.

    Args:
        image_paths: List of image file paths
        title: Gallery title
        auto_open: Automatically open in browser

    Returns:
        Path to the created HTML file
    """
    gallery_path = create_html_gallery(image_paths, title=title)

    if auto_open:
        view_image_browser(gallery_path)

    return gallery_path


# Example usage
if __name__ == "__main__":
    print("Image Viewer Utilities")
    print("=" * 60)
    print("\nAvailable functions:")
    print("  • view_image_pil(path) - Open with PIL/Pillow")
    print("  • view_image_browser(path) - Open in web browser")
    print("  • view_image_system(path) - Open with OS default viewer")
    print("  • view_image_auto(path) - Automatically choose best method")
    print("  • view_images_gallery(paths) - Create HTML gallery")
    print("\nExample:")
    print('  from services.image_viewer_utils import view_image_auto')
    print('  view_image_auto("image.jpg")')
