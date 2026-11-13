"""AniList 分数缓存 + 双评分徽章渲染。独立模块。"""
import json
import os
import urllib.request

SCORE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "scores.json")
_ANILIST = "https://graphql.anilist.co"


def load():
    try:
        with open(SCORE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(cache):
    os.makedirs(os.path.dirname(SCORE_PATH), exist_ok=True)
    with open(SCORE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)


_SCORES = load()
_QUOTA = 60


def anilist(query):
    body = json.dumps({"query": "query($s:String){Media(search:$s,type:ANIME){averageScore popularity}}",
                       "variables": {"s": query}}).encode()
    req = urllib.request.Request(_ANILIST, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "dsh-animebar/0.5"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        m = (data.get("data") or {}).get("Media") or {}
        if not m.get("averageScore"):
            return None
        return {"score": m["averageScore"], "pop": m.get("popularity") or 0}
    except Exception:
        return None


def alt(zh, orig):
    global _QUOTA
    key = f"{zh}|{orig}"
    if key in _SCORES:
        return _SCORES[key] or None
    if _QUOTA <= 0:
        return None
    _QUOTA -= 1
    for q in (orig, zh):
        if not q:
            continue
        got = anilist(q)
        if got:
            _SCORES[key] = got
            return got
    _SCORES[key] = None
    return None


def flush():
    save(_SCORES)


def badges(bgm, meta):
    """封面右上角的双评分徽章 HTML。"""
    al = f"{meta['score']/10:.1f}" if meta else ""
    diff = abs(bgm - meta["score"] / 10) if (meta and bgm) else 0
    cls = " score-hi" if diff >= 1.5 else ""
    al_html = f'<span class="score alt">{al}</span>' if al else '<span class="score alt">—</span>'
    return f'<span class="scores{cls}"><span class="score bgm">{bgm:.1f}</span>{al_html}</span>'
