import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import click
import validators

from kisskh_downloader.downloader import Downloader
from kisskh_downloader.enums.quality import Quality
from kisskh_downloader.kisskh_api import KissKHApi


@click.group()
def kisskh():
    pass


@kisskh.command()
@click.argument("drama_url_or_name")
@click.option("--first", "-f", type=click.INT, default=1, help="Starting episode number.")
@click.option("--last", "-l", type=click.INT, default=sys.maxsize, help="Ending episode number.")
@click.option(
    "--quality",
    "-q",
    default="1080p",
    type=click.Choice([quality.value for quality in Quality]),
    help="Quality of the video to be downloaded.",
)
@click.option(
    "--sub-langs",
    "-s",
    default=("en",),
    multiple=True,
    help="Languages of the subtitles to download.",
)
@click.option(
    "--output-dir",
    "-o",
    default=Path.home() / "Downloads",
    help="Output directory where downloaded files will be store.",
)
def dl(
    drama_url_or_name: str,
    first: int,
    last: int,
    quality: str,
    sub_langs: list[str],
    output_dir: Path | str,
) -> None:
    kisskh_api = KissKHApi()
    downloader = Downloader()
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
        video_stream_url = kisskh_api.get_stream_url(episode_id)
        subtitles = kisskh_api.get_subtitles(episode_id, *sub_langs)
        if "tickcounter" in video_stream_url:
            print(f"Episode {episode_number} still not released!")
            continue

        filepath = f"{output_dir}/{drama_name}/{drama_name}_E{episode_number:02d}"
        downloader.download_video_from_stream_url(video_stream_url, filepath, quality)
        downloader.download_subtitles(subtitles, filepath)


if __name__ == "__main__":
    kisskh()
