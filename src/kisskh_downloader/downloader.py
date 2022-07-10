from pathlib import Path
import queue
import re
from threading import Thread
import m3u8
from playwright.sync_api import sync_playwright
import requests
from tqdm import tqdm


class Mu38Extracter:
    def _append_mu38_urls(self, response, m3u8_urls):
        if ".m3u8" in (m3u8_url := response.get("response").get("url")):
            m3u8_urls.append(m3u8_url)

    def _page_init_hook(self, page, m3u8_urls):
        client = page.context.new_cdp_session(page)
        client.send("Network.enable")
        client.on(
            "Network.responseReceived",
            lambda response: self._append_mu38_urls(response, m3u8_urls),
        )

    def extract(self, url: str):
        m3u8_urls = []
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            page = browser.new_page()
            self._page_init_hook(page, m3u8_urls)
            print(f"Parsing {url}...")
            page.goto(url, wait_until="networkidle", timeout=60000)
            browser.close()
        return m3u8_urls


class Worker(Thread):
    def __init__(self, request_queue, session, tqdm_progress_bar=None):
        Thread.__init__(self)
        self.queue = request_queue
        self.session = session
        self.responses = []
        self.progress_bar = tqdm_progress_bar

    def run(self):
        while True:
            content = self.queue.get()
            if content == "":
                break
            index, url = content
            response = self.session.get(url)
            self.responses.append((index, response.content))
            if self.progress_bar:
                self.progress_bar.update(1)
            self.queue.task_done()


class Mu3u8Selector:
    def __init__(self, url: str):
        self.url = url
        self.session = None

    def _get_session(self):
        if self.session is None:
            self.session = requests.Session()
        return self.session

    def get_segments_mapping(self):
        session = self._get_session()
        response = session.get(self.url)
        m3u8_master = m3u8.loads(response.text)
        if not m3u8_master.data["is_variant"]:
            # For two kinds of URL:
            #     https://hls04.daduymeavea.online/hls04/a-business-proposal-2022-episode-1-v1/720.m3u8
            #     https://hls04.daduymeavea.online/hls04/e21c5e3a133ef02ef786d0c62ba7ca08/ep.14.v0.1622327945.720.m3u8
            # split in eihter '.' or '/'
            split_url = re.split(r"\.|/", self.url)
            key = split_url[split_url.index("m3u8") - 1]
            return {key: [segment["uri"] for segment in m3u8_master.data["segments"]]}

        m3u8_playlists = dict()

        for m3u8_playlist in m3u8_master.data["playlists"]:
            key = m3u8_playlist["stream_info"]["resolution"]
            response = session.get(m3u8_playlist["uri"])
            m3u8_master = m3u8.loads(response.text)
            m3u8_playlists[key] = [
                segment["uri"] for segment in m3u8_master.data["segments"]
            ]

        return m3u8_playlists

    def download_playlist_segments(
        self,
        outfile: Path | str,
        playlist_segments: list[str],
        number_of_workers: int = 16,
    ):
        session = self._get_session()
        segments_dict = dict(zip(range(len(playlist_segments)), playlist_segments))
        q = queue.Queue()
        for segment in segments_dict.items():
            q.put(segment)
        for _ in range(number_of_workers):
            q.put("")

        with tqdm(
            total=len(segments_dict),
            desc=f"Downloading content for {Path(outfile).name}",
        ) as progress_bar:
            workers = []
            for _ in range(number_of_workers):
                worker = Worker(q, session, progress_bar)
                worker.daemon = True
                worker.start()
                workers.append(worker)

            for worker in workers:
                worker.join()

        responses = []
        for worker in workers:
            responses.extend(worker.responses)

        Path(outfile).parent.mkdir(parents=True, exist_ok=True)
        with open(outfile, "wb") as file:
            responses_dict = dict(responses)
            for i in tqdm(
                range(len(responses_dict)),
                desc=f"Writing content for {Path(outfile).name}...",
            ):
                file.write(responses_dict[i])
