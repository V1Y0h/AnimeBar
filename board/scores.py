"""多平台评分缓存：AniList、Kitsu（Bangumi 来自页面数据）。独立模块。"""
import json
import os
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
AL_PATH = os.path.join(HERE, "assets", "scores.json")
KIT_PATH = os.path.join(HERE, "assets", "kitsu.json")
_ANILIST = "https://graphql.anilist.co"
_KITSU = "https://kitsu.io/api/edge/anime"


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(cache, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)


_AL = _load(AL_PATH)
_KIT = _load(KIT_PATH)
_QUOTA = 60


def _anilist(query):
    body = json.dumps({"query": "query($s:String){Media(search:$s,type:ANIME){averageScore popularity}}",
                       "variables": {"s": query}}).encode()
    req = urllib.request.Request(_ANILIST, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "dsh-animebar/0.6"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        m = (data.get("data") or {}).get("Media") or {}
        return {"score": m.get("averageScore"), "pop": m.get("popularity") or 0} if m.get("averageScore") else None
    except Exception:
        return None


def _kitsu(query):
    q = urllib.parse.quote(query)
    req = urllib.request.Request(f"{_KITSU}?filter%5Btext%5D={q}&page%5Blimit%5D=1",
                                 headers={"User-Agent": "dsh-animebar/0.6"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        d = (data.get("data") or [{}])[0].get("attributes") or {}
        return {"score": d.get("averageRating"), "pop": d.get("userCount") or 0} if d.get("averageRating") else None
    except Exception:
        return None


def _cached(cache, fn, zh, orig):
    global _QUOTA
    key = f"{zh}|{orig}"
    if key in cache:
        return cache[key] or None
    if _QUOTA <= 0:
        return None
    _QUOTA -= 1
    for q in (orig, zh):
        if not q:
            continue
        got = fn(q)
        if got:
            cache[key] = got
            return got
    cache[key] = None
    return None


def alt(zh, orig):
    return _cached(_AL, _anilist, zh, orig)


def kitsu_alt(zh, orig):
    return _cached(_KIT, _kitsu, zh, orig)


def flush():
    _save(_AL, AL_PATH)
    _save(_KIT, KIT_PATH)


def badges(bgm, al, kit):
    """封面右上角多平台评分徽章。"""
    def one(label, meta):
        if not meta or not meta.get("score"):
            return ""
        try:
            v = float(meta["score"])
        except (TypeError, ValueError):
            return ""
        return f'<span class="score {label}">{label} {v/10:.1f}</span>'

    parts = []
    if bgm:
        parts.append(f'<span class="score bgm">BGM {bgm:.1f}</span>')
    parts.append(one("AniList", al))
    parts.append(one("Kitsu", kit))
    parts = [p for p in parts if p]
    if not parts:
        return '<span class="score">—</span>'
    return '<span class="scores">' + "".join(parts) + '</span>'
