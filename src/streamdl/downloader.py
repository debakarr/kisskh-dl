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

        # For CDNs with known key format issues, preprocess playlists first
        # to avoid download-then-fail-then-resume problems
        need_fix = "mediacache.cc" in video_stream_url

        if need_fix:
            # Preprocess playlists first to fix base64 keys
            (fixed_master, temp_dir, server) = self._prepare_fixed_playlist(video_stream_url, headers)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download(fixed_master)
            finally:
                server.shutdown()
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)
            return

        # Try native yt-dlp first
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(video_stream_url)
            return
        except Exception as e:
            if "key length" not in str(e):
                raise

        # ── Fix base64-encoded AES keys by preprocessing playlists ──
        (fixed_url, temp_dir, server) = self._prepare_fixed_playlist(video_stream_url, headers)
        try:
            logger.info("Downloading with fixed playlist at %s", fixed_url)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(fixed_url)
        finally:
            server.shutdown()
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    def _prepare_fixed_playlist(self, url: str, headers: dict) -> tuple[str, str, HTTPServer]:
        """Preprocess HLS playlists: decode base64 keys, serve via local HTTP server.
        Returns (local_url, temp_dir, server)."""
        logger.info("Fixing AES key format in HLS playlists...")
        session = requests.Session()
        session.headers.update(headers)

        temp_dir = tempfile.mkdtemp(prefix="streamdl_")

        def process_m3u8(m3u8_url: str) -> str:
            resp = session.get(m3u8_url, timeout=15)
            resp.raise_for_status()
            content = resp.text

            for m in re.finditer(r'#EXT-X-KEY:METHOD=AES-128,URI="([^"]+)"', content):
                key_url = urljoin(m3u8_url, m.group(1))
                try:
                    kr = session.get(key_url, timeout=15)
                    raw = kr.content.strip()
                    decoded = base64.b64decode(raw)
                    data_uri = f"data:text/plain;base64,{base64.b64encode(decoded).decode()}"
                    content = content.replace(m.group(1), data_uri)
                except Exception:
                    pass

            # Extract query params from playlist URL (needed for segment auth)
            playlist_query = ""
            if "?" in m3u8_url:
                playlist_query = "?" + m3u8_url.split("?", 1)[1]

            lines = content.split("\n")
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                # Check if it's a variant playlist (contains .m3u8)
                if ".m3u8" in stripped:
                    var_clean = stripped.split("?")[0] if "?" in stripped else stripped
                    if var_clean.endswith(".m3u8"):
                        var_path = process_m3u8(urljoin(m3u8_url, stripped))
                        lines[i] = var_path
                    else:
                        lines[i] = urljoin(m3u8_url, stripped)
                else:
                    # Segment URL - make absolute and preserve query params
                    abs_url = urljoin(m3u8_url.split("?")[0], stripped)
                    abs_url += playlist_query
                    lines[i] = abs_url

            name = f"pl_{abs(hash(m3u8_url))}.m3u8"
            local_path = os.path.join(temp_dir, name)
            with open(local_path, "w") as f:
                f.write("\n".join(lines))
            return name

        fixed_master_name = process_m3u8(url)

        server = HTTPServer(("127.0.0.1", 0), _QuietHandler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        os.chdir(temp_dir)
        # Restore cwd when caller continues
        local_url = f"http://127.0.0.1:{port}/{fixed_master_name}"
        logger.info("Serving fixed playlist at %s", local_url)
        return local_url, temp_dir, server

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
