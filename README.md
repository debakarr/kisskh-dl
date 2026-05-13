# :tv: kisskh-dl

<div align="center">
   <img src="https://i.imgur.com/nhQtOZa.png">
   <br>
   <strong><i>Simple downloader for https://kisskh.nl/</i></strong>
   <br>
   <a href="https://pypi.org/project/kisskh-downloader/">
   <img src="https://img.shields.io/pypi/v/kisskh-downloader?style=for-the-badge">
   </a>
   <img src="https://img.shields.io/github/actions/workflow/status/debakarr/kisskh-dl/pull-request.yml?style=for-the-badge">
   <img src="https://img.shields.io/pypi/dm/kisskh-downloader?style=for-the-badge">
</div>

---

👋 Welcome to the kisskh-downloader README! This package is a simple command-line tool for downloading shows from https://kisskh.nl/. Here's everything you need to know to get started:

## 💻 Installation

To install kisskh-downloader, simply run the following command:

```console
pip install -U kisskh-downloader
```

### Playwright (optional)

The site now requires an authentication token (`kkey`) for stream and subtitle APIs. You have two options:

**Option A:** Set `KISSKH_STREAM_KEY` and `KISSKH_SUB_KEY` environment variables (see [Authentication section](#-authentication)).

**Option B:** Install Playwright to generate keys automatically:

```console
playwright install chromium
```

---

## 📚 Usage

### `kisskh dl` — Download episodes

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
  -ds, --decrypt-subtitle         Decrypt the downloaded subtitle
  -k, --key TEXT                  Subtitle decryption key (or set KISSKH_KEY
                                  env var).
  -iv, --initialization-vector TEXT
                                  Initialization vector for subtitle
                                  decryption (or set
                                  KISSKH_INITIALIZATION_VECTOR env var).
  --stream-key TEXT               Pre-generated kkey for stream endpoint (or
                                  set KISSKH_STREAM_KEY env var). Skips
                                  browser-based kkey generation.
  --sub-key TEXT                  Pre-generated kkey for subtitle endpoint (or
                                  set KISSKH_SUB_KEY env var). Skips browser-
                                  based kkey generation.
  --help                          Show this message and exit.
```

#### Download entire series

```console
kisskh dl "https://kisskh.nl/Drama/Island-Season-2?id=7000" -o .
```

#### Search and download

```console
kisskh dl "Stranger Things" -o .
```

#### Download specific episodes with specific quality

> :exclamation: Note that if the selected quality is not available, it will try to get something lower than that quality. If that also is not available, it will try to get the best quality available.

Downloads episode 4 to 8 of `Alchemy of Souls` in 720p:

```console
kisskh dl "https://kisskh.nl/Drama/Alchemy-of-Souls?id=5043" -f 4 -l 8 -q 720p -o .
```

Downloads a single episode in 720p:

```console
kisskh dl "https://kisskh.nl/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p -o .
```

You can also download a single episode by providing the episode URL:

```console
kisskh dl "https://kisskh.nl/Drama/A-Business-Proposal/Episode-3?id=4608&ep=86439&page=0&pageSize=100" -o .
```

For more options, use the `--help` flag.

---

### `kisskh get-key` — Generate authentication tokens

The site now requires a `kkey` authentication token. Use `get-key` to generate one from an episode URL:

```console
kisskh get-key "https://kisskh.nl/Drama/A-Business-Proposal/Episode-1?id=4608&ep=86192&page=0&pageSize=100"
```

This opens a headless browser to extract the keys, then prints them:

```
── kkey tokens generated successfully! ──

  Stream key:  <long_hex_string>
  Sub key:     <long_hex_string>

  To use these without a browser next time, set these env vars:

    set KISSKH_STREAM_KEY=<long_hex_string>
    set KISSKH_SUB_KEY=<long_hex_string>

  Then run your download command as usual:
    kisskh dl "https://kisskh.nl/Drama/.../Episode-1?id=1234&ep=5678&page=0&pageSize=100" -o .
```

---

### 📖 Decrypting Subtitles

If you want to decrypt the downloaded subtitles, you need to pass the `--decrypt-subtitle` or `-ds` flag along with a decryption key and initialization vector. Check [#14](https://github.com/debakarr/kisskh-dl/issues/14).

Here is an example of how to pass these parameters from the command line:

```bash
kisskh dl "<drama_url>" --decrypt-subtitle --key "your_key_here" --initialization-vector "your_iv_here"
```

You can also set these parameters as environment variables. If you set the `KISSKH_KEY` and `KISSKH_INITIALIZATION_VECTOR` environment variables, they will be used by default.

Here is an example of how to set these environment variables:

- On Linux/Mac:

```bash
export KISSKH_KEY="your_key_here"
export KISSKH_INITIALIZATION_VECTOR="your_iv_here"
```

- On Windows:

```cmd
set KISSKH_KEY="your_key_here"
set KISSKH_INITIALIZATION_VECTOR="your_iv_here"
```

After setting these environment variables, you can use the `--decrypt-subtitle` flag without passing the key and initialization vector explicitly:

```bash
kisskh dl "Drama Name" --decrypt-subtitle
```

---

## 🔐 Authentication

The site now requires a `kkey` authentication token for stream and subtitle API calls. You have several options:

| Method | How it works |
|---|---|
| **Playwright (automatic)** | Installs Chromium and generates keys on-the-fly per episode. Requires: `playwright install chromium` |
| **Environment variables** | Set `KISSKH_STREAM_KEY` and `KISSKH_SUB_KEY` to skip browser entirely. Generate them once with `kisskh get-key`. |

### All supported environment variables

| Variable | Description | Default |
|---|---|---|
| `KISSKH_BASE_URL` | Site base URL | `https://kisskh.nl` |
| `KISSKH_STREAM_KEY` | Pre-generated kkey for stream endpoint | — |
| `KISSKH_SUB_KEY` | Pre-generated kkey for subtitle endpoint | — |
| `KISSKH_KEY` | Subtitle decryption key | — |
| `KISSKH_INITIALIZATION_VECTOR` | Subtitle decryption IV | — |

---

## 🐞 DEBUG

To enable debugging, use the `-vv` flag while running `kisskh dl`.

```console
kisskh -vv dl "https://kisskh.nl/Drama/A-Business-Proposal?id=4608" -f 3 -l 3 -q 720p
```
