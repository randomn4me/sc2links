# sc2links

Small terminal browser for [sc2links.com](https://www.sc2links.com/vods/) VODs.
Lets you pick a year → tournament → round → match and opens the embedded video
in [mpv](https://mpv.io/).

## Requirements

- Python 3.8+
- [mpv](https://mpv.io/) on `PATH`
- [yt-dlp](https://github.com/yt-dlp/yt-dlp), which mpv uses to play YouTube
- `beautifulsoup4` (see `requirements.txt`)

## Install

```sh
pip install -r requirements.txt
```

## Usage

```sh
./sc2links.py
```

Pick **browser** to navigate from the index, or **last tournament** to jump
back into the most recently visited tournament. Type `q` at any prompt to
quit.

## Cache

Pages are cached under `~/.cache/sc2links/`. Entries are reused if they were
written today; otherwise they are refetched. The pointer file `last` records
the URL of the last tournament you opened so `last tournament` can resume;
that page is refetched like any other once its cached copy is a day old.

## Notes

Only YouTube-embedded VODs play; other embeds are reported but not opened.
