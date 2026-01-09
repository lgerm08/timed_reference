import httpx
from dataclasses import dataclass
from typing import Optional
import config


@dataclass
class Photo:
    id: int
    url: str
    photographer: str
    photographer_url: str
    alt: str
    src_medium: str
    src_large: str
    src_original: str


class PexelsClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.PEXELS_API_KEY
        self.base_url = config.PEXELS_BASE_URL
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers={"Authorization": self.api_key},
                timeout=30.0,
            )
        return self._client

    def search_photos(
        self,
        query: str,
        per_page: int = 10,
        page: int = 1,
    ) -> list[Photo]:
        """Search for photos on Pexels.

        Args:
            query: Search terms
            per_page: Number of results per page (max 80)
            page: Page number for pagination

        Returns:
            List of Photo objects
        """
        per_page = min(per_page, 80)

        response = self.client.get(
            f"{self.base_url}/search",
            params={
                "query": query,
                "per_page": per_page,
                "page": page,
            },
        )
        response.raise_for_status()
        data = response.json()

        photos = []
        for photo_data in data.get("photos", []):
            photos.append(
                Photo(
                    id=photo_data["id"],
                    url=photo_data["url"],
                    photographer=photo_data["photographer"],
                    photographer_url=photo_data["photographer_url"],
                    alt=photo_data.get("alt", ""),
                    src_medium=photo_data["src"]["medium"],
                    src_large=photo_data["src"]["large"],
                    src_original=photo_data["src"]["original"],
                )
            )

        return photos

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


pexels_client = PexelsClient()
