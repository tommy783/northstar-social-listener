#!/usr/bin/env python3
"""
Northstar Growth - Social Listener  (LinkedIn + X)
==================================================
Builds a single standalone dashboard.html of what your space is talking
about, from four sources:

  LinkedIn · Key Voices   - posts from tracked SEO/GEO/AEO people
  LinkedIn · The Industry - posts matching your core keywords
  X        · Key Voices   - posts from the same people on X (where known)
  X        · The Industry - posts matching your core keywords on X

Quality filter: industry posts need >=30 likes; key-voice posts need >=3.
Sorted most-engaging first by default.

No pip installs required - uses only the Python standard library.

Daily use:
    python3 listen.py            # scrape fresh data + rebuild dashboard
    python3 listen.py --build    # rebuild from last scrape (no token needed)

Token: put it once in a file  .env  next to this script:
    APIFY_TOKEN=apify_api_xxxxx
"""

import os, sys, json, time, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
RAW  = BASE / "raw"
DATA = BASE / "data"
DASH = BASE / "dashboard.html"

# ── Actors ──────────────────────────────────────────────────────────────
LI_PROFILE_ACTOR = "A3cAPGpwBEG8RJwse"   # harvestapi/linkedin-profile-posts
LI_KEYWORD_ACTOR = "buIWk2uOUzTmcLsuB"   # harvestapi/linkedin-post-search
X_PROFILE_ACTOR  = "Fo9GoU5wC270BgcBr"   # scraper_one/x-profile-posts-scraper
X_SEARCH_ACTOR   = "dOpbyXERU9eIsl4w6"   # scraping_solutions twitter search

# ── LinkedIn key voices (verified vanity URLs) ──────────────────────────
LI_VOICES = {
    "https://www.linkedin.com/in/aleyda/":               "Aleyda Solís",
    "https://www.linkedin.com/in/lily-ray-44755615/":    "Lily Ray",
    "https://www.linkedin.com/in/koray-tugberk-gubur/":  "Koray Tuğberk Gübür",
    "https://www.linkedin.com/in/michaelkingphilly/":    "Mike King",
    "https://www.linkedin.com/in/randfishkin/":          "Rand Fishkin",
    "https://www.linkedin.com/in/rustybrick/":           "Barry Schwartz",
    "https://www.linkedin.com/in/marie-haynes/":         "Dr Marie Haynes",
    "https://www.linkedin.com/in/brianedean/":           "Brian Dean",
    "https://www.linkedin.com/in/ferenczkaszoni/":       "Fery Kaszoni",
    "https://www.linkedin.com/in/mattdiggityseo/":       "Matt Diggity",
    "https://www.linkedin.com/in/evanbailyn/":           "Evan Bailyn",
    "https://www.linkedin.com/in/russelllobo/":          "Russell Lobo",
    "https://www.linkedin.com/in/glenngabe/":            "Glenn Gabe",
    "https://www.linkedin.com/in/cyrusshepard/":         "Cyrus Shepard",
    "https://www.linkedin.com/in/kevinindig/":           "Kevin Indig",
    "https://www.linkedin.com/in/areejabuali/":          "Areej AbuAli",
    "https://www.linkedin.com/in/patrickstox/":          "Patrick Stox",
    "https://www.linkedin.com/in/markseo/":              "Mark Williams-Cook",
    "https://www.linkedin.com/in/brodieclark/":          "Brodie Clark",
    "https://www.linkedin.com/in/joyhawkins/":           "Joy Hawkins",
    "https://www.linkedin.com/in/darrenshawwhitespark/": "Darren Shaw",
    "https://www.linkedin.com/in/dannysullivan/":        "Danny Sullivan",
    "https://www.linkedin.com/in/johnmueller/":          "John Mueller",
    "https://www.linkedin.com/in/elischwartz/":          "Eli Schwartz",
    "https://www.linkedin.com/in/mordyoberstein/":       "Mordy Oberstein",
    "https://www.linkedin.com/in/izzi-smith/":           "Izzi Smith",
    "https://www.linkedin.com/in/kristinaazarenko/":     "Kristina Azarenko",
    "https://www.linkedin.com/in/lidiainfante/":         "Lidia Infante",
    "https://www.linkedin.com/in/chima-mmeje/":          "Chima Mmeje",
    "https://www.linkedin.com/in/bernardjhuang/":        "Bernard Huang",
    "https://www.linkedin.com/in/gael-breton-78305118/": "Gael Breton",
    "https://www.linkedin.com/in/markwebster1/":         "Mark Webster",
    "https://www.linkedin.com/in/carrieroseballoch/":    "Carrie Rose",
    "https://www.linkedin.com/in/nathangotch/":          "Nathan Gotch",
    "https://www.linkedin.com/in/craigcampbell0302/":    "Craig Campbell",
    "https://www.linkedin.com/in/matthewwoodwarduk/":    "Matthew Woodward",
    "https://www.linkedin.com/in/thedigitalmarketingconsultant/": "Ryan Stewart",
    "https://www.linkedin.com/in/joostdevalk/":          "Joost de Valk",
    "https://www.linkedin.com/in/mariekerakt/":          "Marieke de Valk",
}

# ── X key voices (handle in lower-case → name) ──────────────────────────
# Posts are only kept if the scraped screenName matches the key here, so a
# wrong guess just yields nothing (it never mis-attributes a post).
X_VOICES = {
    "aleyda":"Aleyda Solís", "lilyraynyc":"Lily Ray", "koraygubur":"Koray Tuğberk Gübür",
    "ipullrank":"Mike King", "randfish":"Rand Fishkin", "rustybrick":"Barry Schwartz",
    "marie_haynes":"Dr Marie Haynes", "brian_g_dean":"Brian Dean", "mattdiggity":"Matt Diggity",
    "glenngabe":"Glenn Gabe", "cyrusshepard":"Cyrus Shepard", "kevin_indig":"Kevin Indig",
    "patrickstox":"Patrick Stox", "joyannehawkins":"Joy Hawkins", "darrenshaw99":"Darren Shaw",
    "dannysullivan":"Danny Sullivan", "johnmu":"John Mueller", "5le":"Eli Schwartz",
    "mordyoberstein":"Mordy Oberstein", "gaelbreton":"Gael Breton", "gotchseo":"Nathan Gotch",
    "mattwoodwarduk":"Matthew Woodward", "ryanwashere":"Ryan Stewart", "jdevalk":"Joost de Valk",
    "areejabuali":"Areej AbuAli", "lidiainfantem":"Lidia Infante", "kristinaazarenko":"Kristina Azarenko",
    "bernardjhuang":"Bernard Huang", "evanbailyn":"Evan Bailyn",
}

# ── Keyword searches → short label shown on the dashboard ───────────────
KEYWORDS = {
    "SEO":                            "SEO",
    "generative engine optimization": "GEO",
    "answer engine optimization":     "AEO",
    "search everywhere optimization": "Search Everywhere",
    "AI search optimization":         "AI Search",
    "marketing agency SEO":           "Agency",
}

# ── Tuning ──────────────────────────────────────────────────────────────
LI_POSTS_PER_VOICE   = 8
LI_POSTS_PER_KEYWORD = 30
X_POSTS_PER_VOICE    = 10
X_POSTS_PER_KEYWORD  = 40
POSTED_LIMIT         = "week"          # LinkedIn date filter
X_DAYS               = 7               # X has no date filter → trim in code
MIN_LIKES_INDUSTRY   = 30
MIN_LIKES_VOICE      = 3


# ── Token ───────────────────────────────────────────────────────────────
def get_token():
    tok = os.environ.get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN")
    if tok:
        return tok.strip()
    envf = BASE / ".env"
    if envf.exists():
        for line in envf.read_text().splitlines():
            if line.strip().startswith("APIFY_TOKEN") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def run_actor(actor_id, run_input, token, timeout=300):
    url = (f"https://api.apify.com/v2/acts/{actor_id}"
           f"/run-sync-get-dataset-items?token={urllib.parse.quote(token)}")
    body = json.dumps(run_input).encode()
    req  = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def scrape(token):
    RAW.mkdir(exist_ok=True)

    # 1 ── LinkedIn key voices ──────────────────────────────────────────
    print("  → LinkedIn key voices (%d profiles)…" % len(LI_VOICES))
    li_profiles = run_actor(LI_PROFILE_ACTOR, {
        "targetUrls":     list(LI_VOICES.keys()),
        "maxPosts":       LI_POSTS_PER_VOICE,
        "postedLimit":    POSTED_LIMIT,
        "includeReposts": True, "includeQuotePosts": True,
    }, token)
    (RAW / "li_profiles.json").write_text(json.dumps(li_profiles, ensure_ascii=False))
    print("    ✓ %d posts" % len(li_profiles))

    # 2 ── LinkedIn keyword search ──────────────────────────────────────
    print("  → LinkedIn industry (%d keywords)…" % len(KEYWORDS))
    li_keywords = run_actor(LI_KEYWORD_ACTOR, {
        "searchQueries": list(KEYWORDS.keys()),
        "maxPosts":      LI_POSTS_PER_KEYWORD,
        # 'relevance' surfaces popular/engaging posts; 'date' returns newest,
        # which on the keyword firehose is mostly tiny accounts (median 0 likes).
        "postedLimit":   POSTED_LIMIT, "sortBy": "relevance",
    }, token)
    (RAW / "li_keywords.json").write_text(json.dumps(li_keywords, ensure_ascii=False))
    print("    ✓ %d posts" % len(li_keywords))

    # 3 ── X keyword search ─────────────────────────────────────────────
    print("  → X industry (%d keywords)…" % len(KEYWORDS))
    try:
        x_keywords = run_actor(X_SEARCH_ACTOR, {
            "TypeScraper": "search",
            "Input_Search": list(KEYWORDS.keys()),
            "filter": "top", "resultsLimit": X_POSTS_PER_KEYWORD,
        }, token)
    except Exception as e:
        print("    ! X industry failed (%s) – skipping" % e); x_keywords = []
    (RAW / "x_keywords.json").write_text(json.dumps(x_keywords, ensure_ascii=False))
    print("    ✓ %d posts" % len(x_keywords))

    # 4 ── X key voices (chunks of 5, this actor rate-limits) ───────────
    print("  → X key voices (%d handles, in chunks)…" % len(X_VOICES))
    handles = list(X_VOICES.keys())
    x_profiles = []
    for i in range(0, len(handles), 5):
        chunk = handles[i:i+5]
        urls  = [f"https://x.com/{h}" for h in chunk]
        for attempt in (1, 2):
            try:
                items = run_actor(X_PROFILE_ACTOR, {
                    "profileUrls": urls, "resultsLimit": X_POSTS_PER_VOICE,
                    "skipPinnedPosts": True,
                }, token, timeout=120)
                if items:
                    x_profiles.extend(items)
                break
            except Exception as e:
                if attempt == 2:
                    print("    ! chunk %s failed: %s" % (chunk, e))
        time.sleep(4)   # be gentle – this actor throttles
    (RAW / "x_profiles.json").write_text(json.dumps(x_profiles, ensure_ascii=False))
    print("    ✓ %d posts" % len(x_profiles))


# ── Normalisation ────────────────────────────────────────────────────────
def _i(v):
    try:    return int(v or 0)
    except: return 0

def _to_ms(ts):
    ts = _i(ts)
    if ts == 0:        return 0
    if ts < 10**12:    return ts * 1000     # seconds → ms
    return ts

def _ago(ms, now_ms):
    if not ms: return ""
    s = max(0, (now_ms - ms) // 1000)
    if s < 3600:   return f"{s//60}m ago"
    if s < 86400:  return f"{s//3600}h ago"
    return f"{s//86400}d ago"

def _avatar(a):
    if isinstance(a, dict): return a.get("url") or ""
    return a or ""


def norm_li(raw, source, bucket, now_ms):
    author = raw.get("author") or {}
    text   = (raw.get("content") or "").strip()
    is_rep = False
    if not text and (raw.get("repost") or {}).get("content"):
        text = raw["repost"]["content"].strip(); is_rep = True
    eng = raw.get("engagement") or {}
    likes, comments, shares = _i(eng.get("likes")), _i(eng.get("comments")), _i(eng.get("shares"))
    ms = _to_ms((raw.get("postedAt") or {}).get("timestamp"))
    return {
        "platform":"linkedin", "source":source, "bucket":bucket,
        "author":author.get("name") or "Unknown",
        "headline":(author.get("info") or "")[:110],
        "author_url":author.get("linkedinUrl") or "",
        "avatar":_avatar(author.get("avatar")),
        "text":text, "url":raw.get("linkedinUrl") or "",
        "ts_ms":ms, "ago":_ago(ms, now_ms),
        "likes":likes, "comments":comments, "shares":shares,
        "engagement":likes+comments+shares, "is_repost":is_rep,
    }

def norm_x_search(raw, now_ms):
    user = raw.get("user") or {}
    likes = _i(raw.get("favorite_count")); rts = _i(raw.get("retweet_count"))
    reps  = _i(raw.get("reply_count"));    qts = _i(raw.get("quote_count"))
    ms = _to_ms(raw.get("timestamp"))
    label = KEYWORDS.get(raw.get("search",""), raw.get("search") or "Keyword")
    return {
        "platform":"x", "source":"keyword", "bucket":label,
        "author":user.get("full_name") or "Unknown", "headline":"",
        "author_url":raw.get("link_user") or "", "avatar":user.get("profile_pic_url") or "",
        "text":(raw.get("text") or "").strip(), "url":raw.get("link_post") or "",
        "ts_ms":ms, "ago":_ago(ms, now_ms),
        "likes":likes, "comments":reps, "shares":rts+qts,
        "engagement":likes+rts+reps+qts, "is_repost":False,
    }

def norm_x_profile(raw, now_ms):
    author = raw.get("author") or {}
    handle = (author.get("screenName") or "").lower()
    name   = X_VOICES.get(handle)
    if not name:               # screenName doesn't match a tracked voice → drop
        return None
    likes = _i(raw.get("favouriteCount")); rts = _i(raw.get("repostCount"))
    reps  = _i(raw.get("replyCount"));     qts = _i(raw.get("quoteCount"))
    ms = _to_ms(raw.get("timestamp"))
    return {
        "platform":"x", "source":"voice", "bucket":name,
        "author":author.get("name") or name, "headline":f"@{author.get('screenName','')}",
        "author_url":f"https://x.com/{author.get('screenName','')}",
        "avatar":author.get("profileImageUrl") or "",
        "text":(raw.get("postText") or "").strip(), "url":raw.get("postUrl") or "",
        "ts_ms":ms, "ago":_ago(ms, now_ms),
        "likes":likes, "comments":reps, "shares":rts+qts,
        "engagement":likes+rts+reps+qts, "is_repost":False,
    }


def _load(name):
    f = RAW / name
    return json.loads(f.read_text()) if f.exists() else []


def build():
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    x_cutoff = now_ms - X_DAYS * 86400 * 1000
    raw_posts = []

    for it in _load("li_profiles.json"):
        tgt = (it.get("query") or {}).get("targetUrl", "").rstrip("/") + "/"
        person = LI_VOICES.get(tgt) or (it.get("author") or {}).get("name") or "Key Voice"
        raw_posts.append(norm_li(it, "voice", person, now_ms))
    for it in _load("li_keywords.json"):
        label = KEYWORDS.get((it.get("query") or {}).get("search",""),
                             (it.get("query") or {}).get("search") or "Keyword")
        raw_posts.append(norm_li(it, "keyword", label, now_ms))
    for it in _load("x_keywords.json"):
        p = norm_x_search(it, now_ms)
        if p["ts_ms"] and p["ts_ms"] < x_cutoff:   # keep last X_DAYS only
            continue
        raw_posts.append(p)
    for it in _load("x_profiles.json"):
        p = norm_x_profile(it, now_ms)
        if not p: continue
        if p["ts_ms"] and p["ts_ms"] < x_cutoff:
            continue
        raw_posts.append(p)

    # quality filter + dedupe
    posts, seen = [], set()
    for p in raw_posts:
        if not p["text"]:
            continue
        floor = MIN_LIKES_VOICE if p["source"] == "voice" else MIN_LIKES_INDUSTRY
        if p["likes"] < floor:
            continue
        key = p["url"] or (p["author"] + p["text"][:80])
        if key in seen:
            continue
        seen.add(key)
        posts.append(p)

    posts.sort(key=lambda p: p["engagement"], reverse=True)   # most engaging first

    run_at = datetime.now(timezone.utc)
    payload = {"run_at": run_at.isoformat(), "posts": posts}
    DATA.mkdir(exist_ok=True)
    (DATA / f"{run_at:%Y-%m-%d}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2))
    render(payload)

    def c(src=None, plat=None):
        return sum(1 for p in posts
                   if (src is None or p["source"]==src) and (plat is None or p["platform"]==plat))
    print(f"  ✓ Dashboard built: {len(posts)} posts → {DASH.name}")
    print(f"      LinkedIn: {c(plat='linkedin')}  (voices {c('voice','linkedin')}, industry {c('keyword','linkedin')})")
    print(f"      X:        {c(plat='x')}  (voices {c('voice','x')}, industry {c('keyword','x')})")


# ── Dashboard ─────────────────────────────────────────────────────────────
def render(payload):
    posts  = payload["posts"]
    run_dt = datetime.fromisoformat(payload["run_at"])
    voices = list(dict.fromkeys(list(LI_VOICES.values()) + list(X_VOICES.values())))
    voices.sort()
    kw = list(dict.fromkeys(KEYWORDS.values()))
    html_out = DASHBOARD_TEMPLATE.format(
        updated = run_dt.strftime("%A %d %B %Y, %H:%M UTC"),
        total   = len(posts),
        n_voice = sum(1 for p in posts if p["source"]=="voice"),
        n_kw    = sum(1 for p in posts if p["source"]=="keyword"),
        n_li    = sum(1 for p in posts if p["platform"]=="linkedin"),
        n_x     = sum(1 for p in posts if p["platform"]=="x"),
        voices  = json.dumps(voices, ensure_ascii=False),
        keywords= json.dumps(kw, ensure_ascii=False),
        data    = json.dumps(posts, ensure_ascii=False),
    )
    DASH.write_text(html_out, encoding="utf-8")
    # also write index.html so GitHub Pages serves the dashboard at the root URL
    (BASE / "index.html").write_text(html_out, encoding="utf-8")


DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Northstar Growth · Social Listener</title>
<style>
  :root{{--bg:#0b1220;--card:#141d2e;--card2:#1b2740;--line:#26334d;
        --txt:#e6edf7;--mut:#8aa0c0;--accent:#3b82f6;--voice:#f59e0b;--kw:#22d3ee;
        --li:#0a66c2;--x:#1d9bf0;}}
  *{{box-sizing:border-box}}
  body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       background:var(--bg);color:var(--txt);line-height:1.5}}
  header{{padding:24px 20px 16px;border-bottom:1px solid var(--line);
         position:sticky;top:0;background:rgba(11,18,32,.94);backdrop-filter:blur(8px);z-index:10}}
  h1{{margin:0;font-size:19px}} h1 span{{color:var(--accent)}}
  .sub{{color:var(--mut);font-size:13px;margin-top:4px}}
  .stats{{display:flex;gap:14px;margin-top:12px;flex-wrap:wrap}}
  .stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:7px 13px}}
  .stat b{{font-size:17px}} .stat span{{color:var(--mut);font-size:11px;display:block}}
  .barrow{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:14px}}
  .tab{{padding:7px 15px;border-radius:999px;border:1px solid var(--line);background:var(--card);
       color:var(--mut);cursor:pointer;font-size:13px;font-weight:600}}
  .tab.active{{background:var(--accent);color:#fff;border-color:var(--accent)}}
  .seg{{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}}
  .seg div{{padding:7px 13px;cursor:pointer;font-size:12px;color:var(--mut);background:var(--card)}}
  .seg div.active{{color:#fff}}
  .seg div.active[data-plat=all]{{background:var(--accent)}}
  .seg div.active[data-plat=linkedin]{{background:var(--li)}}
  .seg div.active[data-plat=x]{{background:#111}}
  input[type=search]{{flex:1;min-width:180px;background:var(--card);border:1px solid var(--line);
       color:var(--txt);padding:9px 12px;border-radius:9px;font-size:14px}}
  select{{background:var(--card);border:1px solid var(--line);color:var(--txt);
       padding:9px 12px;border-radius:9px;font-size:13px}}
  .chips{{display:flex;gap:6px;flex-wrap:wrap;margin-top:11px;max-height:104px;overflow-y:auto}}
  .chip{{padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:var(--card);
        color:var(--mut);cursor:pointer;font-size:12px}}
  .chip.active{{background:var(--card2);color:var(--txt);border-color:var(--accent)}}
  main{{max-width:760px;margin:0 auto;padding:20px 14px 80px}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px 17px;margin-bottom:13px}}
  .card:hover{{border-color:#34507f}}
  .row{{display:flex;align-items:center;gap:11px}}
  .av{{width:42px;height:42px;border-radius:50%;background:var(--card2);flex:none;object-fit:cover;
      font-weight:700;display:flex;align-items:center;justify-content:center;color:var(--mut);font-size:14px}}
  .name{{font-weight:700;font-size:15px}}
  .head{{color:var(--mut);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:420px}}
  .meta{{margin-left:auto;text-align:right;color:var(--mut);font-size:12px;white-space:nowrap}}
  .pill{{display:inline-block;font-size:10px;font-weight:700;padding:2px 7px;border-radius:5px;margin-right:5px}}
  .p-li{{background:rgba(10,102,194,.18);color:#4d9fe8;border:1px solid rgba(10,102,194,.4)}}
  .p-x{{background:rgba(255,255,255,.08);color:#cfd8e6;border:1px solid #3a475e}}
  .badge{{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:999px;margin-top:9px}}
  .b-voice{{background:rgba(245,158,11,.15);color:var(--voice);border:1px solid rgba(245,158,11,.35)}}
  .b-kw{{background:rgba(34,211,238,.12);color:var(--kw);border:1px solid rgba(34,211,238,.3)}}
  .b-rep{{background:var(--card2);color:var(--mut);border:1px solid var(--line);margin-left:6px}}
  .text{{margin:11px 0 0;white-space:pre-wrap;font-size:14.5px}}
  .text.clamp{{display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden}}
  .more{{color:var(--accent);cursor:pointer;font-size:13px;margin-top:6px;display:inline-block}}
  .foot{{display:flex;gap:16px;align-items:center;margin-top:13px;color:var(--mut);font-size:13px}}
  .foot a{{margin-left:auto;color:var(--accent);text-decoration:none;font-weight:600}}
  .empty{{text-align:center;color:var(--mut);padding:60px 20px}}
</style></head>
<body>
<header>
  <h1>⭐ Northstar Growth · <span>Social Listener</span></h1>
  <div class="sub">LinkedIn + X · sorted by engagement · updated {updated}</div>
  <div class="stats">
    <div class="stat"><b>{total}</b><span>posts</span></div>
    <div class="stat"><b>{n_voice}</b><span>key voices</span></div>
    <div class="stat"><b>{n_kw}</b><span>industry</span></div>
    <div class="stat"><b>{n_li}</b><span>LinkedIn</span></div>
    <div class="stat"><b>{n_x}</b><span>X</span></div>
  </div>
  <div class="barrow">
    <div class="tab active" data-src="all">All</div>
    <div class="tab" data-src="voice">⭐ Key Voices</div>
    <div class="tab" data-src="keyword"># The Industry</div>
    <div class="seg" id="plat">
      <div data-plat="all" class="active">All</div>
      <div data-plat="linkedin">in</div>
      <div data-plat="x">𝕏</div>
    </div>
  </div>
  <div class="barrow">
    <input type="search" id="q" placeholder="Search posts, people, topics…">
    <select id="sort">
      <option value="engagement">Most engagement</option>
      <option value="recent">Most recent</option>
    </select>
  </div>
  <div class="chips" id="chips"></div>
</header>
<main id="feed"></main>
<script>
const POSTS={data}, VOICES={voices}, KEYWORDS={keywords};
let state={{src:"all", plat:"all", bucket:null, q:"", sort:"engagement"}};
const chipsEl=document.getElementById("chips");
function renderChips(){{
  let b = state.src==="voice"?VOICES : state.src==="keyword"?KEYWORDS : [];
  chipsEl.innerHTML="";
  b.forEach(x=>{{const c=document.createElement("div");
    c.className="chip"+(state.bucket===x?" active":""); c.textContent=x;
    c.onclick=()=>{{state.bucket=state.bucket===x?null:x; renderChips(); draw();}};
    chipsEl.appendChild(c);}});
}}
function esc(s){{return (s||"").replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));}}
function initials(n){{return (n||"?").replace(/[^A-Za-z ]/g,"").split(" ").filter(Boolean).slice(0,2).map(w=>w[0]).join("").toUpperCase()||"?";}}
function fmt(n){{return n>=1000?(n/1000).toFixed(1).replace(/\.0$/,'')+"k":n;}}
function draw(){{
  let l=POSTS.slice();
  if(state.src!=="all")  l=l.filter(p=>p.source===state.src);
  if(state.plat!=="all") l=l.filter(p=>p.platform===state.plat);
  if(state.bucket)       l=l.filter(p=>p.bucket===state.bucket);
  if(state.q){{const q=state.q.toLowerCase();
    l=l.filter(p=>(p.text+" "+p.author+" "+p.bucket).toLowerCase().includes(q));}}
  l.sort((a,b)=> state.sort==="recent"? b.ts_ms-a.ts_ms : b.engagement-a.engagement);
  const feed=document.getElementById("feed");
  if(!l.length){{feed.innerHTML='<div class="empty">No posts match.</div>';return;}}
  feed.innerHTML=l.map(p=>{{
    const av=p.avatar
      ?`<img class="av" src="${{esc(p.avatar)}}" referrerpolicy="no-referrer" onerror="this.replaceWith(Object.assign(document.createElement('div'),{{className:'av',textContent:'${{initials(p.author)}}'}}))">`
      :`<div class="av">${{initials(p.author)}}</div>`;
    const plat=p.platform==="linkedin"?`<span class="pill p-li">in</span>`:`<span class="pill p-x">𝕏</span>`;
    const badge=p.source==="voice"?`<span class="badge b-voice">⭐ ${{esc(p.bucket)}}</span>`
                                   :`<span class="badge b-kw"># ${{esc(p.bucket)}}</span>`;
    const rep=p.is_repost?`<span class="badge b-rep">↻ repost</span>`:"";
    const long=(p.text||"").length>360;
    return `<div class="card">
      <div class="row">${{av}}
        <div style="min-width:0"><div class="name">${{esc(p.author)}}</div>
        <div class="head">${{esc(p.headline)}}</div></div>
        <div class="meta">${{esc(p.ago)}}</div></div>
      <div>${{plat}}${{badge}}${{rep}}</div>
      <div class="text ${{long?'clamp':''}}">${{esc(p.text)}}</div>
      ${{long?`<span class="more" onclick="this.previousElementSibling.classList.toggle('clamp');this.textContent=this.textContent.includes('Show')?'Show less':'Show more'">Show more</span>`:''}}
      <div class="foot"><span>👍 ${{fmt(p.likes)}}</span><span>💬 ${{fmt(p.comments)}}</span><span>🔁 ${{fmt(p.shares)}}</span>
        ${{p.url?`<a href="${{esc(p.url)}}" target="_blank">Open →</a>`:''}}</div></div>`;
  }}).join("");
}}
document.querySelectorAll(".tab").forEach(t=>t.onclick=()=>{{
  document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));
  t.classList.add("active"); state.src=t.dataset.src; state.bucket=null; renderChips(); draw();}});
document.querySelectorAll("#plat div").forEach(d=>d.onclick=()=>{{
  document.querySelectorAll("#plat div").forEach(x=>x.classList.remove("active"));
  d.classList.add("active"); state.plat=d.dataset.plat; draw();}});
document.getElementById("q").oninput=e=>{{state.q=e.target.value; draw();}};
document.getElementById("sort").onchange=e=>{{state.sort=e.target.value; draw();}};
renderChips(); draw();
</script>
</body></html>"""


def main():
    args = sys.argv[1:]
    print("\n  ⭐ Northstar Growth · Social Listener (LinkedIn + X)")
    print("  ───────────────────────────────────────────────────")
    if "--build" in args:
        print("  Rebuilding from last saved raw data (no scrape)…")
        build()
    else:
        token = get_token()
        if not token:
            sys.exit("\n  ✗ No Apify token. Put APIFY_TOKEN=... in social_listener/.env\n"
                     "    (or run  python3 listen.py --build  to rebuild offline)\n")
        scrape(token)
        build()
    print("  Open:  file://%s\n" % DASH.resolve())


if __name__ == "__main__":
    main()
