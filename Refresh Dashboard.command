#!/bin/bash
# Double-click this file (about once a month — see README) to pull fresh LinkedIn posts
# and rebuild the dashboard, then open it in your browser.
cd "$(dirname "$0")"
echo "Refreshing Northstar Growth social listener…"
python3 listen.py
echo ""
echo "Opening dashboard…"
open dashboard.html
echo "Done. You can close this window."
