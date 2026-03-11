
from __future__ import annotations
import os, json
from pathlib import Path
from dotenv import load_dotenv
from common.config import load_config
from common.http import ThrottledSession
from common.output import run_dir, write_json
from common.logging_config import setup_logging
from common.email import email_alert
from scrapers import headlines_sections, multimedia_validator, perf_monitor, article_schema_validator


def main():
    load_dotenv()
    cfg = load_config(Path('config.yaml'))
    logger = setup_logging(Path('logs'), name='pipeline')
    session = ThrottledSession(rate_limit_per_sec=cfg.rate_limit_per_sec, timeout=cfg.request_timeout, user_agent=cfg.user_agent)
    out = run_dir(Path(cfg.output_dir))
    logger.info(f'Pipeline output: {out}')

    offline = os.getenv('SKIP_NETWORK', 'false').lower() == 'true'

    if offline:
        h = {'count': 0}
        m = {'checked': 0, 'errors': 0}
        p = {'checked': 0, 'slow': 0}
        s = {'checked': 0, 'issues': 0}
        write_json(out / 'headlines_sections.json', [])
    else:
        sections = cfg.sections[:6]
        h = headlines_sections.run(cfg.base_url, sections, 30, cfg.selectors, session, out)
        hs_path = out / 'headlines_sections.json'
        urls = []
        if hs_path.exists():
            data = json.loads(hs_path.read_text())
            urls = [row['url'] for row in data][:40]
        m = multimedia_validator.run(cfg.base_url, urls, cfg.selectors, session, out)
        perf_urls = [cfg.base_url] + [f"{cfg.base_url}/{s}" for s in sections]
        p = perf_monitor.run(perf_urls, session, out)
        s = article_schema_validator.run(cfg.base_url, urls, cfg.selectors, session, out)

    summary = {'headlines': h, 'multimedia': m, 'perf': p, 'schema': s, 'output': str(out)}
    write_json(out / 'pipeline_summary.json', summary)
    logger.info(f'Summary: {summary}')

    alerts = []
    if os.getenv('DISABLE_EMAIL', 'false').lower() != 'true' and cfg.email.enabled:
        if m.get('errors', 0) >= cfg.thresholds.multimedia_fail_alert_min:
            alerts.append(f"Multimedia broken assets: {m['errors']}")
        if p.get('slow', 0) > 0:
            alerts.append(f"Slow URLs: {p['slow']} (> {cfg.thresholds.perf_slow_ms} ms)")
        if s.get('issues', 0) > cfg.thresholds.schema_max_missing:
            alerts.append(f"Articles with schema issues: {s['issues']}")
        if alerts:
            msg = "
".join(alerts) + f"

Output: {out}"
            email_alert("[NYPost QA] Pipeline Alerts", msg)

if __name__ == '__main__':
    main()
