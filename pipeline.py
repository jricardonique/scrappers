
from __future__ import annotations
import os, json
from pathlib import Path
from dotenv import load_dotenv
from common.config import load_config
from common.http import ThrottledSession
from common.output import run_dir, write_json
from common.logging_config import setup_logging
from scrapers import headlines_sections, perf_monitor, article_schema_validator


def main():
    load_dotenv()
    cfg = load_config(Path('config.yaml'))
    logger = setup_logging(Path('logs'), name='pipeline')
    session = ThrottledSession(rate_limit_per_sec=cfg.rate_limit_per_sec, timeout=cfg.request_timeout, user_agent=cfg.user_agent)
    out = run_dir(Path(cfg.output_dir))
    logger.info(f'Pipeline output: {out}')

    grouped = headlines_sections.run(cfg.base_url, cfg.sections, 50, cfg.selectors, session)
    write_json(out / 'headlines_sections.json', grouped)

    overrides = grouped.get('overrides', {})
    def perf_url_for(section: str) -> str:
        return (overrides.get(section) or f"{cfg.base_url.rstrip('/')}/{section.strip('/')}")
    perf_urls = [cfg.base_url] + [perf_url_for(s) for s in cfg.sections]
    p = perf_monitor.run(perf_urls, session)

    all_urls=[]
    for sec in grouped.get('sections', []):
        all_urls.extend([r['url'] for r in grouped['by_section'].get(sec, [])])
    urls = all_urls[:40]

    s_rows=[]
    for u in urls:
        try:
            r=session.get(u)
            ok=r.ok
            data=article_schema_validator.parse_article(r.text if ok else '', cfg.selectors, cfg.base_url) if ok else {k:'' for k in ['title','author','published','section','lead_image']}
            issues=article_schema_validator.validate_article(data)
            s_rows.append({'url': u, 'http_ok': ok, **data, **issues})
        except Exception as e:
            s_rows.append({'url': u, 'http_ok': False, 'error': str(e), 'missing_fields': 'title, author, published, section, lead_image'})
    s_summary={'checked': len(s_rows), 'issues': sum(1 for r in s_rows if r.get('missing_fields'))}
    write_json(out / 'article_schema_validation.json', s_rows)

    summary={
        'headlines': {'count': sum(len(grouped['by_section'].get(sec, [])) for sec in grouped['sections'])},
        'perf': {'checked': p['checked'], 'slow': p['slow']},
        'schema': s_summary,
        'output': str(out)
    }
    write_json(out / 'pipeline_summary.json', summary)
    logger.info(f'Summary: {summary}')

if __name__ == '__main__':
    main()
