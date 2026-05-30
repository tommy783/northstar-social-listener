#!/bin/bash
# Double-click this (about once a month — see README) to pull fresh posts,
# rebuild the dashboard, open it locally, AND update the live shared link.
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:$PATH"

echo "Refreshing Northstar Growth social listener…"
python3 listen.py || { echo "Scrape failed — see message above."; exit 1; }

echo ""
echo "Publishing update to the live link…"
git add -A
git commit -m "refresh $(date +%Y-%m-%d)" >/dev/null 2>&1 && git push >/dev/null 2>&1 \
  && echo "✓ Live link updated: https://tommy783.github.io/northstar-social-listener/" \
  || echo "(nothing new to publish, or push skipped)"

echo ""
echo "Opening local dashboard…"
open dashboard.html
echo "Done. You can close this window."
