"""Download videos using yt-dlp with HLS preprocessing for non-standard keys."""

import base64
import logging
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yt_dlp

from streamdl.helper.decrypt_subtitle import SubtitleDecrypter
from streamdl.models.sub import SubItem

logger = logging.getLogger(__name__)


class Downloader:
    def __init__(self, referer: str) -> None:
        self.referer = referer

    def download_video_from_stream_url(self, video_stream_url: str, filepath: str, quality: str) -> None:
        headers = {
            "Referer": self.referer,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Safari/537.36"
            ),
        }

        # Try native yt-dlp first
        ydl_opts = {
            "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]/best",
            "concurrent_fragment_downloads": 15,
            "outtmpl": f"{filepath}.%(ext)s",
            "http_headers": headers,
            "verbose": logger.getEffectiveLevel() == logging.DEBUG,
            "retries": 10,
        }
        logger.debug("Download options: %s", ydl_opts)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(video_stream_url)
            return
        except Exception as e:
            if "key length" in str(e):
                logger.info("Key format issue detected, preprocessing playlist...")
            else:
                raise

        # Fix: download playlist, decode base64 key, rewrite with data URI key
        session = requests.Session()
        session.headers.update(headers)

        def fix_key(content: str, base_url: str) -> str:
            """Replace base64-encoded AES keys in m3u8 with data URIs."""
            for m in re.finditer(r'#EXT-X-KEY:METHOD=AES-128,URI="([^"]+)"', content):
                key_url = urljoin(base_url, m.group(1))
                logger.debug("Fixing key: %s", key_url)
                try:
                    kr = session.get(key_url, timeout=15)
                    raw = kr.content.strip()
                    decoded = base64.b64decode(raw)
                except Exception:
                    decoded = raw[:16]
                data_uri = f"data:text/plain;base64,{base64.b64encode(decoded).decode()}"
                content = content.replace(m.group(1), data_uri)
            return content

        def resolve_url(base: str, url: str) -> str:
            if url.startswith("http"):
                return url
            return urljoin(base, url)

        def fix_all_playlists(master_url: str) -> str:
            """Recursively fix keys in master and variant playlists. Returns local path."""
            resp = session.get(master_url, timeout=15)
            resp.raise_for_status()
            master = resp.text

            # Find variant playlist URLs (line after #EXT-X-STREAM-INF or direct .m3u8)
            lines = master.split("\n")
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.endswith(".m3u8") and not stripped.startswith("#"):
                    var_url = resolve_url(master_url, stripped)
                    var_resp = session.get(var_url, timeout=15)
                    var_fixed = fix_key(var_resp.text, var_url)
                    # Save variant to temp
                    var_name = f"v_{abs(hash(var_url))}.m3u8"
                    var_path = os.path.join(temp_dir, var_name)
                    with open(var_path, "w") as f:
                        f.write(var_fixed)
                    new_lines.append(var_path)
                else:
                    new_lines.append(line)
            master = "\n".join(new_lines)
            master = fix_key(master, master_url)
            master_path = os.path.join(temp_dir, "master.m3u8")
            with open(master_path, "w") as f:
                f.write(master)
            return master_path

        temp_dir = tempfile.mkdtemp(prefix="streamdl_")
        try:
            fixed_path = fix_all_playlists(video_stream_url)
            logger.info("Retrying with fixed playlist...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(fixed_path)
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def download_subtitles(
        self, subtitles: list[SubItem], filepath: str, decrypter: SubtitleDecrypter | None = None
    ) -> None:
        for subtitle in subtitles:
            logger.info("Downloading %s sub...", subtitle.label)
            extension = os.path.splitext(urlparse(subtitle.src).path)[-1]
            response = requests.get(subtitle.src, timeout=60)
            output_path = Path(f"{filepath}.{subtitle.land}{extension}")
            output_path.write_bytes(response.content)
            if decrypter is not None:
                decrypted_subtitle = decrypter.decrypt_subtitles(output_path)
                decrypted_subtitle.save(output_path)
