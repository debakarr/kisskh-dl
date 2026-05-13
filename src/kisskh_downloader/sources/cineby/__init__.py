"""Cineby source module.

Cineby (https://www.cineby.sc/) is a free movie and TV show streaming site
that uses TMDB IDs for content. It has multi-layer anti-bot protection:
  - Cloudflare challenge
  - Encrypted streaming source API (WASM + AES decrypt)
  - Custom XOR-based hash for AES key derivation

This module uses Playwright to handle the browser-side JavaScript execution
naturally, including Cloudflare challenges and WASM decryption.
"""

from .cineby_api import CinebyAPI

__all__ = ["CinebyAPI"]
