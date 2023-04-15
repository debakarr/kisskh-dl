# :tv: kisskh-dl

<div align="center">
   <img src="https://i.imgur.com/nhQtOZa.png">
   <br>
   <strong><i>Simple downloaded for https://kisskh.co/</i></strong>
   <br>
   <a href="https://pypi.org/project/kisskh-downloader/">
   <img src="https://img.shields.io/pypi/v/kisskh-downloader?style=for-the-badge">
   </a>
   <img src="https://img.shields.io/github/actions/workflow/status/Dibakarroy1997/kisskh-dl/pull-request.yml?style=for-the-badge">
   <img src="https://img.shields.io/pypi/dm/kisskh-downloader?style=for-the-badge">
</div>

---

👋 Welcome to the kisskh-downloader README! This package is a simple command-line tool for downloading shows from https://kisskh.co/. Here's everything you need to know to get started:

## 💻 Installation

To install kisskh-downloader, simply run the following command:

```console
pip install -U kisskh-downloader
```

## 📚 Usage

After installing the package, you can use the `kisskh dl` command to download shows from the command line.

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

Here are some examples:

### 🔗 Direct download entire series in highest quality available in current folder

```console
kisskh dl "https://kisskh.co/Drama/Island-Season-2?id=7000" -o .
```

![Download all using URL](https://i.imgur.com/cvKYqK3.gif)


### 🔍 Search and download entire series in highest quality available in current folder

```console
kisskh dl "Stranger Things" -o .
1. Stranger Things - Season 4
2. Stranger Things - Season 1
3. Stranger Things - Season 2
4. Stranger Things - Season 3
Please select one from above: 1
```

![Download all using URL](https://i.imgur.com/mLPqjgj.gif)

### ⬇️ Download specific episodes with specific quality

> :exclamation: Note that if the selected quality is not available, it will try to get something lower than that quality. If that also is not available, it will try to get the best quality available.

Downloads episode 4 to 8 of `Alchemy of Souls` in 720p:
```console
kisskh dl "https://kisskh.co/Drama/Alchemy-of-Souls?id=5043" -f 4 -l 8 -q 720p -o .
```

![Download range of episodes](https://i.imgur.com/Q6697pa.gif)

Downloads episode 3 of `A Business Proposal` in 720p:
```console
kisskh dl "https://kisskh.co/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p -o .
```

![Download single episode](https://i.imgur.com/cNlED8m.gif)

You can also dowload single episode by providing the episode URL

```console
kisskh dl "https://kisskh.co/Drama/A-Business-Proposal/Episode-3?id=4608&ep=86439&page=0&pageSize=100" -o .
```

For more options, use the `--help` flag.

---

# 🐞 DEBUG

To enable debugging, use the `-vv` flag while running `kisskh dl`.

```console
kisskh -vv dl "https://kisskh.co/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p
```

---

# :construction: TODO
- [ ] Add ability to export all download link
- [ ] Add ability to open stream in some player
