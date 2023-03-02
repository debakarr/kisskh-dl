import logging
import re
import sys
from pathlib import Path
from typing import List, Union
from urllib.parse import parse_qs, urlparse

import click
import validators

from kisskh_downloader.downloader import Downloader
from kisskh_downloader.enums.quality import Quality
from kisskh_downloader.kisskh_api import KissKHApi


@click.group()
@click.option("-v", "--verbose", count=True, help="Increase log level verbosity")
def kisskh(verbose):
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    if verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)


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
    sub_langs: List[str],
    output_dir: Union[Path, str],
) -> None:
    logger = logging.getLogger(__name__)
    kisskh_api = KissKHApi()
    downloader = Downloader(referer="https://kisskh.me")
    episode_ids = []
    if validators.url(drama_url_or_name):
        parsed_url = urlparse(drama_url_or_name)
        ids = parse_qs(parsed_url.query).get("id")
        if ids is None:
            raise FileNotFoundError("Not a valid url for a drama!")
        drama_id = int(ids[0])
        episode_id = parse_qs(parsed_url.query).get("ep")
        episode_number = None
        if episode_string := re.search(r"Episode-(\d+)", parsed_url.path):
            episode_number = int(episode_string.group(1))
        if episode_id and episode_number:
            episode_ids = {episode_number: episode_id[0]}
        drama_name = parsed_url.path.split("/")[-1].replace("-", "_")
    else:
        drama = kisskh_api.get_drama_by_query(drama_url_or_name)
        if drama is None:
            logger.warning("No drama found with the query provided...")
            return None
        drama_id = drama.id
        drama_name = drama.title

    if not episode_ids:
        episode_ids = kisskh_api.get_episode_ids(drama_id=drama_id, start=first, stop=last)

    for episode_number, episode_id in episode_ids.items():
        logger.info(f"Getting details for Episode {episode_number}...")
        video_stream_url = kisskh_api.get_stream_url(episode_id)
        subtitles = kisskh_api.get_subtitles(episode_id, *sub_langs)
        if "tickcounter" in video_stream_url:
            logger.warning(f"Episode {episode_number} still not released!")
            continue

        filepath = f"{output_dir}/{drama_name}/{drama_name}_E{episode_number:02d}"
        logger.debug(f"Using video url: {video_stream_url}")
        downloader.download_video_from_stream_url(video_stream_url, filepath, quality)
        downloader.download_subtitles(subtitles, filepath)


if __name__ == "__main__":
    kisskh()
