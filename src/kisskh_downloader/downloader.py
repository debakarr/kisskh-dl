import os
from pathlib import Path
from urllib.parse import urlparse

import requests
import yt_dlp

from kisskh_downloader.models.sub import SubItem


class Downloader:
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
            "postprocessors": [{"key": "FFmpegFixupM3u8"}],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download(video_stream_url)

    def download_subtitles(self, subtitles: list[SubItem], filepath: str) -> None:
        """Download subtitles

        :param subtitles: list of all subtitles
        :param filepath: file path where to download
        """
        for subtitle in subtitles:
            print(f"Downloading {subtitle.label} sub...")
            extension = os.path.splitext(urlparse(subtitle.src).path)[-1]
            response = requests.get(subtitle.src)
            Path(f"{filepath}.{subtitle.land}{extension}").write_bytes(response.content)
