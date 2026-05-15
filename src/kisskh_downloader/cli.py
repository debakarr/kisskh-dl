import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import click
import validators
from dotenv import load_dotenv

from kisskh_downloader.downloader import Downloader
from kisskh_downloader.enums.quality import Quality
from kisskh_downloader.helper.decrypt_subtitle import SubtitleDecrypter
from kisskh_downloader.kisskh_api import KissKHApi

load_dotenv()


def _resolve_base_url() -> str:
    """Return the base URL from env or default."""
    return os.getenv("KISSKH_BASE_URL", "https://kisskh.nl")


def _sanitize_path_component(name: str) -> str:
    """Sanitize a string for safe use as a single path segment.

    Removes path separators, parent directory references, and other
    characters that could enable path traversal attacks.
    """
    sanitized = re.sub(r'[\\/;:|*?"<>]', "_", name)
    sanitized = sanitized.replace("..", "_")
    return sanitized.strip(". ") or "_"


def _format_episode(num: float) -> str:
    """Format an episode number for use in filenames.

    Integer episodes → ``E01``, ``E16``; float/recap episodes → ``E16.1``, ``E16.2``.
    """
    if num == int(num):
        return f"E{int(num):02d}"
    return f"E{num}"


# ── Top-level CLI group ──────────────────────────────────────────────────


@click.group()
@click.option("-v", "--verbose", count=True, help="Increase log level verbosity")
def kisskh(verbose):
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    if verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)


# ── Download command ─────────────────────────────────────────────────────


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
    default=None,
    help="Subtitle decryption key (or set KISSKH_KEY env var).",
)
@click.option(
    "--initialization-vector",
    "-iv",
    default=None,
    help="Initialization vector for subtitle decryption (or set KISSKH_INITIALIZATION_VECTOR env var).",
)
@click.option(
    "--stream-key",
    default=None,
    help="Pre-generated kkey for stream endpoint (or set KISSKH_STREAM_KEY env var). "
    "Skips browser-based kkey generation.",
)
@click.option(
    "--sub-key",
    default=None,
    help="Pre-generated kkey for subtitle endpoint (or set KISSKH_SUB_KEY env var). "
    "Skips browser-based kkey generation.",
)
@click.option(
    "--subs-only",
    "-so",
    is_flag=True,
    default=False,
    help="Download subtitles only, skip video download.",
)
@click.option(
    "--skip-recap",
    is_flag=True,
    default=False,
    help="Skip recap/special episodes (those with fractional episode numbers like 16.1, 16.2).",
)
def dl(
    drama_url_or_name: str,
    first: int,
    last: int,
    quality: str,
    sub_langs: list[str],
    output_dir: Path | str,
    decrypt_subtitle: bool,
    key: str | None,
    initialization_vector: str | None,
    stream_key: str | None,
    sub_key: str | None,
    subs_only: bool = False,
    skip_recap: bool = False,
) -> None:
    """Download episodes from kisskh.

    DRAMA_URL_OR_NAME can be a full URL (e.g. https://kisskh.nl/Drama/Some-Show?id=1234)
    or a search query (e.g. "Stranger Things").
    """
    logger = logging.getLogger(__name__)

    # Resolve secrets from env vars if not passed via CLI
    key = key or os.getenv("KISSKH_KEY")
    initialization_vector = initialization_vector or os.getenv("KISSKH_INITIALIZATION_VECTOR")
    stream_key = stream_key or os.getenv("KISSKH_STREAM_KEY")
    sub_key = sub_key or os.getenv("KISSKH_SUB_KEY")

    if decrypt_subtitle and not (key and initialization_vector):
        raise click.UsageError(
            "--key and --initialization-vector must be provided when --decrypt-subtitle is set. "
            "Either pass them or set them via KISSKH_KEY and KISSKH_INITIALIZATION_VECTOR "
            "environment variables."
        )

    decrypter: SubtitleDecrypter | None = None
    if decrypt_subtitle:
        assert key is not None and initialization_vector is not None  # validated above
        decrypter = SubtitleDecrypter(key=key, initialization_vector=initialization_vector)

    base_url = _resolve_base_url()
    kisskh_api = KissKHApi(base_url=base_url)
    downloader = Downloader(referer=base_url)
    episode_ids: dict[float, int] = {}

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
            episode_ids = {float(episode_number): int(episode_id[0])}
        drama_name = _sanitize_path_component(parsed_url.path.split("/")[2]).replace("-", "_")
    else:
        drama = kisskh_api.get_drama_by_query(drama_url_or_name)
        if drama is None:
            logger.warning("No drama found with the query provided...")
            return None
        drama_id = drama.id
        drama_name = _sanitize_path_component(drama.title)

    if not episode_ids:
        episode_ids = kisskh_api.get_episode_ids(drama_id=drama_id, start=first, stop=last, skip_recap=skip_recap)

    for episode_number, current_episode_id in episode_ids.items():
        episode_tag = _format_episode(episode_number)
        logger.info("Getting details for Episode %s...", episode_tag)

        # Generate or retrieve kkey tokens
        if stream_key and sub_key:
            kkeys = {"stream": stream_key, "sub": sub_key}
            logger.debug("Using kkey from command-line / environment variables")
        else:
            logger.info("Generating authentication token for Episode %s...", episode_tag)
            try:
                kkeys = kisskh_api.generate_kkeys(
                    drama_id=drama_id,
                    episode_id=current_episode_id,
                    episode_number=int(episode_number),
                    drama_title=drama_name,
                )
            except Exception as e:
                logger.error("Failed to generate authentication token for Episode %s: %s", episode_tag, e)
                logger.error(
                    "Tip: Set KISSKH_STREAM_KEY and KISSKH_SUB_KEY environment variables "
                    "to skip browser-based kkey generation."
                )
                continue

        subtitles = kisskh_api.get_subtitles(current_episode_id, kkeys.get("sub", ""), *sub_langs)

        if subs_only:
            filepath = f"{output_dir}/{drama_name}/{drama_name}_{episode_tag}"
            logger.info("Downloading subtitles for Episode %s...", episode_tag)
            downloader.download_subtitles(subtitles, filepath, decrypter)
            continue

        video_stream_url = kisskh_api.get_stream_url(current_episode_id, kkeys.get("stream", ""))
        if "tickcounter" in video_stream_url:
            logger.warning("Episode %s still not released!", episode_tag)
            continue

        filepath = f"{output_dir}/{drama_name}/{drama_name}_{episode_tag}"
        logger.debug("Using video url: %s", video_stream_url)
        downloader.download_video_from_stream_url(video_stream_url, filepath, quality)
        downloader.download_subtitles(subtitles, filepath, decrypter)

    kisskh_api.cleanup()


# ── Get-key command ──────────────────────────────────────────────────────


@kisskh.command(name="get-key")
@click.argument("drama_url")
def get_key(drama_url: str) -> None:
    """Generate and display kkey tokens for a drama episode URL.

    Opens a headless browser to extract the authentication keys that
    kisskh requires for stream and subtitle API calls.

    Example:

        kisskh get-key "https://kisskh.nl/Drama/A-Business-Proposal/Episode-1?id=4608&ep=86192&page=0&pageSize=100"

    After getting the keys, you can export them as environment variables
    and run ``kisskh dl`` without needing a browser each time:

        set KISSKH_STREAM_KEY=<stream_key>
        set KISSKH_SUB_KEY=<sub_key>
    """
    if not validators.url(drama_url):
        raise click.UsageError("A valid episode URL is required.")

    parsed_url = urlparse(drama_url)
    params = parse_qs(parsed_url.query)

    drama_id_str = params.get("id", [None])[0]
    episode_id_str = params.get("ep", [None])[0]
    if not drama_id_str or not episode_id_str:
        raise click.UsageError(
            "URL must contain both ?id=... and &ep=... parameters. "
            "Example: https://kisskh.nl/Drama/.../Episode-1?id=1234&ep=5678"
        )

    drama_id = int(drama_id_str)
    episode_id = int(episode_id_str)
    episode_number = 0
    if episode_string := re.search(r"Episode-(\d+)", parsed_url.path):
        episode_number = int(episode_string.group(1))

    drama_slug = _sanitize_path_component(parsed_url.path.split("/")[2]).replace("-", "_")

    base_url = _resolve_base_url()
    kisskh_api = KissKHApi(base_url=base_url)

    click.echo("Launching browser to extract kkey tokens...")
    try:
        kkeys = kisskh_api.generate_kkeys(
            drama_id=drama_id,
            episode_id=episode_id,
            episode_number=episode_number,
            drama_title=drama_slug,
        )
    except Exception as e:
        raise click.ClickException(f"Failed to generate kkey: {e}")
    finally:
        kisskh_api.cleanup()

    click.echo("")
    click.echo("─" * 50)
    click.echo("  kkey tokens generated successfully!")
    click.echo("─" * 50)
    click.echo("")
    click.echo(f"  Stream key:  {kkeys.get('stream', 'N/A')}")
    click.echo(f"  Sub key:     {kkeys.get('sub', 'N/A')}")
    click.echo("")
    click.echo("  To use these without a browser next time, set these env vars:")
    click.echo("")
    click.echo(f"    set KISSKH_STREAM_KEY={kkeys.get('stream', '')}")
    click.echo(f"    set KISSKH_SUB_KEY={kkeys.get('sub', '')}")
    click.echo("")
    click.echo("  Then run your download command as usual:")
    click.echo(f'    kisskh dl "{drama_url}" -o .')
    click.echo("")


if __name__ == "__main__":
    kisskh()
