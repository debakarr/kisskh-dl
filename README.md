# kisskh-dl

Simple downloaded for https://kisskh.me/

---

## Installation
```console
pip install kisskh-downloader
```

---

## Usage

> **NOTE:** As of now the video files downloaded are in [.ts](https://en.wikipedia.org/wiki/MPEG_transport_stream) format. You can still use players like [VLC](https://www.videolan.org/) to play the video.

### Direct download entire series in highest quality available

```console
kisskh dl "https://kisskh.me/Drama/Money-Heist--Korea---Joint-Economic-Area?id=5044"
```

### Search and download entire series in highest quality available

```console
kisskh dl "Stranger Things"
1. Stranger Things - Season 4
2. Stranger Things - Season 1
3. Stranger Things - Season 2
4. Stranger Things - Season 3
Please select one from above: 1
```

### Download specific episodes with specific quality

Downloads episode 4 to 8 of `Alchemy of Souls` in 720p:
```console
kisskh dl "https://kisskh.me/Drama/Alchemy-of-Souls?id=5043" -e 4:8 -q 720p
```

Downloads episode 3 of `A Business Proposal` in 720p:
```console
kisskh dl "https://kisskh.me/Drama/A-Business-Proposal?id=4608" -e 3 -q 720p
```

---

# TODO
- [ ] Add ability to export video in other format using ffmpeg
- [ ] Add unit test
- [ ] Handle Ctrl + C signal in terminal
- [ ] Throw appropriate exception or handles it somehow
    - [ ] In valid URL pass
    - [ ] Video file not present
- [ ] Add option to download subtitles
