import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp

from kisskh_downloader.helper.decrypt_subtitle import SubtitleDecrypter
from kisskh_downloader.models.sub import SubItem

logger = logging.getLogger(__name__)


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
            extension = os.path.splitext(urlparse(subtitle.src).path)[-1]
            response = requests.get(subtitle.src, timeout=60)
            output_path = Path(f"{filepath}.{subtitle.land}{extension}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            if decrypter is not None:
                decrypted_subtitle = decrypter.decrypt_subtitles(output_path)
                decrypted_subtitle.save(output_path)
