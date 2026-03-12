
from __future__ import annotations
import time
from typing import List, Dict
from common.http import ThrottledSession

def probe(session: ThrottledSession, url: str) -> Dict:
    row={'url': url, 'ok': False, 'status': None, 'elapsed_ms': None, 'bytes': None}
    t0=time.time()
    try:
        r=session.get(url, stream=True)
        row['status']=r.status_code; row['ok']=r.ok
        row['elapsed_ms']=round((time.time()-t0)*1000,1)
        size=0
        for chunk in r.iter_content(8192):
            if chunk:
                size+=len(chunk)
                if size>2_000_000: break
        row['bytes']=size; r.close()
    except Exception as e:
        row['status']=str(e)
    return row

def run(urls: List[str], session: ThrottledSession) -> Dict:
    rows=[probe(session, u) for u in urls]
    slow=[r for r in rows if r.get('elapsed_ms') and r['elapsed_ms']>1500]
    return {'rows': rows, 'checked': len(rows), 'slow': len(slow)}
