
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import requests
from bs4 import BeautifulSoup

# ==========================
# Config (editable via ENV)
# ==========================
USER_AGENT = os.getenv('USER_AGENT', 'NYPost-QA-OptionB/1.0 (+QA)')
TIMEOUT = int(os.getenv('TIMEOUT', '15'))
HEADLINES_LIMIT = int(os.getenv('HEADLINES_LIMIT', '20'))
CACHE_FILE = Path(os.getenv('CACHE_FILE', 'cache.json'))
DASHBOARD_FILE = Path(os.getenv('DASHBOARD_FILE', 'dashboard.html'))
ZAPIER_WEBHOOK_URL = os.getenv('ZAPIER_WEBHOOK_URL', '')
OFFLINE = os.getenv('OFFLINE', 'false').lower() == 'true'

# Mobile API endpoints for parity
API_ENDPOINTS = [
    'https://stage.stag.nypost.djservices.io/apps/nypost-v3/theaters/pagesix-subnav-collection?screen_ids=pagesix.section-PS',
    'https://stage.stag.nypost.djservices.io/apps/ca_post/theaters/tag-collection?screen_ids=california',
    'https://stage.stag.nypost.djservices.io/apps/nypost-v3/theaters/pagesix',
    'https://nypost.com/wp-json/nypost/v1.2/posts/slugs/william-byron-ricky-stenhouse-jr-have-value-at-pennzoil-400?api_key=ca2def68f4d13e28b83e40886240e556',
]

REQUIRED_SCHEMA_FIELDS = [
    'title', 'author', 'published', 'section', 'tags', 'lead_image', 'canonical_url', 'body_text'
]

# ==========================
# HTTP helpers
# ==========================

_session = None

def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({'User-Agent': USER_AGENT})
        _session = s
    return _session


def http_get(url: str, **kwargs) -> Optional[requests.Response]:
    if OFFLINE:
        return None
    try:
        return session().get(url, timeout=TIMEOUT, **kwargs)
    except Exception:
        return None


def http_head(url: str) -> Tuple[Optional[int], Optional[float]]:
    if OFFLINE:
        return (200, 0.0)
    t0 = time.time()
    try:
        r = session().head(url, timeout=TIMEOUT, allow_redirects=True)
        return (r.status_code, (time.time() - t0) * 1000)
    except Exception:
        try:
            t0 = time.time()
            r = session().get(url, timeout=TIMEOUT, stream=True)
            for _ in r.iter_content(chunk_size=4096):
                break
            r.close()
            return (r.status_code, (time.time() - t0) * 1000)
        except Exception:
            return (None, None)

# ==========================
# Web scraping
# ==========================

NYPOST_HOME = 'https://nypost.com/'


def scrape_homepage(limit=HEADLINES_LIMIT) -> List[Dict[str, str]]:
    if OFFLINE:
        return [
            {'title': 'Mock Story One', 'url': 'https://nypost.com/mock1'},
            {'title': 'Mock Story Two', 'url': 'https://nypost.com/mock2'},
        ]
    r = http_get(NYPOST_HOME)
    if not r or r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, 'lxml')
    headlines = []
    seen = set()
    for tag in soup.select('h1, h2, h3'):
        title = tag.get_text(strip=True)
        a = tag.find('a')
        href = a.get('href') if a else None
        if not title or not href:
            continue
        if href.startswith('/'):
            href = 'https://nypost.com' + href
        key = (title, href)
        if key in seen:
            continue
        seen.add(key)
        headlines.append({'title': title, 'url': href})
        if len(headlines) >= limit:
            break
    return headlines

# ==========================
# Article parsing & schema validation
# ==========================

META_AUTHOR_SELECTORS = [
    "meta[name='author']", "meta[property='article:author']", "[rel='author']", ".byline", ".author"
]
META_PUB_SELECTORS = [
    "meta[property='article:published_time']", "time", ".timestamp", ".date"
]
META_SECTION_SELECTORS = [
    "meta[property='article:section']", "[data-section]", ".section", ".channel"
]


def fetch_article_html(url: str) -> str:
    if OFFLINE:
        return "<html><head><title>Mock Article</title><meta property='og:image' content='https://example.com/mock.jpg'><meta property='article:published_time' content='2025-01-01T12:00:00Z'><meta name='author' content='Mock Author'><meta property='article:section' content='News'><link rel='canonical' href='https://nypost.com/mock1'><meta name='keywords' content='tag1, tag2'></head><body><article><p>Paragraph one.</p><img src='https://example.com/img1.jpg'><video src='https://example.com/vid1.mp4'></video><iframe src='https://www.youtube.com/embed/xyz'></iframe><blockquote class='twitter-tweet'>...</blockquote></article></body></html>"
    r = http_get(url)
    if r and r.status_code == 200:
        return r.text
    return ''


def extract_text(el: Optional[BeautifulSoup]) -> str:
    if not el:
        return ''
    return el.get_text(strip=True)


def schema_from_html(html: str, url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, 'lxml')
    title = None
    ogt = soup.find('meta', property='og:title')
    if ogt and ogt.get('content'):
        title = ogt['content']
    if not title:
        if soup.title and soup.title.get_text():
            title = soup.title.get_text(strip=True)
        else:
            h1 = soup.find('h1')
            title = extract_text(h1)

    author = ''
    for sel in META_AUTHOR_SELECTORS:
        el = soup.select_one(sel)
        if el:
            author = el.get('content') or extract_text(el)
            if author:
                break

    published = ''
    for sel in META_PUB_SELECTORS:
        el = soup.select_one(sel)
        if el:
            published = el.get('datetime') or el.get('content') or extract_text(el)
            if published:
                break

    section = ''
    for sel in META_SECTION_SELECTORS:
        el = soup.select_one(sel)
        if el:
            section = el.get('content') or extract_text(el)
            if section:
                break

    lead_image = ''
    ogimg = soup.find('meta', property='og:image')
    if ogimg and ogimg.get('content'):
        lead_image = ogimg['content']

    canonical_url = ''
    can = soup.find('link', rel='canonical')
    if can and can.get('href'):
        canonical_url = can['href']

    tags: List[str] = []
    for tag_meta in soup.find_all('meta', attrs={'property': 'article:tag'}):
        if tag_meta.get('content'):
            tags.append(tag_meta['content'])
    if not tags:
        kw = soup.find('meta', attrs={'name': 'keywords'})
        if kw and kw.get('content'):
            tags = [t.strip() for t in kw['content'].split(',') if t.strip()]

    body_text = ''
    main = soup.find('article') or soup.find('main') or soup.body
    if main:
        paras = [p.get_text(strip=True) for p in main.find_all('p') if p.get_text(strip=True)]
        body_text = '\n'.join(paras[:40])

    data = {
        'url': url,
        'title': title or '',
        'author': author or '',
        'published': published or '',
        'section': section or '',
        'tags': tags,
        'lead_image': lead_image or '',
        'canonical_url': canonical_url or '',
        'body_text': body_text or '',
    }
    missing = [f for f in REQUIRED_SCHEMA_FIELDS if (not data.get(f) or (isinstance(data.get(f), list) and not data.get(f)))]
    data['missing'] = missing
    return data

# ==========================
# Multimedia validation
# ==========================

IMG_ATTRS = ['src', 'data-src', 'data-lazy', 'data-original']
SOCIAL_DOMAINS = ['twitter.com', 'x.com', 'instagram.com', 'tiktok.com', 'youtube.com', 'youtu.be']


def extract_multimedia(html: str) -> Dict[str, List[str]]:
    soup = BeautifulSoup(html, 'lxml')
    images: List[str] = []
    videos: List[str] = []
    embeds: List[str] = []

    for img in soup.find_all('img'):
        for a in IMG_ATTRS:
            v = img.get(a)
            if v:
                images.append(v)
                break

    for vtag in soup.find_all(['video', 'source']):
        v = vtag.get('src')
        if v:
            videos.append(v)

    for iframe in soup.find_all('iframe'):
        src = iframe.get('src')
        if src and any(dom in src for dom in SOCIAL_DOMAINS):
            embeds.append(src)
    for script in soup.find_all('script'):
        src = script.get('src')
        if src and any(dom in src for dom in SOCIAL_DOMAINS):
            embeds.append(src)

    for gal in soup.select('.gallery, [data-gallery], .slideshow'):
        for img in gal.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                images.append(src)

    def norm(u: str) -> str:
        if u.startswith('//'):
            return 'https:' + u
        return u
    images = list(dict.fromkeys([norm(u) for u in images]))
    videos = list(dict.fromkeys([norm(u) for u in videos]))
    embeds = list(dict.fromkeys([norm(u) for u in embeds]))

    return {'images': images, 'videos': videos, 'embeds': embeds}


def validate_assets(urls: List[str]) -> List[Dict[str, Any]]:
    results = []
    for u in urls:
        status, ms = http_head(u)
        results.append({'url': u, 'status': status, 'elapsed_ms': ms})
    return results

# ==========================
# API parity
# ==========================


def extract_titles_from_json(data: Any) -> List[str]:
    titles = []
    if isinstance(data, dict):
        for key in ('title', 'headline'):
            v = data.get(key)
            if isinstance(v, str):
                titles.append(v)
            elif isinstance(v, dict) and 'rendered' in v:
                titles.append(v['rendered'])
        for v in data.values():
            titles.extend(extract_titles_from_json(v))
    elif isinstance(data, list):
        for item in data:
            titles.extend(extract_titles_from_json(item))
    return titles


def api_parity_check(web_headlines: List[Dict[str, str]]) -> Dict[str, Any]:
    results = []
    web_titles = {h['title'].strip().lower() for h in web_headlines}
    for ep in API_ENDPOINTS:
        if OFFLINE:
            api_titles = {'Mock Story One', 'Mock From API'}
        else:
            r = http_get(ep)
            if not r or r.status_code != 200:
                results.append({'endpoint': ep, 'status': None, 'ok': False, 'overlap': 0, 'api_count': 0})
                continue
            try:
                data = r.json()
            except Exception:
                results.append({'endpoint': ep, 'status': r.status_code, 'ok': False, 'overlap': 0, 'api_count': 0})
                continue
            api_titles_list = extract_titles_from_json(data)
            api_titles = {t.strip().lower() for t in api_titles_list if isinstance(t, str) and t.strip()}
        overlap = len(web_titles & api_titles)
        results.append({'endpoint': ep, 'ok': True, 'overlap': overlap, 'api_count': len(api_titles)})
    return {'web_count': len(web_titles), 'endpoints': results}

# ==========================
# Push simulation (type A)
# ==========================


def load_cache() -> Dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_cache(data: Dict[str, Any]):
    try:
        CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        pass


def simulate_push_events(current_headlines: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    cache = load_cache()
    prev = {item['url'] for item in cache.get('headlines', [])}
    now = {h['url'] for h in current_headlines}
    new_urls = list(now - prev)
    events = []
    ts = int(time.time())
    for h in current_headlines:
        if h['url'] in new_urls:
            events.append({'title': h['title'], 'url': h['url'], 'detected_ts': ts})
    save_cache({'headlines': current_headlines, 'ts': ts})
    return events

# ==========================
# Dashboard generation (auto light/dark)
# ==========================

DASHBOARD_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>NYPost QA Dashboard</title>
<style>
:root{ --bg:#0f172a; --fg:#e2e8f0; --card:#111827; --ok:#16a34a; --warn:#f59e0b; --err:#ef4444; --muted:#94a3b8; }
@media (prefers-color-scheme: light){ :root{ --bg:#f8fafc; --fg:#0f172a; --card:#ffffff; --ok:#15803d; --warn:#b45309; --err:#b91c1c; --muted:#475569; } }
body{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,Segoe UI,Arial,sans-serif;margin:0}
main{max-width:1100px;margin:40px auto;padding:0 16px}
section{background:var(--card);border-radius:10px;padding:16px;margin:12px 0}
h1{font-size:26px;margin:0 0 16px}
h2{font-size:18px;margin:0 0 12px}
pre{white-space:pre-wrap;word-break:break-word}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px}
.badge.ok{background:rgba(22,163,74,.15);color:var(--ok)}
.badge.err{background:rgba(239,68,68,.15);color:var(--err)}
.badge.warn{background:rgba(245,158,11,.15);color:var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.card{background:var(--card);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:12px}
small{color:var(--muted)}
.code{background:rgba(148,163,184,.1);padding:8px;border-radius:6px}
ul{padding-left:18px}
</style>
</head>
<body>
<main>
  <h1>NYPost QA Dashboard</h1>
  <section>
    <h2>Summary</h2>
    <div id="summary" class="grid"></div>
  </section>
  <section>
    <h2>New Push Events</h2>
    <div id="push"></div>
  </section>
  <section>
    <h2>Schema Validation</h2>
    <div id="schema"></div>
  </section>
  <section>
    <h2>Multimedia Validation</h2>
    <div id="media"></div>
  </section>
  <section>
    <h2>API Parity</h2>
    <div id="parity"></div>
  </section>
  <section>
    <h2>Headlines</h2>
    <div id="headlines"></div>
  </section>
</main>
<script>
const DATA = __DATA__;
function el(tag, cls){ const e=document.createElement(tag); if(cls) e.className=cls; return e; }
function badge(text, kind){ const b=el('span','badge '+kind); b.textContent=text; return b; }
(function(){
  const s = el('div','grid');
  const cards=[
    ['Headlines', DATA.headlines.length],
    ['New Push Events', DATA.push_events.length],
    ['Articles Validated', DATA.schema_results.length],
    ['Articles with Missing Fields', DATA.schema_results.filter(a=>a.missing&&a.missing.length).length],
    ['Images Checked', DATA.media_summary.images.checked],
    ['Broken Images', DATA.media_summary.images.broken],
    ['Videos Checked', DATA.media_summary.videos.checked],
    ['Embeds Found', DATA.media_summary.embeds.count],
  ];
  for(const [k,v] of cards){ const c=el('div','card'); c.innerHTML = `<strong>${k}</strong><div style="font-size:22px;margin-top:6px">${v}</div>`; s.appendChild(c); }
  document.getElementById('summary').appendChild(s);
})();
(function(){
  const wrp = el('div');
  if(!DATA.push_events.length){ wrp.innerHTML='<small>No new items since last run.</small>'; }
  else{
    const ul = el('ul');
    for(const ev of DATA.push_events){ const li = el('li'); const a = el('a'); a.href=ev.url; a.textContent=ev.title; a.target='_blank'; li.appendChild(a); li.appendChild(document.createTextNode(' ')); li.appendChild(badge(new Date(ev.detected_ts*1000).toLocaleString(),'ok')); ul.appendChild(li);} 
    wrp.appendChild(ul);
  }
  document.getElementById('push').appendChild(wrp);
})();
(function(){
  const wrp=el('div'); const ul = el('ul');
  for(const art of DATA.schema_results){ const li = el('li'); const a = el('a'); a.href=art.url; a.textContent=art.title||art.url; a.target='_blank'; li.appendChild(a); if(art.missing && art.missing.length){ li.appendChild(document.createTextNode(' ')); li.appendChild(badge('Missing: '+art.missing.join(', '),'err')); } wrp.appendChild(li); }
  if(!DATA.schema_results.length) wrp.innerHTML='<small>No articles validated.</small>';
  document.getElementById('schema').appendChild(wrp);
})();
(function(){
  const wrp=el('div'); const imgLine = `Images: checked ${DATA.media_summary.images.checked}, broken ${DATA.media_summary.images.broken}`; const vidLine = `Videos: checked ${DATA.media_summary.videos.checked}, (failures not counted via HEAD)`; const embLine = `Embeds: ${DATA.media_summary.embeds.count}`; wrp.innerHTML = `<div class='code'>${imgLine}<br>${vidLine}<br>${embLine}</div>`; document.getElementById('media').appendChild(wrp);
})();
(function(){
  const wrp=el('div'); const ul = el('ul');
  for(const ep of DATA.api_parity.endpoints){ const li = el('li'); li.textContent = `${ep.endpoint} → ok=${ep.ok} api_count=${ep.api_count} overlap=${ep.overlap}`; ul.appendChild(li);} wrp.appendChild(ul); document.getElementById('parity').appendChild(wrp);
})();
(function(){
  const wrp = el('div'); const ul = el('ul');
  for(const h of DATA.headlines){ const li = el('li'); const a = el('a'); a.href=h.url; a.textContent=h.title; a.target='_blank'; li.appendChild(a); ul.appendChild(li);} wrp.appendChild(ul); document.getElementById('headlines').appendChild(wrp);
})();
</script>
</body>
</html>
"""

# ==========================
# Email via Zapier
# ==========================

def send_email(summary_text: str):
    if not ZAPIER_WEBHOOK_URL:
        print('[Email] ZAPIER_WEBHOOK_URL not set; skipping email.')
        return False
    try:
        r = requests.post(ZAPIER_WEBHOOK_URL, json={'subject': 'NYPost QA Report', 'text': summary_text}, timeout=TIMEOUT)
        print('[Email] Zapier status:', r.status_code)
        return 200 <= r.status_code < 300
    except Exception as e:
        print('[Email] Error:', e)
        return False

# ==========================
# Main pipeline
# ==========================

def main():
    headlines = scrape_homepage()
    push_events = simulate_push_events(headlines)

    schema_results = []
    media_checked_images = 0
    media_broken_images = 0
    media_embeds = 0
    media_videos_checked = 0

    check_urls = [h['url'] for h in headlines[: min(10, len(headlines))]]
    for url in check_urls:
        html = fetch_article_html(url)
        if not html:
            continue
        art = schema_from_html(html, url)
        schema_results.append(art)
        media = extract_multimedia(html)
        img_results = validate_assets(media['images'])
        media_checked_images += len(img_results)
        media_broken_images += sum(1 for r in img_results if (not r['status']) or (r['status'] and r['status'] >= 400))
        vid_results = validate_assets(media['videos'])
        media_videos_checked += len(vid_results)
        media_embeds += len(media['embeds'])

    media_summary = {
        'images': {'checked': media_checked_images, 'broken': media_broken_images},
        'videos': {'checked': media_videos_checked},
        'embeds': {'count': media_embeds}
    }

    api_parity = api_parity_check(headlines)

    data = {
        'headlines': headlines,
        'push_events': push_events,
        'schema_results': schema_results,
        'media_summary': media_summary,
        'api_parity': api_parity,
        'generated_ts': int(time.time()),
    }
    html = DASHBOARD_TEMPLATE.replace('__DATA__', json.dumps(data, ensure_ascii=False))
    DASHBOARD_FILE.write_text(html, encoding='utf-8')
    print('[Dashboard] Wrote', DASHBOARD_FILE)

    missing_total = sum(1 for a in schema_results if a.get('missing'))
    lines_summary = [
        f"Headlines: {len(headlines)}",
        f"New push events: {len(push_events)}",
        f"Articles validated: {len(schema_results)}",
        f"Articles with missing schema: {missing_total}",
        f"Images checked: {media_checked_images}, broken: {media_broken_images}",
        f"API parity endpoints checked: {len(api_parity['endpoints'])}",
        f"Dashboard: {str(DASHBOARD_FILE)}",
    ]
    summary = "\n".join(lines_summary)
send_email(summary)

if __name__ == '__main__':
    main()
