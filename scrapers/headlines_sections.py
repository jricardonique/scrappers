
from __future__ import annotations
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict
from urllib.parse import urljoin
import requests
from common.http import ThrottledSession

SECTION_OVERRIDES: Dict[str, str] = {
    "page-six": "https://pagesix.com",
    "trending": "https://nypost.com/tag/trending/",
}

@dataclass
class Story:
    rank: int
    section: str
    title: str
    url: str

def _section_url(base_url: str, section: str) -> str:
    if section in SECTION_OVERRIDES:
        return SECTION_OVERRIDES[section].rstrip("/")
    return f"{base_url.rstrip('/')}/{section.strip('/')}"

def crawl_section(base_url: str, section: str, limit: int, selectors, session: ThrottledSession) -> List[Story]:
    url = _section_url(base_url, section)
    try:
        r = session.get(url); r.raise_for_status()
    except requests.HTTPError:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    cards = soup.select(selectors.article_card) or soup.find_all('article')
    stories: List[Story] = []
    rank = 1
    for c in cards:
        h = c.select_one(selectors.headline) or c.find(['h1','h2','h3'])
        a = (h.find('a') if h else None) or c.select_one(selectors.link)
        title = (h.get_text(strip=True) if h else '')
        href = a['href'] if a and a.has_attr('href') else ''
        if href and href.startswith('/'):
            href = urljoin(url, href)
        if href and title:
            stories.append(Story(rank, section, title, href))
            rank += 1
        if limit and len(stories) >= limit:
            break
    return stories

def run(base_url: str, sections: List[str], limit: int, selectors, session: ThrottledSession) -> Dict:
    by_section: Dict[str, List[Dict]] = {}
    for sec in sections:
        rows = []
        for s in crawl_section(base_url, sec, limit, selectors, session):
            rows.append({'rank': s.rank, 'section': s.section, 'title': s.title, 'url': s.url})
        by_section[sec] = rows
    return { 'sections': sections, 'by_section': by_section, 'overrides': SECTION_OVERRIDES }
