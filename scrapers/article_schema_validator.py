
from __future__ import annotations
from bs4 import BeautifulSoup
from typing import Dict
from urllib.parse import urljoin

FIELDS=['title','author','published','section','lead_image']

def parse_article(html: str, selectors, base_url: str) -> Dict:
    soup=BeautifulSoup(html,'lxml')
    title_tag=soup.find('meta', property='og:title')
    title=title_tag.get('content') if title_tag else (soup.find('title').get_text(strip=True) if soup.find('title') else '')
    author_el=soup.select_one(selectors.author)
    author=author_el.get('content') if author_el and author_el.has_attr('content') else (author_el.get_text(strip=True) if author_el else '')
    time_el=soup.select_one(selectors.time)
    published=time_el.get('content') if time_el and time_el.has_attr('content') else (time_el.get('datetime') if time_el and time_el.has_attr('datetime') else (time_el.get_text(strip=True) if time_el else ''))
    section_el=soup.select_one(selectors.section_tag)
    section=section_el.get('content') if section_el and section_el.has_attr('content') else (section_el.get_text(strip=True) if section_el else '')
    img=soup.find('meta', property='og:image')
    lead_image=img.get('content') if img else ''
    if lead_image and lead_image.startswith('/'):
        lead_image=urljoin(base_url, lead_image)
    return {'title': title,'author': author,'published': published,'section': section,'lead_image': lead_image}

def validate_article(fields: Dict) -> Dict:
    missing=[k for k in FIELDS if not fields.get(k)]
    return {'missing_fields': ', '.join(missing)}
