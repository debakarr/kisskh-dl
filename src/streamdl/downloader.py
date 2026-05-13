"""Download videos using yt-dlp or manual HLS with custom AES key handling."""

import base64
import concurrent.futures
import logging
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yt_dlp
from Cryptodome.Cipher import AES

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
        session = requests.Session()
        session.headers.update(headers)

        # For CDNs that use base64-encoded AES keys (.png segments, mediacache.cc)
        if "mediacache.cc" in video_stream_url:
            self._download_hls_manual(session, video_stream_url, filepath)
            return

        # Default: use yt-dlp
        ydl_opts = {
            "format": f"bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]/best",
            "concurrent_fragment_downloads": 15,
            "outtmpl": f"{filepath}.%(ext)s",
            "http_headers": headers,
            "verbose": logger.getEffectiveLevel() == logging.DEBUG,
            "retries": 10,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(video_stream_url)
        except Exception as e:
            # Try fallback to manual HLS for key format issues
            if "key length" in str(e).lower():
                logger.info("Key format issue, falling back to manual HLS...")
                self._download_hls_manual(session, video_stream_url, filepath)
            else:
                raise

    def _download_hls_manual(self, session: requests.Session, master_url: str, filepath: str) -> None:
        """Download HLS stream manually, handling base64-encoded AES keys."""
        logger.info("Downloading HLS stream manually...")

        # Download master playlist
        resp = session.get(master_url, timeout=15)
        resp.raise_for_status()
        master = resp.text

        # Find variant playlist URL (prefer 1080p, fallback to first)
        var_url = None
        for line in master.split("\n"):
            line = line.strip()
            if ".m3u8" in line and not line.startswith("#"):
                if "1080" in line or var_url is None:
                    var_url = urljoin(master_url, line)
        if not var_url:
            raise RuntimeError("No variant playlist found")

        logger.debug("Variant: %s", var_url[:80])

        # Download variant playlist
        resp = session.get(var_url, timeout=15)
        resp.raise_for_status()
        var_text = resp.text

        # Get query parameters for segment URLs
        var_query = ("?" + var_url.split("?", 1)[1]) if "?" in var_url else ""

        # Parse segments
        segments: list[str] = []
        key_data: bytes | None = None
        iv: bytes | None = None
        key_url_str: str | None = None

        for line in var_text.split("\n"):
            stripped = line.strip()

            # Find key URL
            if "#EXT-X-KEY" in stripped:
                km = re.search(r'URI="([^"]+)"', stripped)
                if km:
                    key_url_str = urljoin(master_url, km.group(1))
                ivm = re.search(r"IV=0x([0-9A-Fa-f]+)", stripped)
                if ivm:
                    iv = bytes.fromhex(ivm.group(1))

            # Find segment URLs
            if stripped and not stripped.startswith("#"):
                seg_url = urljoin(var_url, stripped)
                # Add query params if not present
                if "?" not in seg_url and var_query:
                    seg_url += var_query
                segments.append(seg_url)

        # Resolve and decode key
        if key_url_str:
            # Resolve relative to master or variant
            key_url = urljoin(master_url, key_url_str)
            logger.debug("Key URL: %s", key_url[:80])
            kr = session.get(key_url, timeout=15)
            key_raw = kr.content.strip()
            # Try base64 decode first; fall back to raw first 16 bytes
            try:
                key_data = base64.b64decode(key_raw)[:16]
            except Exception:
                key_data = key_raw[:16]
            logger.debug("Key (%d bytes): %s", len(key_data), key_data.hex())

        if iv is None and key_data:
            iv = key_data  # Default: IV = key

        if not key_data:
            raise RuntimeError("Could not resolve decryption key")

        # Download segments concurrently with Ctrl+C handling
        logger.info("Downloading %d segments...", len(segments))
        original_sigint = signal.getsignal(signal.SIGINT)

        def fetch_segment(i_seg):
            i, seg_url = i_seg
            for attempt in range(3):
                try:
                    resp = session.get(seg_url, timeout=30)
                    resp.raise_for_status()
                    data = resp.content
                    if key_data:
                        cipher = AES.new(key_data, AES.MODE_CBC, iv or key_data)
                        return (i, cipher.decrypt(data))
                    return (i, data)
                except Exception as e:
                    if attempt == 2:
                        raise
                    logger.warning("Retry %d for segment %d: %s", attempt + 1, i + 1, e)
            return (i, b"")

        def sigint_handler(sig, frame):
            logger.warning("\nCtrl+C pressed, stopping download...")
            sys.exit(1)

        signal.signal(signal.SIGINT, sigint_handler)
        results: list[tuple[int, bytes]] = []
        max_workers = min(10, len(segments))
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(fetch_segment, (i, s)) for i, s in enumerate(segments)]
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    results.append(future.result())
                    if (i + 1) % 25 == 0 or i == 0:
                        logger.info("Segment %d/%d", i + 1, len(segments))
        finally:
            signal.signal(signal.SIGINT, original_sigint)

        results.sort(key=lambda x: x[0])
        temp_ts = f"{filepath}.ts"
        with open(temp_ts, "wb") as out:
            for _, data in results:
                out.write(data)

        # Remux to MP4
        output_mp4 = f"{filepath}.mp4"
        logger.info("Remuxing to MP4: %s", output_mp4)
        try:
            subprocess.run(  # noqa: S603,S607
                ["ffmpeg", "-i", temp_ts, "-c", "copy", "-y", output_mp4],
                capture_output=True,
                text=True,
                timeout=120,
            )
            os.unlink(temp_ts)
            logger.info("Download complete: %s", output_mp4)
        except Exception:
            logger.info("Remux skipped, file at: %s", temp_ts)

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
