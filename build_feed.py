#!/usr/bin/env python3
"""
Generates/updates a podcast RSS feed for "De Nationale Nieuwsquiz"
(aired daily on NPO Radio 1, during Spraakmakers).

It scrapes https://www.nporadio1.nl/programmas/spraakmakers/fragmenten
for fragments whose title/URL mentions "Nationale Nieuwsquiz", tries to
resolve the playable audio URL for each new fragment, and writes/updates
docs/feed.xml (a standard RSS 2.0 + iTunes podcast feed) plus
docs/state.json (bookkeeping of which fragments are already in the feed).

This is a best-effort scraper for personal use: NPO does not publish this
segment as an official podcast, so there is no guaranteed stable API. If
NPO changes their site layout, the audio-URL extraction in find_audio_url()
may need to be adjusted -- check the workflow logs for
"no audio URL found" warnings.

Run from the repo root:
    python build_feed.py

Environment variables (all optional):
    FEED_BASE_URL   Public base URL where docs/ is served (GitHub Pages),
                     e.g. https://<username>.github.io/<repo>
                     Used to build the <link>/<atom:link> tags correctly.
    MAX_PAGES       How many "fragmenten" listing pages to scan for new
                     episodes on a run (default 5).
    MAX_ITEMS       Max number of episodes kept in the feed (default 60).
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
from xml.sax.saxutils import escape

import requests

BASE = "https://www.nporadio1.nl"
LIST_URL = BASE + "/programmas/spraakmakers/fragmenten"
DOCS_DIR = "docs"
FEED_PATH = os.path.join(DOCS_DIR, "feed.xml")
STATE_PATH = os.path.join(DOCS_DIR, "state.json")

MAX_PAGES = int(os.environ.get("MAX_PAGES", "5"))
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "60"))
FEED_BASE_URL = os.environ.get("FEED_BASE_URL", "").rstrip("/")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NieuwsquizFeedBot/1.0; "
        "personal single-user RSS builder)"
    )
}

AUDIO_URL_RE = re.compile(
    r'https?://[^\s"\'<>]+\.(?:mp3|m4a|aac)(?:\?[^\s"\'<>]*)?', re.IGNORECASE
)

STREAM_KEY_RE = re.compile(
    r'"(?:audioUrl|streamUrl|mediaUrl|url)"\s*:\s*'
    r'"([^"]+\.(?:mp3|m4a|aac)[^"]*)"',
    re.IGNORECASE,
)

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)

FRAGMENT_HREF_RE = re.compile(r'href="(/fragmenten/spraakmakers/[^"]+)"')

TITLE_TAG_RE = re.compile(r"<title>([^<]+)</title>")
DESCRIPTION_META_RE = re.compile(r'<meta name="description" content="([^"]*)"')
DATE_IN_URL_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=30, **kw)
    r.raise_for_status()
    return r.text


def find_fragment_links(html):
    """Pull relative fragment URLs out of a listing page."""
    return FRAGMENT_HREF_RE.findall(html)


def collect_candidate_fragments():
    """Scan the fragmenten listing pages for Nieuwsquiz episodes."""
    found = {}
    for page in range(1, MAX_PAGES + 1):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        try:
            html = get(url)
        except requests.RequestException as e:
            print(f"WARN: could not fetch {url}: {e}", file=sys.stderr)
            break
        hrefs = find_fragment_links(html)
        if not hrefs:
            break
        for href in hrefs:
            if "nationale-nieuwsquiz" in href.lower():
                found[urljoin(BASE, href)] = True
        time.sleep(0.5)
    return list(found.keys())


def extract_next_data(html):
    m = NEXT_DATA_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def find_audio_url(html):
    """Best-effort extraction of the playable audio URL from a fragment page."""
    m = AUDIO_URL_RE.search(html)
    if m:
        return m.group(0)

    data = extract_next_data(html)
    if data:
        blob = json.dumps(data)
        m = STREAM_KEY_RE.search(blob)
        if m:
            return m.group(1)
        m = AUDIO_URL_RE.search(blob)
        if m:
            return m.group(0)

    return None


def parse_fragment(url):
    html = get(url)

    title_m = TITLE_TAG_RE.search(html)
    title = (
        title_m.group(1).replace("| NPO Radio 1", "").strip()
        if title_m
        else url
    )

    desc_m = DESCRIPTION_META_RE.search(html)
    description = desc_m.group(1).strip() if desc_m else ""

    date_m = DATE_IN_URL_RE.search(url)
    if date_m:
        pub_date = datetime(
            int(date_m.group(1)),
            int(date_m.group(2)),
            int(date_m.group(3)),
            11,
            30,
            tzinfo=timezone.utc,
        )
    else:
        pub_date = datetime.now(timezone.utc)

    audio_url = find_audio_url(html)

    return {
        "id": url,
        "title": title,
        "description": description,
        "url": url,
        "audio_url": audio_url,
        "pub_date": pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000"),
    }


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"episodes": []}


def save_state(state):
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def build_rss(episodes):
    self_link = f"{FEED_BASE_URL}/feed.xml" if FEED_BASE_URL else "feed.xml"
    site_link = f"{FEED_BASE_URL}/" if FEED_BASE_URL else BASE

    items = []
    for ep in episodes:
        if not ep.get("audio_url"):
            continue
        items.append(
            f"""
    <item>
      <title>{escape(ep['title'])}</title>
      <link>{escape(ep['url'])}</link>
      <guid isPermaLink="false">{escape(ep['id'])}</guid>
      <pubDate>{ep['pub_date']}</pubDate>
      <description>{escape(ep['description'])}</description>
      <enclosure url="{escape(ep['audio_url'])}" type="audio/mpeg" />
    </item>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>De Nationale Nieuwsquiz</title>
    <link>{escape(site_link)}</link>
    <atom:link href="{escape(self_link)}" rel="self" type="application/rss+xml" />
    <description>Dagelijkse aflevering van De Nationale Nieuwsquiz uit Spraakmakers (NPO Radio 1), automatisch verzameld voor persoonlijk gebruik.</description>
    <language>nl-nl</language>
    <itunes:author>NPO Radio 1 / KRO-NCRV</itunes:author>
    <itunes:explicit>no</itunes:explicit>
    {''.join(items)}
  </channel>
</rss>
"""


def main():
    state = load_state()
    known_ids = {e["id"] for e in state["episodes"]}

    candidates = collect_candidate_fragments()
    print(f"Found {len(candidates)} Nieuwsquiz fragment URL(s) on the listing pages.")

    new_count = 0
    for url in candidates:
        if url in known_ids:
            continue
        try:
            ep = parse_fragment(url)
        except requests.RequestException as e:
            print(f"WARN: failed to parse {url}: {e}", file=sys.stderr)
            continue
        if not ep["audio_url"]:
            print(
                f"WARN: no audio URL found for {url} -- skipping for now.",
                file=sys.stderr,
            )
            continue
        state["episodes"].append(ep)
        known_ids.add(url)
        new_count += 1
        time.sleep(0.5)

    state["episodes"].sort(key=lambda e: e["pub_date"], reverse=True)
    state["episodes"] = state["episodes"][:MAX_ITEMS]

    save_state(state)

    rss = build_rss(state["episodes"])
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        f.write(rss)

    print(
        f"Added {new_count} new episode(s). Feed now has "
        f"{len(state['episodes'])} episode(s) with audio."
    )


if __name__ == "__main__":
    main()
