"""
Image Downloader for Pinterest MCP.

Downloads and caches images from URLs for local display.
Works with any image URL, not just Pinterest.
"""

import asyncio
import hashlib
from pathlib import Path
from typing import Optional
import httpx


class ImageDownloader:
    """Downloads and caches images from URLs."""

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the image downloader.

        Args:
            cache_dir: Directory to cache downloaded images.
                      Defaults to project_root/.cache/images
        """
        if cache_dir is None:
            # Use project's cache directory
            project_root = Path(__file__).parent.parent
            cache_dir = project_root / ".cache" / "images"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"[Image Downloader] Cache directory: {self.cache_dir}")

    def _get_cache_path(self, url: str) -> Path:
        """
        Get the cache file path for a URL.

        Uses URL hash to create unique, safe filenames.
        """
        # Hash the URL to create a unique filename
        url_hash = hashlib.md5(url.encode()).hexdigest()

        # Try to extract file extension from URL
        ext = ".jpg"  # Default extension
        if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            ext = Path(url).suffix.lower()

        return self.cache_dir / f"{url_hash}{ext}"

    async def download_image(
        self,
        url: str,
        force_refresh: bool = False
    ) -> Optional[Path]:
        """
        Download an image from a URL and cache it locally.

        Args:
            url: Image URL to download
            force_refresh: If True, re-download even if cached

        Returns:
            Path to the downloaded image file, or None if download failed
        """
        cache_path = self._get_cache_path(url)

        # Return cached file if it exists and not forcing refresh
        if cache_path.exists() and not force_refresh:
            print(f"[Image Downloader] Cache hit: {cache_path.name}")
            return cache_path

        print(f"[Image Downloader] Downloading: {url}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                # Write image data to cache
                cache_path.write_bytes(response.content)

                print(f"[Image Downloader] Saved to: {cache_path.name}")
                return cache_path

        except Exception as e:
            print(f"[Image Downloader] Download failed: {e}")
            return None

    async def download_images(
        self,
        urls: list[str],
        force_refresh: bool = False
    ) -> list[Optional[Path]]:
        """
        Download multiple images concurrently.

        Args:
            urls: List of image URLs
            force_refresh: If True, re-download even if cached

        Returns:
            List of Paths (or None for failed downloads)
        """
        tasks = [
            self.download_image(url, force_refresh)
            for url in urls
        ]
        return await asyncio.gather(*tasks)

    def get_cached_path(self, url: str) -> Optional[Path]:
        """
        Get the cached path for a URL without downloading.

        Args:
            url: Image URL

        Returns:
            Path if cached, None otherwise
        """
        cache_path = self._get_cache_path(url)
        return cache_path if cache_path.exists() else None

    def clear_cache(self):
        """Delete all cached images."""
        count = 0
        for file in self.cache_dir.glob("*"):
            if file.is_file():
                file.unlink()
                count += 1

        print(f"[Image Downloader] Cleared {count} cached images")

    def get_cache_size(self) -> int:
        """Get total size of cached images in bytes."""
        total = 0
        for file in self.cache_dir.glob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total

    def get_cache_count(self) -> int:
        """Get number of cached images."""
        return len(list(self.cache_dir.glob("*")))


# Singleton instance
_downloader: Optional[ImageDownloader] = None


def get_downloader() -> ImageDownloader:
    """Get or create the global image downloader instance."""
    global _downloader
    if _downloader is None:
        _downloader = ImageDownloader()
    return _downloader


# Synchronous wrapper for convenience
def download_image_sync(url: str, force_refresh: bool = False) -> Optional[Path]:
    """
    Synchronous wrapper for downloading an image.

    Args:
        url: Image URL
        force_refresh: Force re-download

    Returns:
        Path to downloaded image or None
    """
    downloader = get_downloader()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(downloader.download_image(url, force_refresh))


def download_images_sync(urls: list[str], force_refresh: bool = False) -> list[Optional[Path]]:
    """
    Synchronous wrapper for downloading multiple images.

    Args:
        urls: List of image URLs
        force_refresh: Force re-download

    Returns:
        List of Paths (or None for failed downloads)
    """
    downloader = get_downloader()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(downloader.download_images(urls, force_refresh))
