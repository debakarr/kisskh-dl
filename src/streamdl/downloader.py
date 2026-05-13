"""Download videos using yt-dlp with HLS preprocessing for non-standard keys."""

import base64
import logging
import os
import re
import tempfile
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yt_dlp

from streamdl.helper.decrypt_subtitle import SubtitleDecrypter
from streamdl.models.sub import SubItem

logger = logging.getLogger(__name__)


class _QuietHandler(SimpleHTTPRequestHandler):
    """HTTP handler that doesn't log to stdout."""

    def log_message(self, *args):
        pass


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

        ydl_opts = {
            "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]/best",
            "concurrent_fragment_downloads": 15,
            "outtmpl": f"{filepath}.%(ext)s",
            "http_headers": headers,
            "verbose": logger.getEffectiveLevel() == logging.DEBUG,
            "retries": 10,
        }
        logger.debug("Download options: %s", ydl_opts)

        # Try native yt-dlp first
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(video_stream_url)
            return
        except Exception as e:
            if "key length" not in str(e):
                raise

        # ── Fix base64-encoded AES keys by preprocessing playlists ──
        logger.info("Fixing AES key format in HLS playlists...")
        session = requests.Session()
        session.headers.update(headers)

        temp_dir = tempfile.mkdtemp(prefix="streamdl_")

        def process_m3u8(url: str) -> str:
            """Download m3u8, fix keys, save to temp dir. Return local path."""
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            content = resp.text

            # Fix AES keys: download base64 key, decode, replace with data URI
            for m in re.finditer(r'#EXT-X-KEY:METHOD=AES-128,URI="([^"]+)"', content):
                key_url = urljoin(url, m.group(1))
                try:
                    kr = session.get(key_url, timeout=15)
                    raw = kr.content.strip()
                    decoded = base64.b64decode(raw)
                    data_uri = f"data:text/plain;base64,{base64.b64encode(decoded).decode()}"
                    content = content.replace(m.group(1), data_uri)
                except Exception:
                    pass

            # Recursively process variant playlists
            lines = content.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if ".m3u8" in stripped and not stripped.startswith("#"):
                    # Extract the URL part before query string
                    var_url = stripped.split("?")[0] if "?" in stripped else stripped
                    if var_url.endswith(".m3u8"):
                        var_path = process_m3u8(urljoin(url, stripped))  # pass full URL including query
                        lines[i] = var_path

            # Save to temp dir. Return just filename (relative path for HTTP server).
            name = f"pl_{abs(hash(url))}.m3u8"
            local_path = os.path.join(temp_dir, name)
            with open(local_path, "w") as f:
                f.write("\n".join(lines))
            return name  # relative path for HTTP server

        # Fix all playlists
        fixed_master = process_m3u8(video_stream_url)

        # Start a local HTTP server to serve fixed playlists to yt-dlp
        server = HTTPServer(("127.0.0.1", 0), _QuietHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            os.chdir(temp_dir)
            local_url = f"http://127.0.0.1:{port}/{os.path.basename(fixed_master)}"
            logger.info("Serving fixed playlist at %s", local_url)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(local_url)
        finally:
            server.shutdown()
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
