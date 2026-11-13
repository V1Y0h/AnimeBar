"""日文片名缓存：原名不是日文时，从 Bangumi 别名里找日文名。"""
import json
import os
import urllib.request

CACHE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "ja-titles.json")
UA = {"User-Agent": "dsh-animebar/0.5"}


def _has_kana(s):
    return any(0x3040 <= ord(c) <= 0x30FF for c in s)


def load():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)


_CACHE = load()
_QUOTA = 40


def _alias_kana(detail):
    for row in (detail.get("infobox") or []):
        if row.get("key") not in ("别名", "日文名"):
            continue
        val = row.get("value")
        items = val if isinstance(val, list) else [{"v": val}]
        for it in items:
            v = it.get("v") if isinstance(it, dict) else str(it)
            if v and _has_kana(v):
                return v
    return ""


def lookup(orig):
    """返回日文名；查不到就返回原名。"""
    if not orig:
        return orig
    if _has_kana(orig):
        return orig
    if orig in _CACHE:
        return _CACHE[orig] or orig
    global _QUOTA
    if _QUOTA <= 0:
        return orig
    _QUOTA -= 1
    # 1) 搜索拿 id
    try:
        body = json.dumps({"keyword": orig, "filter": {"type": [2]}}).encode()
        req = urllib.request.Request("https://api.bgm.tv/v0/search/subjects?limit=1",
                                     data=body, headers={"Content-Type": "application/json", **UA}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            rows = json.load(r).get("data", [])
        sid = rows[0]["id"] if rows else None
        if sid is None:
            _CACHE[orig] = None
            return orig
        # 2) 详情拿别名
        req2 = urllib.request.Request(f"https://api.bgm.tv/v0/subjects/{sid}", headers=UA)
        with urllib.request.urlopen(req2, timeout=20) as r:
            detail = json.load(r)
        ja = _alias_kana(detail)
        _CACHE[orig] = ja or None
        return ja or orig
    except Exception:
        _CACHE[orig] = None
        return orig


def flush():
    save(_CACHE)
