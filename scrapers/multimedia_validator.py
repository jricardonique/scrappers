
from __future__ import annotations
from bs4 import BeautifulSoup
from typing import List, Dict
from urllib.parse import urljoin
import time
from common.http import ThrottledSession


def extract_media_urls(html: str, base_url: str, selectors) -> List[str]:
    soup = BeautifulSoup(html, 'lxml'); urls: List[str] = []
    for img in soup.select(selectors.images):
        src = img.get('src') or img.get('data-src')
        if src: urls.append(urljoin(base_url, src))
    for v in soup.select(selectors.videos):
        src = v.get('src') or v.get('data-src') or v.get('data-video-src')
        if src: urls.append(urljoin(base_url, src))
    # dedupe preserve order
    seen=set(); out=[]
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def validate_url(session: ThrottledSession, url: str) -> Dict:
    row={'url': url, 'status': None, 'ok': False, 'elapsed_ms': None, 'size_bytes': None}
    t0=time.time()
    try:
        resp=session.get(url, stream=True)
        row['status']=resp.status_code; row['ok']=resp.ok
        row['elapsed_ms']=round((time.time()-t0)*1000,1)
        size=0
        for chunk in resp.iter_content(8192):
            if not chunk: continue
            size+=len(chunk)
            if size>5_000_000: break
        row['size_bytes']=size; resp.close()
    except Exception as e:
        row['status']=str(e); row['ok']=False
    return row


def run(base_url: str, article_urls: List[str], selectors, session: ThrottledSession) -> Dict:
    results: List[Dict]=[]
    for url in article_urls:
        try:
            r=session.get(url)
            if not r.ok:
                results.append({'article_url': url, 'type': 'article_fetch', 'ok': False, 'status': r.status_code}); continue
            for m in extract_media_urls(r.text, base_url, selectors):
                row=validate_url(session, m); row['article_url']=url; results.append(row)
        except Exception as e:
            results.append({'article_url': url, 'type': 'article_fetch', 'ok': False, 'status': str(e)})
    errors=[r for r in results if not r.get('ok')]
    return {'results': results, 'checked': len(results), 'errors': len(errors)}
