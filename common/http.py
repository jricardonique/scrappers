
from __future__ import annotations
import os, time
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class ThrottledSession(requests.Session):
    def __init__(self, rate_limit_per_sec: float = 2.0, timeout: int = 15, user_agent: Optional[str] = None):
        super().__init__()
        self.rate_limit = max(0.001, rate_limit_per_sec)
        self.timeout = timeout
        self.last_request_ts = 0.0
        self.headers.update({'User-Agent': user_agent or os.getenv('HTTP_USER_AGENT','NYPost-QA-Scraper/1.0')})
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429,500,502,503,504])
        adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
        self.mount('http://', adapter)
        self.mount('https://', adapter)
    def request(self, method, url, **kwargs):
        now = time.time(); elapsed = now - self.last_request_ts; min_interval = 1.0/self.rate_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        kwargs.setdefault('timeout', self.timeout)
        resp = super().request(method, url, **kwargs)
        self.last_request_ts = time.time()
        return resp
