import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import click
import validators
from dotenv import load_dotenv

from streamdl.downloader import Downloader
from streamdl.enums.quality import Quality
from streamdl.helper.decrypt_subtitle import SubtitleDecrypter
from streamdl.kisskh_api import KissKHApi
from streamdl.sources import detect_source, init_sources, list_sources, search_all

load_dotenv()


def _resolve_base_url() -> str:
    """Return the base URL from env or default."""
    return os.getenv("KISSKH_BASE_URL", "https://kisskh.nl")


def _dispatch_animestream(
    content_id: str, output_dir: Path, locale: str = "ja-JP", subtitle_locale: str = "en-US", **kwargs
) -> None:
    """Download from AnimeStream by content ID."""
    from streamdl.downloader import Downloader
    from streamdl.sources.animestream import AnimeStreamAPI

    logger = logging.getLogger(__name__)
    api = AnimeStreamAPI()
    info = api.content(content_id)
    series = info.get("series_title", info.get("title", ""))
    ep = info.get("episode", "0")
    logger.info("%s - Episode %s: %s", series, ep, info.get("title", ""))

    sub = subtitle_locale if subtitle_locale and subtitle_locale != "off" else None
    stream_url = api.get_stream_url(content_id, locale=locale, subtitle_locale=sub)
    if not stream_url:
        logger.error("Could not get stream URL for content_id: %s", content_id)
        return

    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in series).strip()
    filepath = str(Path(str(output_dir)) / f"{safe}_E{ep}")
    Downloader(referer="https://anime.uniquestream.net/").download_video_from_stream_url(stream_url, filepath, "1080p")
    logger.info("Downloaded: %s", filepath)


def _dispatch_dl(url_or_query: str, output_dir: Path, quality: str, **kwargs) -> None:
    """Route a download to the correct source."""
    logger = logging.getLogger(__name__)

    if validators.url(url_or_query):
        # ── URL mode: detect source and download ──
        source_cls = detect_source(url_or_query)
        if source_cls is None:
            known = ", ".join(s.domains[0] for s in list_sources())
            logger.error("Unknown source in URL. Supported: %s", known)
            return

        logger.info("Detected source: %s", source_cls.name)
        info = source_cls.get_content_info(url_or_query)
        stream_url = source_cls.get_stream_url(url_or_query, **kwargs)

        if not stream_url:
            logger.error("Could not get stream URL.")
            return

        title = info.get("title", "video").replace(" ", "_")
        ep = info.get("episode", "")
        filename = f"{title}_E{ep}" if ep else title
        filepath = str(Path(str(output_dir)) / filename)

        downloader = Downloader(referer=url_or_query)
        downloader.download_video_from_stream_url(stream_url, filepath, quality)
        logger.info("Downloaded: %s", filepath)

    else:
        # ── Search mode: first try direct content_id (AnimeStream) ──
        try:
            from streamdl.sources.animestream import AnimeStreamAPI

            info = AnimeStreamAPI().content(url_or_query)
            if info.get("content_id"):
                logger.info(
                    "Direct content ID detected: %s - Episode %s",
                    info.get("series_title", "?"),
                    info.get("episode", "?"),
                )
                _dispatch_animestream(url_or_query, output_dir, **kwargs)
                return
        except Exception:
            pass

        # ── Search all sources ──
        logger.info("Searching all sources for: %s", url_or_query)
        results = search_all(url_or_query)

        if not results:
            logger.warning("No results found for: %s", url_or_query)
            return

        click.echo("\nResults:")
        for i, r in enumerate(results, 1):
            click.echo(f"  {i}. [{r.get('source', '?')}] {r.get('title', '?')}")
        click.echo()

        selection = click.prompt("Select a result", type=int, default=1)
        if selection < 1 or selection > len(results):
            logger.warning("Invalid selection.")
            return

        chosen = results[selection - 1]
        chosen_url = chosen.get("url", "")
        if not chosen_url:
            logger.error("No URL for selected item.")
            return

        click.echo(f"Downloading: {chosen.get('title')}")
        _dispatch_dl(chosen_url, output_dir, quality, **kwargs)


# ── Top-level CLI group ──────────────────────────────────────────────────


@click.group()
@click.option("-v", "--verbose", count=True, help="Increase log level verbosity")
def streamdl(verbose):
    init_sources()
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
    if verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)


# ── Kisskh-specific download logic ───────────────────────────────────────


def _dispatch_kisskh(
    url: str,
    first: int,
    last: int,
    quality: str,
    sub_langs: list[str],
    output_dir: Path | str,
    decrypt_subtitle: bool,
    key: str,
    initialization_vector: str,
    stream_key: str,
    sub_key: str,
) -> None:
    """Kisskh-specific download with episode range, subs, and kkey support."""
    logger = logging.getLogger(__name__)
    if decrypt_subtitle and not (key and initialization_vector):
        raise click.UsageError("--key and --iv required with --decrypt-subtitle.")
    decrypter = SubtitleDecrypter(key=key, initialization_vector=initialization_vector) if decrypt_subtitle else None
    base_url = _resolve_base_url()
    api = KissKHApi(base_url=base_url)
    downloader = Downloader(referer=base_url)
    episode_ids: dict[int, int] = {}
    parsed_url = urlparse(url)
    ids = parse_qs(parsed_url.query).get("id")
    if not ids:
        logger.error("Not a valid kisskh URL (missing ?id=...).")
        return
    drama_id = int(ids[0])
    ep_id = parse_qs(parsed_url.query).get("ep")
    ep_number = None
    if ep_string := re.search(r"Episode-(\d+)", parsed_url.path):
        ep_number = ep_string.group(1)
    if ep_id and ep_number:
        episode_ids = {int(ep_number): int(ep_id[0])}
    drama_name = parsed_url.path.split("/")[2].replace("-", "_")
    if not episode_ids:
        episode_ids = api.get_episode_ids(drama_id=drama_id, start=first, stop=last)
    for ep_num, cur_ep_id in episode_ids.items():
        logger.info("Getting details for Episode %s...", ep_num)
        if stream_key and sub_key:
            kkeys = {"stream": stream_key, "sub": sub_key}
        else:
            logger.info("Generating auth token for Episode %s...", ep_num)
            try:
                kkeys = api.generate_kkeys(
                    drama_id=drama_id,
                    episode_id=cur_ep_id,
                    episode_number=ep_num,
                    drama_title=drama_name,
                )
            except Exception as e:
                logger.error("Failed to generate auth token for Episode %s: %s", ep_num, e)
                continue
        video_url = api.get_stream_url(cur_ep_id, kkeys.get("stream", ""))
        subtitles = api.get_subtitles(cur_ep_id, kkeys.get("sub", ""), *sub_langs)
        if "tickcounter" in video_url:
            logger.warning("Episode %s still not released!", ep_num)
            continue
        filepath = f"{output_dir}/{drama_name}/{drama_name}_E{ep_num:02d}"
        downloader.download_video_from_stream_url(video_url, filepath, quality)
        downloader.download_subtitles(subtitles, filepath, decrypter)
    api.cleanup()


# ── Download command ─────────────────────────────────────────────────────


@streamdl.command()
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
    help="Subtitle decryption key (or set KISSKH_KEY env var).",
)
@click.option(
    "--initialization-vector",
    "-iv",
    default=os.getenv("KISSKH_INITIALIZATION_VECTOR"),
    help="Initialization vector for subtitle decryption (or set KISSKH_INITIALIZATION_VECTOR env var).",
)
@click.option(
    "--stream-key",
    default=os.getenv("KISSKH_STREAM_KEY"),
    help="Pre-generated kkey for stream endpoint (or set KISSKH_STREAM_KEY env var). "
    "Skips browser-based kkey generation.",
)
@click.option(
    "--sub-key",
    default=os.getenv("KISSKH_SUB_KEY"),
    help="Pre-generated kkey for subtitle endpoint (or set KISSKH_SUB_KEY env var). "
    "Skips browser-based kkey generation.",
)
def dl(
    drama_url_or_name: str,
    first: int,
    last: int,
    quality: str,
    sub_langs: list[str],
    output_dir: Path | str,
    decrypt_subtitle: bool,
    key: str,
    initialization_vector: str,
    stream_key: str,
    sub_key: str,
) -> None:
    """Download from any supported source.

    Pass a URL to auto-detect the source, or a search query to search all sources.

    Examples:
        streamdl dl https://kisskh.nl/Drama/Some-Show?id=1234
        streamdl dl https://anime.uniquestream.net/watch/sczeR0vi/...
        streamdl dl "Solo Leveling"
    """
    if validators.url(drama_url_or_name):
        source_cls = detect_source(drama_url_or_name)
        if source_cls and source_cls.name == "kisskh":
            # ── Kisskh-specific path (keeps episode range, subs, kkey) ──
            _dispatch_kisskh(
                drama_url_or_name,
                first,
                last,
                quality,
                sub_langs,
                output_dir,
                decrypt_subtitle,
                key,
                initialization_vector,
                stream_key,
                sub_key,
            )
            return

    # ── Universal dispatch (auto-detect or search) ──
    _dispatch_dl(drama_url_or_name, Path(str(output_dir)), quality)


# ── Get-key command ──────────────────────────────────────────────────────


@streamdl.command(name="get-key")
@click.argument("drama_url")
def get_key(drama_url: str) -> None:
    """Generate kkey tokens for a kisskh drama episode URL.

    Opens a headless browser to extract the authentication keys that
    kisskh requires for stream and subtitle API calls.

    Example:

        streamdl get-key "https://kisskh.nl/Drama/.../Episode-1?id=4608&ep=86192&page=0&pageSize=100"

    After getting the keys, set these env vars to skip the browser next time:

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

    drama_slug = parsed_url.path.split("/")[2].replace("-", "_")

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
    click.echo(f'    streamdl dl "{drama_url}" -o .')
    click.echo("")


if __name__ == "__main__":
    streamdl()
