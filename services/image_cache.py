import os
import hashlib
import httpx
from pathlib import Path
from typing import Optional
import config


class ImageCache:
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or config.CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=60.0)
        return self._client

    def _get_cache_path(self, url: str) -> Path:
        """Generate a cache file path based on URL hash."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        extension = url.split(".")[-1].split("?")[0]
        if extension not in ("jpg", "jpeg", "png", "webp", "gif"):
            extension = "jpg"
        return self.cache_dir / f"{url_hash}.{extension}"

    def get_cached_path(self, url: str) -> Optional[Path]:
        """Return cached file path if exists, None otherwise."""
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            return cache_path
        return None

    def download(self, url: str) -> Path:
        """Download image and return local path. Uses cache if available."""
        cache_path = self._get_cache_path(url)

        if cache_path.exists():
            return cache_path

        response = self.client.get(url)
        response.raise_for_status()

        with open(cache_path, "wb") as f:
            f.write(response.content)

        return cache_path

    def download_all(self, urls: list[str]) -> list[Path]:
        """Download multiple images and return their local paths."""
        paths = []
        for url in urls:
            try:
                path = self.download(url)
                paths.append(path)
            except Exception as e:
                print(f"Failed to download {url}: {e}")
        return paths

    def clear_cache(self):
        """Remove all cached images."""
        for file in self.cache_dir.iterdir():
            if file.is_file():
                file.unlink()

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


image_cache = ImageCache()
