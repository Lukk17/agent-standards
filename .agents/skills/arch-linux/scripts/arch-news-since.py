#!/usr/bin/env python3
"""Print Arch Linux News items published since a date, read-only.

Usage: arch-news-since.py [YYYY-MM-DD]
Without an argument the date of the last "starting full system upgrade"
line in /var/log/pacman.log is used. Exit status 0 on success, 2 when the
feed or the date could not be read.
"""
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

FEED = "https://archlinux.org/feeds/news/"
PACMAN_LOG = "/var/log/pacman.log"
ACTION = re.compile(r"manual intervention|requires|breaking|incident", re.IGNORECASE)


def last_upgrade_day() -> str | None:
    day = None
    try:
        with open(PACMAN_LOG, errors="replace") as log:
            for line in log:
                if "starting full system upgrade" in line:
                    day = line[1:11]
    except OSError as error:
        print(f"could not read {PACMAN_LOG}: {error}", file=sys.stderr)
    return day


def main() -> int:
    since = sys.argv[1] if len(sys.argv) > 1 else last_upgrade_day()
    if since is None:
        print("no full system upgrade found, pass a date as YYYY-MM-DD", file=sys.stderr)
        return 2
    request = urllib.request.Request(FEED, headers={"User-Agent": "arch-news-since/1"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            root = ET.parse(response).getroot()
    except Exception as error:
        print(f"could not read the feed: {error}", file=sys.stderr)
        return 2
    print(f"news since {since}")
    for item in root.iter("item"):
        day = parsedate_to_datetime(item.findtext("pubDate")).date().isoformat()
        if day < since:
            continue
        title = html.unescape(item.findtext("title"))
        label = "ACTION" if ACTION.search(title) else "info"
        print(f"{day} [{label}] {title}\n    {item.findtext('link')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
