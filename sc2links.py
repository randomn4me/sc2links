#!/usr/bin/env python3

import datetime
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

URL = 'https://www.sc2links.com/vods/'
SEPARATOR = '+---------+'
CACHE_DIR = Path.home() / '.cache' / 'sc2links'
LAST_FILE = 'last'
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) '
    'Gecko/20100101 Firefox/128.0'
)
REQUEST_TIMEOUT = 15


def year(string):
    parts = string.split()
    if len(parts) < 3:
        raise ValueError(f'unexpected date format: {string!r}')
    return parts[-1]


def ask(aloi):
    items = list(aloi)
    for i, item in enumerate(items):
        print(f'|-{i+1}> {item}')
    print(SEPARATOR)

    valid = set(range(1, len(items) + 1))
    while True:
        raw = input('| which one? > ').strip()
        print(SEPARATOR)
        if raw == 'q':
            sys.exit()
        try:
            choice = int(raw)
        except ValueError:
            print('| please enter a number or "q" to quit')
            continue
        if choice in valid:
            return choice - 1
        print(f'| pick a number between 1 and {len(items)}')


def filter_tournaments(content, base_url=URL):
    soup = BeautifulSoup(content, 'html.parser')
    vodlinks = soup.find_all('div', ['vodlink'])
    voddates = soup.find_all('div', ['voddate'])

    if not vodlinks or not voddates:
        raise RuntimeError(
            'no tournaments found — sc2links.com layout may have changed'
        )
    if len(vodlinks) != len(voddates):
        print(f'[!] {len(vodlinks)} tournaments but {len(voddates)} dates, '
              'years may be wrong')

    by_year = defaultdict(list)
    for l, d in zip(vodlinks, voddates):
        a = l.find('a')
        if a is None or not a.get('href'):
            continue
        try:
            y = year(d.get_text(strip=True))
        except ValueError as e:
            print(f'[!] skipping tournament: {e}')
            continue
        by_year[y].append((l.get_text(strip=True), urljoin(base_url, a['href'])))

    return by_year


def get_year(data):
    years = list(data.keys())
    return years[ask(years)]


def get_tournament(data):
    return data[ask([m for m, _ in data])]


def filter_rounds(content):
    soup = BeautifulSoup(content, 'html.parser')
    return soup.find_all('h3')


def get_round(data):
    return data[ask([r.get_text(strip=True) for r in data])]


def filter_matches(round_tag, base_url):
    matches = []
    for sibling in round_tag.next_siblings:
        name = getattr(sibling, 'name', None)
        if name is None:
            continue
        if name != 'h5':
            break
        matches.append(sibling)

    data = []
    for m in matches:
        a_tag = m.find('a') or m.find_next('a')
        if a_tag is None or not a_tag.get('href'):
            continue
        data.append((a_tag.get_text(strip=True), urljoin(base_url, a_tag['href'])))
    return data


def get_match(data):
    return data[ask([m for m, _ in data])]


def open_mpv(content, page_url):
    soup = BeautifulSoup(content, 'html.parser')
    iframes = soup.find_all('iframe')
    if not iframes:
        print('| no video iframe found on this page')
        print(SEPARATOR)
        return

    src = iframes[0].get('src')
    if not src:
        print('| iframe has no src')
        print(SEPARATOR)
        return
    url = urljoin(page_url, src)

    if 'youtu.be' not in url and 'youtube' not in url:
        print(f'| sorry, can\'t play: {url}')
        print(SEPARATOR)
        return

    if shutil.which('mpv') is None:
        print(f'| mpv not found on PATH, video: {url}')
        print(SEPARATOR)
        return

    if subprocess.call(['mpv', url]) != 0:
        print(f'| mpv failed to play: {url}')
        print(SEPARATOR)


def up_to_date_file(filepath):
    today = datetime.date.today()
    file_date = datetime.date.fromtimestamp(os.path.getmtime(filepath))
    return file_date == today


def cache_filename(url):
    return hashlib.md5(url.encode()).hexdigest()


def load_cache(filename):
    filepath = CACHE_DIR / filename
    if not filepath.exists() or not up_to_date_file(filepath):
        return None
    return filepath.read_text(encoding='utf-8')


def cache(filename, text):
    filepath = CACHE_DIR / filename
    try:
        filepath.write_text(text, encoding='utf-8')
    except OSError as e:
        print(f'[!] error writing cache: {e}')


def write_last_seen(url):
    (CACHE_DIR / LAST_FILE).write_text(url, encoding='utf-8')


def load(url, set_last_seen=False):
    filename = cache_filename(url)

    content = load_cache(filename)
    if content is None:
        print('| loading |')
        print(SEPARATOR)
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as resp:
                charset = resp.headers.get_content_charset() or 'utf-8'
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f'[!] HTTP {e.code} fetching {url}')
        except urllib.error.URLError as e:
            raise SystemExit(f'[!] network error fetching {url}: {e.reason}')
        try:
            content = raw.decode(charset, errors='replace')
        except LookupError:
            content = raw.decode('utf-8', errors='replace')
        cache(filename, content)

    if set_last_seen:
        write_last_seen(url)

    return content


def browser():
    content = load(URL)
    data = filter_tournaments(content)

    chosen_year = get_year(data)
    tournaments = sorted(data[chosen_year])
    tournament = get_tournament(tournaments)

    tournament_url = tournament[1]
    content = load(tournament_url, set_last_seen=True)
    rounds = filter_rounds(content)[1:]
    if not rounds:
        raise RuntimeError(
            'no rounds found — sc2links.com layout may have changed'
        )

    round_tag = get_round(rounds)
    matches = sorted(filter_matches(round_tag, tournament_url))
    if not matches:
        raise RuntimeError('no matches found in selected round')

    match = get_match(matches)
    return load(match[1]), match[1]


def last_tournament():
    last_seen_pointer = CACHE_DIR / LAST_FILE
    if not last_seen_pointer.exists():
        raise SystemExit('| no last-seen tournament — use browser first')

    last_seen = last_seen_pointer.read_text(encoding='utf-8').strip()
    if last_seen.startswith(('http://', 'https://')):
        # load() refetches when the cached copy is stale, so ongoing
        # tournaments pick up new matches
        tournament_url = last_seen
        content = load(tournament_url)
    else:
        # older versions stored the cache filename instead of the url
        last_seen_path = CACHE_DIR / last_seen
        if not last_seen_path.exists():
            raise SystemExit('| cached last-seen tournament missing — use browser')
        tournament_url = URL
        content = last_seen_path.read_text(encoding='utf-8')

    rounds = filter_rounds(content)[1:]
    if not rounds:
        raise RuntimeError('no rounds in cached tournament')

    round_tag = get_round(rounds)
    matches = sorted(filter_matches(round_tag, tournament_url))
    if not matches:
        raise RuntimeError('no matches found in selected round')

    match = get_match(matches)
    return load(match[1]), match[1]


def main_menu():
    options = {
        'last tournament': last_tournament,
        'browser': browser,
    }
    keys = list(options)
    return options[keys[ask(keys)]]


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    action = main_menu()
    video_page, video_page_url = action()
    open_mpv(video_page, video_page_url)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
