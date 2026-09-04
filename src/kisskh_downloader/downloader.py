import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp

from kisskh_downloader.helper.decrypt_subtitle import SubtitleDecrypter
from kisskh_downloader.models.sub import SubItem

logger = logging.getLogger(__name__)

# Upper bound for subtitle file downloads to prevent disk exhaustion
# from a malicious/compromised API response.
MAX_SUBTITLE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MiB


def _sanitize_path_component(name: str) -> str:
    """Sanitize a string for safe use as a single path segment.

    Strips control characters, path separators, parent-directory
    references and other characters that could enable path traversal.
    """
    sanitized = re.sub(r'[\\\0-\037/;:|*?"<>]', "_", name)
    sanitized = sanitized.replace("..", "_")
    return sanitized.strip(". ") or "_"


def _safe_extension(src: str) -> str:
    """Extract a safe file extension from a URL, defaulting to ``.srt``."""
    extension = os.path.splitext(urlparse(src).path)[-1]
    if not re.fullmatch(r"\.[A-Za-z0-9]{1,10}", extension):
        return ".srt"
    return extension.lower()


class Downloader:
    def __init__(self, referer: str) -> None:
        self.referer = referer

    def download_video_from_stream_url(self, video_stream_url: str, filepath: str, quality: str) -> None:
        """Download a video from stream url

        :param video_stream_url: stream url
        :param filepath: file path where to download
        :param quality: quality to select
        """
        ydl_opts = {
            "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]/best",
            "concurrent_fragment_downloads": 15,
            "outtmpl": f"{filepath}.%(ext)s",
            "http_headers": {
                "Referer": self.referer,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
            },
            "verbose": logger.getEffectiveLevel() == logging.DEBUG,
            "retries": 10,
        }
        logger.debug("Calling download with options: %s", ydl_opts)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(video_stream_url)

    def download_subtitles(
        self, subtitles: list[SubItem], filepath: str, decrypter: SubtitleDecrypter | None = None
    ) -> None:
        """Download subtitles

        :param subtitles: list of all subtitles
        :param filepath: file path where to download
        """
        for subtitle in subtitles:
            logger.info("Downloading %s sub...", subtitle.label)
            if urlparse(subtitle.src).scheme not in ("http", "https"):
                logger.warning("Skipping %s subtitles: unsupported URL scheme.", subtitle.label)
                continue

            response = requests.get(subtitle.src, timeout=60, stream=True)
            response.raise_for_status()

            declared_size = int(response.headers.get("Content-Length") or 0)
            if declared_size > MAX_SUBTITLE_SIZE_BYTES:
                logger.warning(
                    "Skipping %s subtitles: declared size %d bytes exceeds limit.",
                    subtitle.label,
                    declared_size,
                )
                response.close()
                continue

            chunks: list[bytes] = []
            received = 0
            too_large = False
            for chunk in response.iter_content(chunk_size=64 * 1024):
                received += len(chunk)
                if received > MAX_SUBTITLE_SIZE_BYTES:
                    logger.warning("Skipping %s subtitles: download exceeded size limit.", subtitle.label)
                    too_large = True
                    break
                chunks.append(chunk)
            response.close()
            if too_large:
                continue

            land = _sanitize_path_component(subtitle.land)
            extension = _safe_extension(subtitle.src)
            output_path = Path(f"{filepath}.{land}{extension}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"".join(chunks))
            if decrypter is not None:
                decrypted_subtitle = decrypter.decrypt_subtitles(output_path)
                decrypted_subtitle.save(output_path)
