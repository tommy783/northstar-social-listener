# Northstar Growth — Social Listener (LinkedIn + X)

What your space is talking about, in one dashboard. Four sources:

1. **LinkedIn · Key Voices** — posts from 39 tracked SEO/GEO/AEO people
2. **LinkedIn · The Industry** — posts matching core keywords
3. **X · Key Voices** — the same people on X (where the handle is known)
4. **X · The Industry** — keyword posts on X

Quality filter: industry posts need ≥30 likes; key-voice posts need ≥3.
Sorted most-engaging first by default. Filter by platform, source, person,
keyword, or free-text search.

## How often to run it
Runs use your Apify account. On the **free $5/month plan**, one full run costs
roughly **$0.60–1.00**, so the practical cadence is **about once a month**
(the budget resets on the 28th). To run more often (e.g. weekly/daily),
upgrade the Apify plan at https://console.apify.com/billing/subscription.

## To run
Double-click **`Refresh Dashboard.command`**, or in a terminal:
```
python3 listen.py          # scrape everything + rebuild dashboard
python3 listen.py --build  # rebuild from last scrape only (free, no token)
```
Then open `dashboard.html` in any browser.

## Notes
- Token lives in `.env` (already set up). No `pip install` needed.
- The **X profile scraper rate-limits** if hammered; the script chunks calls
  with delays and retries. If X voices come back light on a given run, the
  X keyword search still covers the space.
- LinkedIn keyword search is sorted by **relevance** (popular posts), not date,
  so the ≥30-like industry filter has good posts to show.

## Files
- `listen.py` — the whole tool (scrape + build)
- `dashboard.html` — the dashboard
- `data/` — dated JSON snapshot per run · `raw/` — last raw scrape per source
- `.env` — Apify token (git-ignored)
