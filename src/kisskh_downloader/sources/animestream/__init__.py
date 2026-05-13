"""AnimeStream source module.

AnimeStream (https://anime.uniquestream.net/) is an anime streaming site
with a clean, open API. No Cloudflare, no encryption.
"""

from .animestream_api import AnimeStreamAPI

__all__ = ["AnimeStreamAPI"]
