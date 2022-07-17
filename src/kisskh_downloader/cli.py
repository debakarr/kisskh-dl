import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import click
import ffmpeg
import validators

from kisskh_downloader.downloader import Mu3u8Downloader
from kisskh_downloader.kisskh_api import KissKHApi
from kisskh_downloader.utils import get_matching_quality


@click.group()
def kisskh():
    pass


@kisskh.command()
@click.argument("drama_url_or_name")
@click.option(
    "--first", "-f", type=click.INT, default=1, help="Starting episode number."
)
@click.option(
    "--last", "-l", type=click.INT, default=sys.maxsize, help="Ending episode number."
)
@click.option(
    "--quality",
    "-q",
    default="1080p",
    type=click.Choice(["360p", "480p", "540p", "720p", "1080p"]),
    help="Quality of the video to be downloaded.",
)
@click.option(
    "--output-dir",
    "-o",
    default=Path.home() / "Downloads",
    help="Output directory where downloaded files will be store.",
)
@click.option(
    "--force-download",
    "-fd",
    is_flag=True,
    default=False,
    help="Select nearest video quality if expected one not available.",
)
@click.option(
    "--convert-stream-to",
    "-cs",
    default="mkv",
    help="Convert the stream (.ts) to other format (.mkv, .mp4, .avi etc.).",
)
@click.option(
    "--keep-stream-file",
    "-ks",
    is_flag=True,
    default=False,
    help="Keep the .ts format after the conversion is done.",
)
def dl(
    drama_url_or_name: str,
    first: int,
    last: int,
    quality: str,
    output_dir: Path | str,
    force_download: bool,
    convert_stream_to: str,
    keep_stream_file: bool,
) -> None:
    kisskh_api = KissKHApi()
    if validators.url(drama_url_or_name):
        parsed_url = urlparse(drama_url_or_name)
        drama_id = parse_qs(parsed_url.query)["id"][0]
        drama_name = parsed_url.path.split("/")[-1].replace("-", "_")
    else:
        drama = kisskh_api.get_drama_by_query(drama_url_or_name)
        drama_id, drama_name = drama.id, drama.title

    episode_ids = kisskh_api.get_episode_ids(drama_id=drama_id, start=first, stop=last)

    for episode_number, episode_id in episode_ids.items():
        print(f"Getting details for Episode {episode_number}...")
        url = kisskh_api.get_stream_url(episode_id)
        if "tickcounter" in url:
            print(f"Episode {episode_number} still not released!")
            continue

        ms = Mu3u8Downloader(url)
        videos = ms.get_segments_mapping()
        downloadable_quality = get_matching_quality(
            quality, videos.keys(), select_closest_available=force_download
        )
        outfile = f"{output_dir}/{drama_name}/{drama_name}_"
        f"{downloadable_quality}_E{episode_number:02d}.ts"
        ms.download_playlist_segments(outfile, videos.get(downloadable_quality))
        ffmpeg.input(outfile).output(
            filename=f"{outfile[:-3]}.{convert_stream_to}", acodec="copy", vcodec="copy"
        ).global_args("-loglevel", "quiet").run()
        if not keep_stream_file:
            os.remove(outfile)


if __name__ == "__main__":
    kisskh()
