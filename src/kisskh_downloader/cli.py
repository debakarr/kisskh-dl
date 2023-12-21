import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Union
from urllib.parse import parse_qs, urlparse

import click
import validators
from dotenv import load_dotenv

from kisskh_downloader.downloader import Downloader
from kisskh_downloader.enums.quality import Quality
from kisskh_downloader.helper.decrypt_subtitle import SubtitleDecrypter
from kisskh_downloader.kisskh_api import KissKHApi

load_dotenv()


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
@click.option(
    "--decrypt-subtitle",
    "-ds",
    is_flag=True,
    help="Decrypt the downloaded subtitle",
)
@click.option(
    "--key",
    "-k",
    default=os.getenv("KISSKH_KEY"),
    help="Decryption key",
)
@click.option(
    "--initialization-vector",
    "-iv",
    default=os.getenv("KISSKH_INITIALIZATION_VECTOR"),
    help="Initialization vector for decryption",
)
def dl(
    drama_url_or_name: str,
    first: int,
    last: int,
    quality: str,
    sub_langs: List[str],
    output_dir: Union[Path, str],
    decrypt_subtitle: bool,
    key: str,
    initialization_vector: str,
) -> None:
    logger = logging.getLogger(__name__)

    if decrypt_subtitle and not (key and initialization_vector):
        raise click.UsageError(
            "--key and --initialization-vector must be provided when --decrypt-subtitle is set. "
            "Either pass them or set them via KISSKH_KEY and KISSKH_INITIALIZATION_VECTOR environment variable."
        )

    decrypter = SubtitleDecrypter(key=key, initialization_vector=initialization_vector) if decrypt_subtitle else None

    kisskh_api = KissKHApi()
    downloader = Downloader(referer="https://kisskh.co")
    episode_ids: Dict[int, int] = {}
    if validators.url(drama_url_or_name):
        parsed_url = urlparse(drama_url_or_name)
        ids = parse_qs(parsed_url.query).get("id")
        if ids is None:
            raise FileNotFoundError("Not a valid url for a drama!")
        drama_id = int(ids[0])
        episode_id = parse_qs(parsed_url.query).get("ep")
        episode_number = None
        if episode_string := re.search(r"Episode-(\d+)", parsed_url.path):
            episode_number = episode_string.group(1)
        if episode_id and episode_number:
            episode_ids = {int(episode_number): int(episode_id[0])}
        drama_name = parsed_url.path.split("/")[2].replace("-", "_")
    else:
        drama = kisskh_api.get_drama_by_query(drama_url_or_name)
        if drama is None:
            logger.warning("No drama found with the query provided...")
            return None
        drama_id = drama.id
        drama_name = drama.title

    if not episode_ids:
        episode_ids = kisskh_api.get_episode_ids(drama_id=drama_id, start=first, stop=last)

    for episode_number, episode_id in episode_ids.items():  # type: ignore
        logger.info(f"Getting details for Episode {episode_number}...")
        video_stream_url = kisskh_api.get_stream_url(episode_id)  # type: ignore
        subtitles = kisskh_api.get_subtitles(episode_id, *sub_langs)  # type: ignore
        if "tickcounter" in video_stream_url:
            logger.warning(f"Episode {episode_number} still not released!")
            continue

        filepath = f"{output_dir}/{drama_name}/{drama_name}_E{episode_number:02d}"
        logger.debug(f"Using video url: {video_stream_url}")
        downloader.download_video_from_stream_url(video_stream_url, filepath, quality)
        downloader.download_subtitles(subtitles, filepath, decrypter)


if __name__ == "__main__":
    kisskh()
