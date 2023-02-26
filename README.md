# :tv: kisskh-dl

Simple downloaded for https://kisskh.me/

---

## :inbox_tray: Installation

```console
pip install -U kisskh-downloader
```

## :books: Usage

```console
kisskh dl --help
Usage: kisskh dl [OPTIONS] DRAMA_URL_OR_NAME

Options:
  -f, --first INTEGER             Starting episode number.
  -l, --last INTEGER              Ending episode number.
  -q, --quality [360p|480p|540p|720p|1080p]
                                  Quality of the video to be downloaded.
  -s, --sub-langs TEXT            Languages of the subtitles to download.
  -o, --output-dir TEXT           Output directory where downloaded files will
                                  be store.
  --help                          Show this message and exit.
```

### :high_brightness: Direct download entire series in highest quality available

```console
kisskh dl "https://kisskh.me/Drama/Money-Heist--Korea---Joint-Economic-Area?id=5044"
```

### :mag_right: Search and download entire series in highest quality available

```console
kisskh dl "Stranger Things"
1. Stranger Things - Season 4
2. Stranger Things - Season 1
3. Stranger Things - Season 2
4. Stranger Things - Season 3
Please select one from above: 1
```

### :arrow_forward: Download specific episodes with specific quality

> :exclamation: Note that if the selected quality is not available, it will try to get something lower than that quality. If that also is not available, it will try to get the best quality available.

Downloads episode 4 to 8 of `Alchemy of Souls` in 720p:
```console
kisskh dl "https://kisskh.me/Drama/Alchemy-of-Souls?id=5043" -f 4 -l 8 -q 720p
```

Downloads episode 3 of `A Business Proposal` in 720p:
```console
kisskh dl "https://kisskh.me/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p
```

---

# :beetle: DEBUG

Use -vv flag while running `kisskh dl`
```console
kisskh -vv dl "https://kisskh.me/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p
```

---

# :construction: TODO
- [ ] Add unit test
- [ ] Add ability to export all download link
- [ ] Add ability to open stream in some player
