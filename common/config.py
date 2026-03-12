
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os, yaml

@dataclass
class Selectors:
    article_card: str
    headline: str
    link: str
    author: str
    time: str
    section_tag: str
    images: str
    videos: str

@dataclass
class Thresholds:
    perf_slow_ms: int = 1500
    schema_max_missing: int = 0
    multimedia_fail_alert_min: int = 1

@dataclass
class EmailCfg:
    enabled: bool = True
    provider: str = 'sendgrid'
    to_env: str = 'TO_EMAIL'
    from_env: str = 'FROM_EMAIL'
    api_key_env: str = 'SENDGRID_API_KEY'

@dataclass
class Config:
    base_url: str
    sections: list
    output_dir: Path
    user_agent: str
    rate_limit_per_sec: float
    request_timeout: int
    selectors: Selectors
    thresholds: Thresholds
    email: EmailCfg
    respect_robots_txt: bool = True

def _env_substitute(value: Any) -> Any:
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        env_var = value[2:-1]
        return os.getenv(env_var, '')
    return value

def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text())
    for k in ('user_agent','rate_limit_per_sec','request_timeout'):
        if k in data: data[k] = _env_substitute(data[k])
    def _num(v, fb, cast):
        try:
            if v is None: return fb
            if isinstance(v,str):
                v=v.strip();
                if v=='': return fb
                return cast(v)
            return cast(v)
        except Exception:
            return fb
    sels = Selectors(**data.get('selectors', {}))
    ua = data.get('user_agent') or os.getenv('HTTP_USER_AGENT') or 'NYPost-QA-Scraper/1.0'
    rate = _num(data.get('rate_limit_per_sec', 2), 2.0, float)
    timeout = _num(data.get('request_timeout', 15), 15, int)
    th = Thresholds(**data.get('thresholds', {}))
    em = EmailCfg(**data.get('email', {}))
    return Config(
        base_url=data['base_url'], sections=data['sections'], output_dir=Path(data['output_dir']),
        user_agent=ua, rate_limit_per_sec=rate, request_timeout=timeout,
        selectors=sels, thresholds=th, email=em, respect_robots_txt=bool(data.get('respect_robots_txt', True))
    )
