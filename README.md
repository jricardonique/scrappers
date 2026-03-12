
# NYPost QA Suite — Option B (Full Scrapers + Analytics Dashboard)

**What you get**
- Real **headlines** crawl
- **Multimedia** asset checks (status, size, latency)
- **Schema** validation (title/author/published/section/lead image)
- **Performance** checks for key pages
- A **Netlify-ready analytics dashboard** with KPIs, tables, and charts
- A **history.json** that accumulates the last 30 runs for trend charts

**How to use**
1) Upload the *contents* of this folder to your GitHub repo root (keep `.github/workflows/scraper.yml`).
2) In GitHub → Settings → Secrets/Variables → Actions:
   - Variables: `HTTP_USER_AGENT`, `RATE_LIMIT_PER_SEC`, `REQUEST_TIMEOUT` (optional)
   - Variables: `SKIP_NETWORK=false`, `DISABLE_EMAIL=false` (live mode)
   - Secrets: `SENDGRID_API_KEY`, `FROM_EMAIL`, `TO_EMAIL` (to enable email alerts; optional)
3) Run the workflow once (Actions → Run workflow). It will commit JSON to `web/data/` and update `history.json`.
4) Point Netlify to `web/` as **Publish directory** and (optionally) set a **Build Hook**. Each run updates the dashboard.
