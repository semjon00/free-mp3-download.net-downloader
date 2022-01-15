# This script looks recursively into the MUSIC_LIBRARY folder, searches the names of the .mp3 files present in that
# folder on free-mp3-download.net and downloads replacement .mp3 or .flac files into another directory.
# Additionally, it changes the modification dates of the new files to such of the old files.
# The replacements may not be suitable, so user needs to manually delete wrong files.
# To avoid hassle of re-downloading wrong files, user may add names of those songs to explicit_ignore.txt file.

import base64
import time
import requests
from urllib.parse import quote
import os

ASK_BEFORE_DOWNLOADING = False
MUSIC_LIBRARY = "D:\\Music"  # no trailing sep
DOWNLOAD_TO = "C:\\Users\\semjon\\PycharmProjects\\flac_upgrader\\Data"  # no trailing sep
DOWNLOAD_FORMAT = 'flac'  # mp3 or flac
_2CAPTCHA_API_KEY = open('2captcha_api_key', 'r').read()  # You need to have a 2captcha account to have this
IGNORED_FOLDERS_PREFIXES = ['[']


# Changes modified date of a file
def timestamp(relpath, name, modified):
    try:
        path = os.path.join(DOWNLOAD_TO, 'New', relpath, name + '.' + DOWNLOAD_FORMAT)
        stinfo = os.stat(path)
        os.utime(path, (stinfo.st_atime, modified))
    except:
        print(f'❗ no_timestamp: {relpath} {name}')


# Crawls music library, extracts rel-path, name and modified
# Only seeks .mp3 format
def crawl():
    # Use this to prioritize by folders, words, artists, dates of modification... The possibilities are endless!
    def sort_function(obj):
        return -obj[2]

    if not os.path.exists(DOWNLOAD_TO):
        os.makedirs(DOWNLOAD_TO)
    ignore = set()
    for ignore_filename in ['ignore.txt', 'explicit_ignore.txt']:
        ignore_path = os.path.join(DOWNLOAD_TO, ignore_filename)
        if not os.path.exists(ignore_path):
            open(ignore_path, 'x', encoding="utf-8").write('# Titles that are excluded from search and download\n')
        ignore = ignore.union(set(open(ignore_path, 'r', encoding="utf-8").read().split('\n')))
    to_update = []
    for root, dirnames, filenames in os.walk(MUSIC_LIBRARY):
        relpath = root[len(MUSIC_LIBRARY + os.path.sep):]
        if any([relpath.startswith(x) for x in IGNORED_FOLDERS_PREFIXES]):
            continue
        for filename in filenames:
            if not filename.endswith('.mp3'):
                continue  # not an .mp3 file
            if filename[:-len('.mp3')] in ignore:
                continue  # this one is ignored
            if os.path.exists(os.path.join(DOWNLOAD_TO, 'New', relpath, filename[:-len('.mp3')] + '.' + DOWNLOAD_FORMAT)):
                continue  # already downloaded
            modified = os.path.getmtime(os.path.join(root, filename))
            to_update += [(relpath, filename[:-len('.mp3')], modified)]
    to_update.sort(key=sort_function)
    to_update = [x for x in to_update if sort_function(x) < 1e25]
    print(f'🕷 Found {len(to_update)} files to update')
    return to_update


# Makes a search using
def search(name):
    # Pretty reasonable precision decider
    # Result that either contains all words, or only some words and no extra words
    # Special symbols replaced with spaces
    # Some words are special, they must match
    def matches(ours, theirs):
        def prepare(name):
            skipped = ['feat', 'ft']
            name = ''.join(ch if ch.isalnum() else ' ' for ch in name)
            name = name.casefold()
            name = set([x for x in name.split(' ') if len(x) > 0 and x not in skipped])
            return name
        explicit = ['live', 'remix', 'vip', 'radio', 'karaoke']
        ours = prepare(ours)
        theirs = prepare(theirs)
        fits = ours.union(theirs) == theirs or ours.union(theirs) == ours
        for ex in explicit:
            if (ex in ours) != (ex in theirs):
                fits = False
        return fits

    def append_ignore(name):
        open(os.path.join(DOWNLOAD_TO, 'ignore.txt'), 'a+', encoding="utf-8").write(name + '\n')
    url = f'https://api.deezer.com/search?output=json&q={name}'
    r = requests.get(url, allow_redirects=True)
    r = r.json()

    if 'data' not in r or 'total' not in r or r['total'] <= 0:
        print(f"😕 {name} ~=~ (/)")
        append_ignore(name)
        return -1

    for i in range(len(r['data'])):
        theirs = f"{r['data'][i]['artist']['name']} {r['data'][i]['title']}"
        if matches(name, theirs):
            if r['data'][i]['duration'] > 8*60:
                continue  # no, that's too much of data
            print(f"🔍 {name} ~=~ {r['data'][i]['artist']['name']} - {r['data'][i]['title']}")
            return r['data'][i]['id']
    print(f"🤔 {name} ~=~ ???, first: {r['data'][0]['artist']['name']} - {r['data'][0]['title']}")
    append_ignore(name)
    return -2


# Creates and solves captcha
def captcha(referer):
    try:
        print(f'ℭ New captcha needed')
        captcha_sitekey = '6LfzIW4UAAAAAM_JBVmQuuOAw4QEA1MfXVZuiO2A'
        form = {"method": "userrecaptcha",
                "googlekey": captcha_sitekey,
                "key": _2CAPTCHA_API_KEY,
                "pageurl": referer,
                "json": 1}

        response = requests.post('https://2captcha.com/in.php', data=form)
        request_id = response.json()['request']

        url = f"https://2captcha.com/res.php?key={_2CAPTCHA_API_KEY}&action=get&id={request_id}&json=1"
        while True:
            res = requests.get(url)
            if res.json()['status'] == 0:
                time.sleep(2)
            else:
                print(f'ℭ Obtained a new captcha')
                return res.json()['request']
    except:
        return captcha(referer)


# Downloads a flac or mp3 from free-mp3-download.net, by deezer id
captcha_response = ''
def download(song_id, name, relpath):
    global captcha_response
    encoded_search_querry = base64.b64encode(quote(name, safe="/*()'!").encode('utf-8'), altchars=None).decode('utf-8')
    referer = f"https://free-mp3-download.net/download.php?id={song_id}&q={encoded_search_querry}"
    if captcha_response == '':
        captcha_response = captcha(referer)

    # Downloading file
    phpsessid = 'ib2a2vhm0dajn0m11ng1451bdr'
    url = f'https://free-mp3-download.net/dl.php?i={song_id}&f={DOWNLOAD_FORMAT}&h={captcha_response}'
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Cookie": f"PHPSESSID={phpsessid}",
        "Host": "free-mp3-download.net",
        "Pragma": "no-cache",
        "Referer": referer,
        "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="97", "Chromium";v="97"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Sec-Fetch-Dest": "iframe",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/97.0.4692.71 Safari/537.36"}
    r = None
    try:
        r = requests.get(url, headers=headers, allow_redirects=True)
    except:
        print(f'❗ Connection broke')
        return download(song_id, name, relpath)
    if len(r.content) < 50_000:
        print(f'❗ wrong output: {song_id}, {name}, {r.content}')
        if 'Incorrect captcha' in r.content.decode('utf-8'):
            captcha_response = ''
            return download(song_id, name, relpath)
        return None
    return r.content


# Saves the binary to a file
def save_file(content, relpath, name):
    if content is None:
        return
    directory = os.path.join(DOWNLOAD_TO, 'New', relpath)
    if not os.path.exists(directory):
        os.makedirs(directory)
    open(os.path.join(directory, name + '.' + DOWNLOAD_FORMAT), 'wb').write(content)
    print(f'💾 {name}.{DOWNLOAD_FORMAT}, {len(content)//1024} KB')


if __name__ == '__main__':
    for relpath, name, modified in crawl():
        deezer_id = search(name)
        if deezer_id >= 0:
            content = download(deezer_id, name, relpath)
            save_file(content, relpath, name)
            timestamp(relpath, name, modified)
        time.sleep(0.5)
