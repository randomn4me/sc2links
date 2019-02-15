#!/usr/bin/python3

import urllib.request
import operator
import subprocess
import os
import hashlib
import datetime

from collections import defaultdict
from bs4 import BeautifulSoup

URL='https://www.sc2links.com/vods/'
SEPARATOR='+---------+'
CACHE_DIR=os.path.join(os.getenv('HOME'), '.cache', 'sc2links')

def year(string):
    m, d, y = string.split()
    return y


def ask(aloi):
    for i, item in enumerate(aloi):
        print(f'|-{i}> {item}')
    print(SEPARATOR)

    answer = -1
    while answer not in list(range(len(aloi))):
        answer = input('| which one? > ')
        print(SEPARATOR)
        try:
            answer = int(answer)
        except:
            pass

    return answer


def filter_tournaments(content):
    soup = BeautifulSoup(content, 'html.parser')
    vodlinks = soup.find_all('div', ['vodlink'])
    voddates = soup.find_all('div', ['voddate'])

    all_vods = zip(vodlinks, voddates)

    by_year = defaultdict(list)

    for l, d in all_vods:
        name = l.text
        link = l.a['href']
        y = year(d.text)

        entry = (name, link)

        by_year[y].append(entry)

    return by_year


def get_year(data):
    return list(data.keys())[ask(data.keys())]


def get_tournament(data, year):
    return data[ask([m for m, l in data])]


def filter_rounds(content):
    soup = BeautifulSoup(content, 'html.parser')
    matches = soup.find_all('h3')
    return matches


def get_round(data):
    return data[ask([r.text for r in data])]


def filter_matches(round_tag):
    match_tag = round_tag.next_sibling
    matches = list()
    while match_tag and match_tag.name == 'h5':
        matches.append(match_tag)
        match_tag = match_tag.next_sibling

    data = list()
    for m in matches:
        a_tag = m.find_next('a')
        data.append((a_tag.text, a_tag['href']))

    return data


def get_match(data):
    return data[ask([m for m, l in data])]


def open_mpv(content):
    soup = BeautifulSoup(content, 'html.parser')
    iframe = soup.find_all('iframe')
    url = iframe[0]['src']

    if 'youtu.be' in url or 'youtube' in url:
        subprocess.call(['mpv', iframe[0]['src']])
    else:
        print('| sorry, can\'t play')
        print(SEPARATOR)


def up_to_date_file(filepath):
    today = datetime.date.today()
    modification_time = os.path.getmtime(filepath)
    file_date = datetime.date.fromtimestamp(modification_time)

    return file_date == today


def load_cache(filename):
    cached_files = os.listdir(CACHE_DIR)

    if filename in cached_files:
        filepath = os.path.join(CACHE_DIR, filename)
        if not up_to_date_file(filepath):
            return

        with open(filepath, 'r') as f:
            content = f.read()
        return content

    return


def cache(filename, data):
    filepath = os.path.join(CACHE_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            f.write(data.decode())
    except:
        print('[!] Error writing to cache')


def load(url):
    filename = hashlib.md5(url.encode()).hexdigest()

    content = load_cache(filename)
    if not content:
        print("""| loading |
+---------+ """)
        content = urllib.request.urlopen(url).read()
        cache(filename, content)
        return content

    return content

def main():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    content = load(URL)

    data = filter_tournaments(content)

    year = get_year(data)

    data = sorted(data[str(year)])
    match = get_tournament(data, year)

    content = load(match[1])
    data = filter_rounds(content)[1:]

    round_tag = get_round(data)
    data = filter_matches(round_tag)

    match = get_match(data)

    content = load(match[1])
    open_mpv(content)

if __name__ == '__main__':
    main()
