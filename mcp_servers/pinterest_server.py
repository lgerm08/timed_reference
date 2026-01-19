#!/usr/bin/env python3
"""
Pinterest MCP Server

A Model Context Protocol server that exposes Pinterest image search functionality.
Educational implementation for learning MCP integration with AI agents.

This server provides tools for:
- Searching Pinterest for reference images
- Filtering results by artistic criteria
- Getting diverse image results for practice sessions

Usage:
    python pinterest_server.py  # Runs as stdio MCP server
"""

import asyncio
import json
import sys
import os
from typing import Any, Optional
from pathlib import Path
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure .env is loaded from the correct location (timed_reference directory)
# IMPORTANT: Load BEFORE importing config to ensure env vars are available
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)  # Override any existing env vars
    print(f"[Pinterest MCP] Loaded .env from: {env_path}", file=sys.stderr)
else:
    print(f"[Pinterest MCP] Warning: .env not found at {env_path}", file=sys.stderr)

# Now import config (it will use the loaded env vars)
import config
# Force reload config values from env in case they were cached
import importlib
importlib.reload(config)

# Debug: Print credential status (not the actual values!)
print(f"[Pinterest MCP] PINTEREST_EMAIL configured: {bool(config.PINTEREST_EMAIL)}", file=sys.stderr)
print(f"[Pinterest MCP] PINTEREST_PASSWORD configured: {bool(config.PINTEREST_PASSWORD)}", file=sys.stderr)


# Pinterest unofficial API endpoints (for educational purposes)
# Note: Pinterest's official API requires business account approval
# This uses public search that doesn't require authentication

class PinterestSearcher:
    """Handles Pinterest image searching through py3-pinterest."""

    # Modern User-Agent to avoid Pinterest blocking old browser identifiers
    MODERN_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self):
        self.pinterest = None
        self._login_attempted = False
        self.use_real_pinterest = bool(config.PINTEREST_EMAIL and config.PINTEREST_PASSWORD)

        if self.use_real_pinterest:
            print("[Pinterest MCP] Using REAL Pinterest (py3-pinterest)", file=sys.stderr)
            print(f"[Pinterest MCP] Email: {config.PINTEREST_EMAIL[:3]}...{config.PINTEREST_EMAIL[-10:]}", file=sys.stderr)
        else:
            print("[Pinterest MCP] Pinterest credentials NOT configured", file=sys.stderr)
            print("[Pinterest MCP] Will use PEXELS API as fallback for image search", file=sys.stderr)
            print("[Pinterest MCP] Set PINTEREST_EMAIL and PINTEREST_PASSWORD in .env for Pinterest", file=sys.stderr)

    def _get_pinterest_client(self):
        """Get or create Pinterest client (lazy initialization with login)."""
        if self.pinterest is None and self.use_real_pinterest and not self._login_attempted:
            self._login_attempted = True  # Prevent repeated login attempts on failure
            try:
                from py3pin.Pinterest import Pinterest

                # Create credentials directory if it doesn't exist
                cred_root = Path(__file__).parent / 'cred_root'
                cred_root.mkdir(exist_ok=True)
                print(f"[Pinterest MCP] Credentials directory: {cred_root}", file=sys.stderr)

                # Check if we have cached credentials from a previous session
                cookie_file = cred_root / config.PINTEREST_EMAIL
                has_cached_cookies = cookie_file.exists()
                if has_cached_cookies:
                    print(f"[Pinterest MCP] Found cached session cookies", file=sys.stderr)

                # Create client with modern User-Agent to avoid 403 errors
                self.pinterest = Pinterest(
                    email=config.PINTEREST_EMAIL,
                    password=config.PINTEREST_PASSWORD,
                    username=None,
                    cred_root=str(cred_root),
                    user_agent=self.MODERN_USER_AGENT  # Use modern browser identifier
                )
                # Force set user_agent (library may not apply constructor param correctly)
                self.pinterest.user_agent = self.MODERN_USER_AGENT
                print(f"[Pinterest MCP] Pinterest client created with User-Agent: {self.pinterest.user_agent[:50]}...", file=sys.stderr)

                # Check if we need to login or can use cached cookies
                if has_cached_cookies and self.pinterest.http.cookies.get('csrftoken'):
                    print("[Pinterest MCP] Using cached session (skipping login)", file=sys.stderr)
                else:
                    print("[Pinterest MCP] Attempting login...", file=sys.stderr)
                    # Try custom login first (more reliable with current Pinterest)
                    if not self._custom_login(cred_root):
                        # Fallback to library login
                        self.pinterest.login()
                    print("[Pinterest MCP] Pinterest login successful!", file=sys.stderr)

            except Exception as e:
                error_msg = str(e)
                print(f"[Pinterest MCP] Failed to init/login Pinterest client: {error_msg}", file=sys.stderr)

                # Provide helpful error messages
                if "403" in error_msg or "Forbidden" in error_msg:
                    print("[Pinterest MCP] 403 Forbidden - This usually means:", file=sys.stderr)
                    print("[Pinterest MCP]   1. Invalid credentials (check email/password)", file=sys.stderr)
                    print("[Pinterest MCP]   2. Pinterest blocked the login (try logging in via browser first)", file=sys.stderr)
                    print("[Pinterest MCP]   3. 2FA is enabled (disable it or handle verification)", file=sys.stderr)
                    print("[Pinterest MCP]   4. Account needs email verification", file=sys.stderr)
                elif "401" in error_msg or "Unauthorized" in error_msg:
                    print("[Pinterest MCP] 401 Unauthorized - Check your credentials", file=sys.stderr)

                import traceback
                traceback.print_exc(file=sys.stderr)
                self.use_real_pinterest = False
                self.pinterest = None
        return self.pinterest

    def _custom_login(self, cred_root: Path) -> bool:
        """
        Custom login implementation that handles Pinterest's current page layout.
        Returns True if login succeeded, False otherwise.
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options as ChromeOptions
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.keys import Keys
            import time
            import json

            chrome_options = ChromeOptions()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'user-agent={self.MODERN_USER_AGENT}')

            print("[Pinterest MCP] Starting custom login with Chrome...", file=sys.stderr)
            driver = webdriver.Chrome(options=chrome_options)

            try:
                driver.get('https://pinterest.com/login')

                # Wait for email field
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.ID, 'email'))
                )
                time.sleep(2)

                # Enter credentials
                email_field = driver.find_element(By.ID, 'email')
                driver.execute_script('arguments[0].click();', email_field)
                time.sleep(0.3)
                email_field.clear()
                email_field.send_keys(config.PINTEREST_EMAIL)

                password_field = driver.find_element(By.ID, 'password')
                driver.execute_script('arguments[0].click();', password_field)
                time.sleep(0.3)
                password_field.clear()
                password_field.send_keys(config.PINTEREST_PASSWORD)

                # Find and click login button or press Enter
                login_buttons = driver.find_elements(By.XPATH, "//button[@type='submit']")
                if login_buttons:
                    driver.execute_script('arguments[0].click();', login_buttons[0])
                else:
                    password_field.send_keys(Keys.RETURN)

                # Wait for login to complete
                time.sleep(5)

                # Check if login was successful
                if 'login' not in driver.current_url.lower():
                    print("[Pinterest MCP] Custom login successful!", file=sys.stderr)

                    # Transfer cookies to requests session
                    cookies = driver.get_cookies()
                    self.pinterest.http.cookies.clear()
                    cookie_dict = {}
                    for cookie in cookies:
                        self.pinterest.http.cookies.set(cookie['name'], cookie['value'])
                        cookie_dict[cookie['name']] = cookie['value']

                    # Save cookies
                    cookie_file = cred_root / config.PINTEREST_EMAIL
                    cookie_file.write_text(json.dumps(cookie_dict))
                    print(f"[Pinterest MCP] Saved {len(cookies)} cookies", file=sys.stderr)
                    return True
                else:
                    print("[Pinterest MCP] Custom login failed - still on login page", file=sys.stderr)
                    return False

            finally:
                driver.quit()

        except Exception as e:
            print(f"[Pinterest MCP] Custom login error: {e}", file=sys.stderr)
            return False

    async def search_images(
        self,
        query: str,
        limit: int = 10,
        art_focused: bool = True
    ) -> list[dict[str, Any]]:
        """
        Search Pinterest for images.

        Args:
            query: Search term
            limit: Maximum number of results (default 10)
            art_focused: Whether to add art-specific filters

        Returns:
            List of image dictionaries with url, title, description, etc.
        """
        print(f"[Pinterest MCP] Searching for: {query} (limit: {limit})", file=sys.stderr)

        # Enhance query for art references if needed
        if art_focused and not any(term in query.lower() for term in ['reference', 'art', 'drawing', 'photo']):
            query = f"{query} reference photo"

        try:
            if self.use_real_pinterest:
                results = await self._real_search(query, limit)
            else:
                results = await self._pexels_fallback(query, limit)

            print(f"[Pinterest MCP] Found {len(results)} results", file=sys.stderr)
            for result in results:
                print(f"  - {result['title']} ({result['image_url']})", file=sys.stderr)
            return results

        except Exception as e:
            print(f"[Pinterest MCP] Search error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return []

    async def _real_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """
        Real Pinterest search using Selenium browser automation.

        Pinterest's internal API has bot detection, so we use browser-based
        scraping which is more reliable.

        Args:
            query: Search term
            limit: Maximum results

        Returns:
            List of image dictionaries
        """
        print(f"[Pinterest MCP] Searching Pinterest for: '{query}'", file=sys.stderr)

        try:
            return self._browser_search(query, limit)
        except Exception as e:
            print(f"[Pinterest MCP] Browser search failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            print("[Pinterest MCP] Falling back to PEXELS API", file=sys.stderr)
            return await self._pexels_fallback(query, limit)

    def _browser_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """
        Search Pinterest using Selenium browser.

        This bypasses Pinterest's API bot detection by using a real browser.
        """
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        import re
        import hashlib

        chrome_options = ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={self.MODERN_USER_AGENT}')

        print("[Pinterest MCP] Starting browser search...", file=sys.stderr)
        driver = webdriver.Chrome(options=chrome_options)

        try:
            # Load cookies if available
            cred_root = Path(__file__).parent / 'cred_root'
            cookie_file = cred_root / config.PINTEREST_EMAIL

            # Navigate to Pinterest first (need to be on domain to set cookies)
            driver.get('https://www.pinterest.com')
            time.sleep(1)

            if cookie_file.exists():
                import json as json_module
                cookies = json_module.loads(cookie_file.read_text())
                for name, value in cookies.items():
                    try:
                        driver.add_cookie({'name': name, 'value': value, 'domain': '.pinterest.com'})
                    except Exception:
                        pass  # Some cookies may fail, that's OK
                print(f"[Pinterest MCP] Loaded {len(cookies)} cookies", file=sys.stderr)

            # Navigate to search page
            encoded_query = query.replace(' ', '%20')
            search_url = f'https://www.pinterest.com/search/pins/?q={encoded_query}'
            driver.get(search_url)

            # Wait for images to load
            time.sleep(4)

            # Scroll down to load more results
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)

            # Extract pin images
            # Pinterest images are on i.pinimg.com
            images = driver.find_elements(By.CSS_SELECTOR, 'img[src*="pinimg.com"]')
            print(f"[Pinterest MCP] Found {len(images)} Pinterest images", file=sys.stderr)

            results = []
            seen_urls = set()

            for img in images:
                if len(results) >= limit:
                    break

                try:
                    src = img.get_attribute('src')
                    if not src or 'pinimg.com' not in src:
                        continue

                    # Skip tiny thumbnails (60x60) and profile pics
                    if '/60x60/' in src or '/75x75/' in src or '/avatars/' in src:
                        continue

                    # Get higher resolution version
                    # Pinterest URLs: https://i.pinimg.com/{size}/{hash}.jpg
                    # Common sizes: 60x60, 236x, 474x, 736x, originals
                    high_res_url = re.sub(r'/\d+x\d*/', '/736x/', src)
                    if high_res_url in seen_urls:
                        continue
                    seen_urls.add(high_res_url)

                    # Get alt text
                    alt = img.get_attribute('alt') or f"{query} reference"

                    # Generate unique ID from URL
                    url_hash = hashlib.md5(high_res_url.encode()).hexdigest()[:12]

                    # Try to find parent link for source URL
                    source_url = 'https://www.pinterest.com'
                    try:
                        parent_link = img.find_element(By.XPATH, './ancestor::a[@href]')
                        href = parent_link.get_attribute('href')
                        if href and '/pin/' in href:
                            source_url = href
                    except Exception:
                        pass

                    results.append({
                        "id": f"pinterest_{url_hash}",
                        "title": alt[:100] if alt else f"{query} reference",
                        "description": f"Pinterest image for {query}",
                        "image_url": high_res_url,
                        "thumbnail_url": src,
                        "source_url": source_url,
                        "board": "Pinterest Search",
                        "creator": "Pinterest User",
                    })

                except Exception as e:
                    continue

            print(f"[Pinterest MCP] Extracted {len(results)} unique pins", file=sys.stderr)
            return results

        finally:
            driver.quit()

    async def _pexels_fallback(self, query: str, limit: int) -> list[dict[str, Any]]:
        """
        Fallback to Pexels API when Pinterest credentials are missing or unavailable.
        Provides clear logging so the user knows what image source is being used.
        """
        print(f"[Pinterest MCP] PEXELS FALLBACK: Searching for '{query}' (limit: {limit})", file=sys.stderr)

        try:
            # Import pexels client from the services module
            from services.pexels_client import pexels_client

            if not config.PEXELS_API_KEY:
                print("[Pinterest MCP] ERROR: No PEXELS_API_KEY configured!", file=sys.stderr)
                print("[Pinterest MCP] Set PEXELS_API_KEY in .env for image search to work", file=sys.stderr)
                return []

            # Search Pexels
            photos = pexels_client.search_photos(query=query, per_page=limit)

            results = []
            for i, photo in enumerate(photos):
                results.append({
                    "id": f"pexels_{photo.id}",
                    "title": photo.alt or f"{query.title()} - Reference {i+1}",
                    "description": f"Reference image from Pexels by {photo.photographer}",
                    "image_url": photo.src_large,
                    "thumbnail_url": photo.src_medium,
                    "source_url": photo.url,
                    "board": "Pexels",
                    "creator": photo.photographer,
                })

            print(f"[Pinterest MCP] PEXELS returned {len(results)} images", file=sys.stderr)
            return results

        except Exception as e:
            print(f"[Pinterest MCP] PEXELS fallback error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return []

    async def get_diverse_results(
        self,
        queries: list[str],
        images_per_query: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search multiple queries and combine results for diversity.

        Args:
            queries: List of search terms
            images_per_query: How many images per query

        Returns:
            Combined list of diverse images
        """
        all_results = []
        seen_ids = set()

        for query in queries:
            results = await self.search_images(query, limit=images_per_query)

            for result in results:
                if result["id"] not in seen_ids:
                    all_results.append(result)
                    seen_ids.add(result["id"])

        print(f"[Pinterest MCP] Diverse search returned {len(all_results)} unique images", file=sys.stderr)
        return all_results


# Initialize the MCP server
app = Server("pinterest-server")
searcher = PinterestSearcher()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Pinterest tools for the MCP client."""
    return [
        Tool(
            name="search_pinterest",
            description="""Search Pinterest for reference images.

            Use this tool to find high-quality reference photos for art practice.
            Works best with specific, concrete search terms.

            Examples:
            - "dancer leap" (not "dynamic pose")
            - "hand holding pencil" (not "hands")
            - "1950s fashion model" (not "vintage style")
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (2-4 words, specific)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results (default 10, max 30)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 30,
                    },
                    "art_focused": {
                        "type": "boolean",
                        "description": "Add art/reference filters to query",
                        "default": True,
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_pinterest_diverse",
            description="""Search Pinterest with multiple queries for diverse results.

            This tool takes multiple search terms and combines results to ensure
            visual diversity in the returned images. Ideal for practice sessions
            where you want variety.

            Example:
            queries: ["ballet dancer", "parkour jump", "martial arts kick", "gymnast pose"]
            Returns: 20 diverse action poses from 4 different contexts
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 3-6 specific search terms",
                        "minItems": 2,
                        "maxItems": 8,
                    },
                    "images_per_query": {
                        "type": "integer",
                        "description": "Images per search term (default 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 10,
                    }
                },
                "required": ["queries"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution requests."""

    if name == "search_pinterest":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        art_focused = arguments.get("art_focused", True)

        if not query:
            return [TextContent(
                type="text",
                text="Error: query parameter is required"
            )]

        results = await searcher.search_images(query, limit, art_focused)

        # Format results as JSON
        response = {
            "query": query,
            "count": len(results),
            "images": results,
        }

        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]

    elif name == "search_pinterest_diverse":
        queries = arguments.get("queries", [])
        images_per_query = arguments.get("images_per_query", 5)

        if not queries or len(queries) < 2:
            return [TextContent(
                type="text",
                text="Error: queries parameter must contain at least 2 search terms"
            )]

        results = await searcher.get_diverse_results(queries, images_per_query)

        response = {
            "queries": queries,
            "total_count": len(results),
            "images": results,
        }

        return [TextContent(
            type="text",
            text=json.dumps(response, indent=2)
        )]

    else:
        return [TextContent(
            type="text",
            text=f"Error: Unknown tool '{name}'"
        )]


async def main():
    """Run the MCP server on stdio."""
    print("[Pinterest MCP] Server starting...", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        print("[Pinterest MCP] Server ready on stdio", file=sys.stderr)
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
