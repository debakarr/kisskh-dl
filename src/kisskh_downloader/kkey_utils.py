"""Utility to generate the kkey authentication token for kisskh API requests.

The kkey is a browser fingerprint encrypted using client-side JS (AES-like).
This module uses Playwright (headless Chromium) to load the episode page and
intercept the kkey from the actual API requests made by the page's JavaScript.

Playwright is only loaded when actually needed. If you set KISSKH_STREAM_KEY
and KISSKH_SUB_KEY environment variables, Playwright is not required.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

# Lazy import: playwright is only imported when KkeyProvider is actually used
_playwright_available = None


def _check_playwright() -> bool:
    """Check if Playwright is available without importing at module level."""
    global _playwright_available
    if _playwright_available is None:
        try:
            # Just check if the package is importable
            import playwright  # noqa: F401

            _playwright_available = True
        except ImportError:
            _playwright_available = False
    return _playwright_available


class KkeyProvider:
    """Generates kkey tokens by loading the episode page in a headless browser.

    Requires Playwright with Chromium installed.
    Run: playwright install chromium
    """

    _playwright_started = False
    _browser = None

    def __init__(self, headless: bool = True, playwright_timeout: int = 30000) -> None:
        self.headless = headless
        self.playwright_timeout = playwright_timeout

    def _ensure_browser(self):
        """Lazily initialize Playwright and launch browser (once)."""
        if KkeyProvider._browser is not None:
            return KkeyProvider._browser

        if not _check_playwright():
            raise ImportError(
                "Playwright is required to generate kkey tokens, but it is not installed.\n"
                "Install it with:\n"
                "  pip install playwright\n"
                "  playwright install chromium\n\n"
                "Alternatively, set KISSKH_STREAM_KEY and KISSKH_SUB_KEY environment variables\n"
                "to skip browser-based kkey generation."
            )

        from playwright.sync_api import sync_playwright

        if not KkeyProvider._playwright_started:
            KkeyProvider._pw = sync_playwright().start()
            KkeyProvider._playwright_started = True

        logger.debug("Launching headless Chromium for kkey generation...")
        KkeyProvider._browser = KkeyProvider._pw.chromium.launch(headless=self.headless)
        return KkeyProvider._browser

    def get_kkeys(
        self,
        drama_id: int,
        episode_id: int,
        episode_number: int,
        drama_title: str,
        episode_page_url: str,
    ) -> dict[str, str]:
        """Load the episode page and extract kkey for stream and subtitle endpoints.

        Returns a dict with keys ``stream`` and ``sub`` containing the kkey values.
        """
        browser = self._ensure_browser()
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()

        captured_kkeys: dict[str, str] = {}

        def intercept_request(request):
            url = request.url
            if "/api/DramaList/Episode/" in url and "kkey=" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "kkey" in params:
                    captured_kkeys["stream"] = params["kkey"][0]
                    logger.debug("Captured stream kkey: %s...", captured_kkeys["stream"][:32])
            elif "/api/Sub/" in url and "kkey=" in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if "kkey" in params:
                    captured_kkeys["sub"] = params["kkey"][0]
                    logger.debug("Captured sub kkey: %s...", captured_kkeys["sub"][:32])

        page.on("request", intercept_request)

        try:
            logger.info("Loading episode page: %s", episode_page_url)
            page.goto(episode_page_url, timeout=self.playwright_timeout, wait_until="networkidle")

            timeout_at = time.time() + (self.playwright_timeout / 1000)
            while len(captured_kkeys) < 2 and time.time() < timeout_at:
                if not captured_kkeys:
                    episode_buttons = page.locator(f"button:has-text('{episode_number}')")
                    if episode_buttons.count() > 0:
                        episode_buttons.first.click()
                        logger.debug("Clicked episode %s button", episode_number)
                page.wait_for_timeout(1000)

        except Exception as e:
            logger.warning("Error while capturing kkeys: %s", e)
        finally:
            page.close()

        if not captured_kkeys:
            raise RuntimeError(
                f"Failed to capture kkey for episode {episode_id}. The site may have changed its API structure."
            )

        return captured_kkeys

    @classmethod
    def cleanup(cls):
        """Close the shared browser instance."""
        if cls._browser is not None:
            try:
                cls._browser.close()
            except Exception:
                logger.debug("Error closing browser", exc_info=True)
            cls._browser = None
        if cls._playwright_started:
            try:
                cls._pw.stop()
            except Exception:
                logger.debug("Error stopping playwright", exc_info=True)
            cls._playwright_started = False
