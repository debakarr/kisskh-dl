"""Download videos using yt-dlp or direct ffmpeg."""

import logging
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp

from streamdl.helper.decrypt_subtitle import SubtitleDecrypter
from streamdl.models.sub import SubItem

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self, referer: str) -> None:
        self.referer = referer

    def download_video_from_stream_url(self, video_stream_url: str, filepath: str, quality: str) -> None:
        """Download a video from stream url.

        Tries yt-dlp first. If that fails (AES key format, .png segments),
        falls back to direct ffmpeg.
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
        logger.debug("Download options: %s", ydl_opts)

        # Try native yt-dlp downloader
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(video_stream_url)
            return
        except Exception as e:
            if "key length" in str(e).lower():
                logger.info("yt-dlp native failed on key format, retrying with ffmpeg...")
            elif "not in allowed_segment_extensions" in str(e):
                logger.info("yt-dlp ffmpeg failed on segment extension, retrying with direct ffmpeg...")
            else:
                raise

        # Fallback: direct ffmpeg with proper args
        output = f"{filepath}.mp4"
        logger.info("Downloading directly with ffmpeg to: %s", output)
        cmd = [
            "ffmpeg",
            "-allowed_extensions",
            "ALL",
            "-protocol_whitelist",
            "file,http,https,tcp,tls",
            "-i",
            video_stream_url,
            "-map",
            "0:v?",
            "-map",
            "0:a?",
            "-c",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            "-y",
            output,
        ]
        logger.debug("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
        if result.returncode != 0:
            logger.error("ffmpeg failed: %s", result.stderr[-500:])
            raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

    def download_subtitles(
        self, subtitles: list[SubItem], filepath: str, decrypter: SubtitleDecrypter | None = None
    ) -> None:
        """Download subtitles"""
        for subtitle in subtitles:
            logger.info("Downloading %s sub...", subtitle.label)
            extension = os.path.splitext(urlparse(subtitle.src).path)[-1]
            response = requests.get(subtitle.src, timeout=60)
            output_path = Path(f"{filepath}.{subtitle.land}{extension}")
            output_path.write_bytes(response.content)
            if decrypter is not None:
                decrypted_subtitle = decrypter.decrypt_subtitles(output_path)
                decrypted_subtitle.save(output_path)
