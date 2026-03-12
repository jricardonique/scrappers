
from __future__ import annotations
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict
from urllib.parse import urljoin
from common.http import ThrottledSession

@dataclass
class Story:
    rank: int; section: str; title: str; url: str

def crawl_section(base_url: str, section: str, limit: int, selectors, session: ThrottledSession) -> List[Story]:
    url = f"{base_url.rstrip('/')}/{section.strip('/')}" if section != 'top-stories' else base_url
    r = session.get(url); r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml')
    cards = soup.select(selectors.article_card) or soup.find_all('article')
    stories: List[Story] = []; rank = 1
    for c in cards:
        h = c.select_one(selectors.headline) or c.find(['h1','h2','h3'])
        a = (h.find('a') if h else None) or c.select_one(selectors.link)
        title = (h.get_text(strip=True) if h else '')
        href = a['href'] if a and a.has_attr('href') else ''
        if href and href.startswith('/'):
            href = urljoin(base_url, href)
        if href and title:
            stories.append(Story(rank, section, title, href)); rank += 1
        if limit and len(stories) >= limit:
            break
    return stories


def run(base_url: str, sections: List[str], limit: int, selectors, session: ThrottledSession) -> List[Dict]:
    rows: List[Dict] = []
    for sec in sections:
        for s in crawl_section(base_url, sec, limit, selectors, session):
            rows.append({'rank': s.rank, 'section': s.section, 'title': s.title, 'url': s.url})
    return rows
