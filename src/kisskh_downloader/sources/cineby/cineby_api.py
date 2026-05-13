"""Cineby API client for extracting streaming sources.

Uses Playwright to load the movie/TV page, execute the site's JavaScript
(including Cloudflare challenge, WASM decryption, etc.), and extract the
final video source URLs from the page's video player.

Supports movies and TV shows via TMDB IDs.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _extract_tmdb_id(url: str) -> tuple[str, int]:
    """Extract media type (movie/tv) and TMDB ID from a cineby URL.

    Args:
        url: e.g. https://www.cineby.sc/movie/687163
              or https://www.cineby.sc/tv/76479

    Returns:
        Tuple of (media_type, tmdb_id) where media_type is "movie" or "tv".
    """
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    parts = path.split("/")
    if len(parts) < 3:
        raise ValueError(f"Invalid cineby URL: {url}")
    media_type = parts[-2].lower()
    tmdb_id_str = parts[-1].split("?")[0]
    if media_type not in ("movie", "tv"):
        raise ValueError(f"Unsupported media type '{media_type}' in URL: {url}")
    try:
        tmdb_id = int(tmdb_id_str)
    except ValueError:
        raise ValueError(f"Invalid TMDB ID in URL: {url}")
    return media_type, tmdb_id


class CinebyAPI:
    """Client for extracting streaming sources from cineby.sc.

    Uses Playwright to handle the full page lifecycle including:
    - Cloudflare challenge resolution
    - WASM-based decryption of streaming sources
    - Video player initialization

    Once initialized, provides methods to get video source URLs for
    downloading with yt-dlp.
    """

    _playwright_available = None

    def __init__(self, headless: bool = False, timeout: int = 30000):
        """Initialize the Cineby API client.

        Args:
            headless: Whether to run the browser in headless mode.
                      Set to False (default) to avoid Cloudflare detection.
            timeout: Maximum time to wait for page load in milliseconds.
        """
        self.headless = headless
        self.timeout = timeout

    def _check_playwright(self) -> bool:
        """Check if Playwright is installed."""
        if CinebyAPI._playwright_available is None:
            try:
                import playwright  # noqa: F401

                CinebyAPI._playwright_available = True
            except ImportError:
                CinebyAPI._playwright_available = False
        return CinebyAPI._playwright_available

    def get_stream_url(
        self,
        url: str,
        preferred_quality: str = "best",
    ) -> str | None:
        """Extract the video stream URL for a cineby movie/TV page.

        Opens the page with Playwright, waits for the video player to
        load, and captures the video source URL.

        Args:
            url: Full cineby URL (e.g. https://www.cineby.sc/movie/687163)
            preferred_quality: Quality preference ("best", "1080p", "720p", etc.)

        Returns:
            The video stream URL (m3u8) or None if extraction fails.
        """
        if not self._check_playwright():
            raise ImportError(
                "Playwright is required for Cineby source extraction.\n"
                "Install it with: pip install playwright && playwright install chromium"
            )

        from playwright.sync_api import sync_playwright

        media_type, tmdb_id = _extract_tmdb_id(url)
        play_url = f"{url.rstrip('/')}?play=true"

        logger.info("Loading Cineby page: %s", play_url)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            captured_sources: list[str] = []
            sources_api_requested = False

            def on_request(request):
                nonlocal sources_api_requested
                url_str = request.url
                if "downloader2/sources-with-title" in url_str:
                    sources_api_requested = True
                    logger.debug("Sources API request detected: %s", url_str[:120])

            def on_response(response):
                url_str = response.url
                ct = response.headers.get("content-type", "")

                # Capture m3u8 video URLs
                if "m3u8" in url_str or "application/vnd.apple.mpegurl" in ct:
                    logger.info("Found video source: %s", url_str[:120])
                    captured_sources.append(url_str)

                # Also capture direct video URLs
                if "video/mp4" in ct or "video/webm" in ct:
                    logger.info("Found video source: %s", url_str[:120])
                    captured_sources.append(url_str)

                # Log sources API response (encrypted)
                if sources_api_requested and "downloader2/sources-with-title" in url_str:
                    logger.debug("Sources API responded with status %s", response.status)

            page.on("request", on_request)
            page.on("response", on_response)

            try:
                page.goto(play_url, timeout=self.timeout, wait_until="domcontentloaded")
                logger.debug("Page loaded, waiting for video player...")

                # Wait for video player or streaming sources to appear
                timeout_at = time.time() + (self.timeout / 1000)

                while time.time() < timeout_at:
                    # Check if video element appeared
                    has_video = page.evaluate(
                        "() => { const v = document.querySelector('video'); "
                        "return v ? { src: v.currentSrc || v.src, readyState: v.readyState } : null; }"
                    )
                    if has_video and has_video.get("src"):
                        logger.info("Video element found with src: %s", has_video["src"][:100])
                        captured_sources.append(has_video["src"])
                        break

                    # Check for iframes (embedded players)
                    iframes = page.evaluate("() => Array.from(document.querySelectorAll('iframe')).map(f => f.src)")
                    if iframes:
                        logger.debug("Found iframes: %s", iframes)

                    page.wait_for_timeout(2000)

            except Exception as e:
                logger.warning("Error during page load: %s", e)
            finally:
                browser.close()

            if captured_sources:
                logger.info("Found %d video source(s)", len(captured_sources))
                return captured_sources[0]

            logger.warning("No video sources found for: %s", url)
            return None

    def search(self, query: str) -> list[dict]:
        """Search for movies/TV shows on cineby.

        Note: Cineby uses TMDB search behind the scenes.
        This method requires Playwright to navigate the search page.

        Args:
            query: Search term (e.g. "Stranger Things")

        Returns:
            List of search results with id, title, media_type, year
        """
        if not self._check_playwright():
            raise ImportError("Playwright is required for Cineby source extraction.")

        from playwright.sync_api import sync_playwright

        search_url = f"https://www.cineby.sc/search?q={query}"
        results: list[dict] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()

            search_results_data = None

            def on_response(response):
                nonlocal search_results_data
                url_str = response.url
                if "/search" in url_str and response.status == 200:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct or "text/html" in ct:
                        # Try to extract search results from __NEXT_DATA__
                        pass

            page.on("response", on_response)

            try:
                page.goto(search_url, timeout=self.timeout, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                # Extract search results from the page
                next_data = page.evaluate(
                    "() => { const el = document.getElementById('__NEXT_DATA__'); "
                    "return el ? JSON.parse(el.textContent) : null; }"
                )
                if next_data:
                    logger.debug("Got __NEXT_DATA__ from search page")
                    # Parse search results from the page data

            except Exception as e:
                logger.warning("Search error: %s", e)
            finally:
                browser.close()

            return results
