# :tv: streamdl

<div align="center">
   <img src="https://i.imgur.com/nhQtOZa.png">
   <br>
   <strong><i>Multi-source streaming downloader — kisskh, AnimeStream, and more</i></strong>
   <br>
   <a href="https://pypi.org/project/streamdl/">
   <img src="https://img.shields.io/pypi/v/streamdl?style=for-the-badge">
   </a>
   <img src="https://img.shields.io/github/actions/workflow/status/debakarr/kisskh-dl/pull-request.yml?style=for-the-badge">
   <img src="https://img.shields.io/pypi/dm/streamdl?style=for-the-badge">
</div>

---

👋 Welcome to **streamdl**! A command-line tool for downloading shows, movies, and anime from multiple streaming sources.

## 🔌 Supported Sources

| Source | Type | Status |
|---|---|---|
| [kisskh.nl](https://kisskh.nl/) | Asian Dramas | ✅ Working |
| [AnimeStream](https://anime.uniquestream.net/) | Anime | ✅ Working |

## 💻 Installation

```console
pip install -U streamdl
```

### Playwright (for kisskh)

The kisskh source requires Playwright to generate authentication tokens:

```console
playwright install chromium
```

Alternatively, you can set `KISSKH_STREAM_KEY` and `KISSKH_SUB_KEY` environment variables to skip the browser (see [Authentication](#-authentication)).

---

## 📚 Usage

### `streamdl dl` — Download from kisskh

```console
streamdl dl --help
```

#### Download a drama series

```console
streamdl dl "https://kisskh.nl/Drama/Island-Season-2?id=7000" -o .
```

#### Search and download

```console
streamdl dl "Stranger Things" -o .
```

#### Download specific episodes

```console
streamdl dl "https://kisskh.nl/Drama/Alchemy-of-Souls?id=5043" -f 4 -l 8 -q 720p -o .
```

---

### `streamdl anime dl` — Download from AnimeStream

AnimeStream has a clean, open API — no authentication needed.

Download an episode by content ID (found in the watch URL):
```console
streamdl anime dl sczeR0vi -o .
```

Search for anime:
```console
streamdl anime search "Solo Leveling"
```

List popular:
```console
streamdl anime popular
```

---

### `streamdl get-key` — Generate kisskh auth tokens

```console
streamdl get-key "https://kisskh.nl/Drama/.../Episode-1?id=4608&ep=86192&page=0&pageSize=100"
```

---

### 📖 Decrypting Subtitles

```bash
streamdl dl "<drama_url>" --decrypt-subtitle --key "your_key_here" --initialization-vector "your_iv_here"
```

Environment variables `KISSKH_KEY` and `KISSKH_INITIALIZATION_VECTOR` can be used instead.

---

## 🔐 Authentication

### kisskh (kkey tokens)

The kisskh site requires a `kkey` authentication token. You have two options:

**Automatic** — Playwright generates keys on-the-fly per episode (requires `playwright install chromium`)

**Environment variables** — Set these to skip the browser entirely (generate once with `streamdl get-key`):

| Variable | Description |
|---|---|
| `KISSKH_BASE_URL` | Site base URL (default: `https://kisskh.nl`) |
| `KISSKH_STREAM_KEY` | Pre-generated stream kkey |
| `KISSKH_SUB_KEY` | Pre-generated subtitle kkey |
| `KISSKH_KEY` | Subtitle decryption key |
| `KISSKH_INITIALIZATION_VECTOR` | Subtitle decryption IV |

### AnimeStream

No authentication required.

---

## 🐞 Debug

```console
streamdl -vv dl "https://kisskh.nl/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p
```
