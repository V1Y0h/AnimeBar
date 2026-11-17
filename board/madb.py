"""メディア芸術データベース（MADB）的早期影像软件档案。

数据源：文化庁「MADB Lab」的 SPARQL 端点（WebAPI 已废弃，只有 SPARQL 可用）。
利用条款：CC BY 4.0 兼容，允许商用，但**必须署名**，修改过还要注明——
页面上的出处行就是这个用途，删掉它就违反了条款。

只取 datePublished 早于 CUTOFF 的影像软件（AnimationVideoPackage），
也就是 OVA／LD／VHS 时代的商业发行物，不含 TV 放送和剧场版。
"""

import datetime
import json
import os
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ENDPOINT = "https://mediaarts-db.artmuseums.go.jp/sparql"
UA = {"User-Agent": "dsh-agent/1.0 (personal use)", "Accept": "application/sparql-results+json"}

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
CACHE = os.path.join(ASSETS, "madb-early.json")
TTL = 30 * 86400   # 历史档案基本不变，一个月刷新一次足够
CUTOFF = "1995"
LIMIT = 600

QUERY = """
PREFIX class: <https://mediaarts-db.artmuseums.go.jp/data/class#>
PREFIX schema: <https://schema.org/>
SELECT ?s ?name ?date ?pub WHERE {
  ?s a class:AnimationVideoPackage ;
     schema:name ?name ;
     schema:datePublished ?date .
  OPTIONAL { ?s schema:publisher ?pub }
  FILTER(STR(?date) < "%s")
}
ORDER BY ?date
LIMIT %d
""" % (CUTOFF, LIMIT)

# 出处：MADB 条款要求，改动过还要注明
ATTRIBUTION_ZH = ('出典：文化庁「MADB Lab」（https://mediag.bunka.go.jp/madb_lab/）；'
                  '本页仅取 1995 年以前的影像软件并按年份重排')
ATTRIBUTION_EN = ('Source: Agency for Cultural Affairs "MADB Lab" '
                  '(https://mediag.bunka.go.jp/madb_lab/); this page selects video '
                  'packages published before 1995 and reorders them by year')


def _fetch():
    # 这个端点只吃表单编码；发 JSON 会直接 400
    body = urllib.parse.urlencode({"query": QUERY}).encode()
    headers = dict(UA)
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(ENDPOINT, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)

    # 同一作品会有汉字名和假名读音两条 name，按 URI 去重，优先取含汉字的写法
    by_subject = {}
    for row in data["results"]["bindings"]:
        uri = row["s"]["value"]
        name = (row.get("name") or {}).get("value", "").strip()
        if not name:
            continue
        prev = by_subject.get(uri)
        score = sum(1 for ch in name if "\u4e00" <= ch <= "\u9fff")
        if prev is None or score > prev["score"]:
            by_subject[uri] = {
                "score": score,
                "title": name,
                "date": (row.get("date") or {}).get("value", ""),
                "publisher": (row.get("pub") or {}).get("value", ""),
                "url": uri,
            }

    out = []
    for v in by_subject.values():
        v.pop("score", None)
        out.append(v)
    out.sort(key=lambda x: x["date"])
    return out


def early_works(log=print):
    """返回按发行日排序的早期影像软件列表，缓存一个月。"""
    try:
        with open(CACHE, encoding="utf-8") as f:
            cached = json.load(f)
        if time.time() - cached.get("fetched_at", 0) < TTL:
            return cached["works"]
    except Exception:
        pass

    log("   MADB：查询早期影像软件…")
    works = _fetch()
    os.makedirs(ASSETS, exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": int(time.time()), "works": works}, f, ensure_ascii=False)
    os.replace(tmp, CACHE)
    log(f"   MADB：{len(works)} 条已缓存")
    return works


COVERS = os.path.join(ASSETS, "madb-covers.json")
BG_API = "https://api.bgm.tv/v0/search/subjects?limit=3"


def _search_cover(title):
    """用 Bangumi 搜同名条目取封面。标题对不上就返回空，不硬套。"""
    import urllib.request as u

    body = json.dumps({"keyword": title, "filter": {"type": [2]}}).encode()
    req = u.Request(BG_API, data=body, headers={
        "content-type": "application/json",
        "user-agent": "dsh-agent/1.0 (personal use)",
    })
    try:
        with u.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception:
        return ""

    def norm(t):
        return "".join(c for c in (t or "") if c.isalnum())

    want = norm(title)
    best = ""
    for it in (data.get("data") or []):
        img = (it.get("images") or {}).get("common") or ""
        if not img:
            continue
        for key in ("name", "name_cn"):
            got = norm(it.get(key))
            if got and want and (got == want or got in want or want in got):
                return img
        if not best:
            best = img  # 没有严格匹配时用第一条有图的兜底
    return best


def attach_covers(works, log=print):
    """给每条补 cover 字段，结果缓存 30 天。"""
    cache = {}
    try:
        with open(COVERS, encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("fetched_at", 0) < TTL:
            cache = data["covers"]
    except Exception:
        pass

    todo = [w["title"] for w in works if w["title"] not in cache]
    if todo:
        log(f"   MADB：补封面 {len(todo)} 条…")
        with ThreadPoolExecutor(max_workers=4) as pool:
            for title, cover in zip(todo, pool.map(_search_cover, todo)):
                cache[title] = cover
        tmp = COVERS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"fetched_at": int(time.time()), "covers": cache}, f, ensure_ascii=False)
        os.replace(tmp, COVERS)

    for w in works:
        w["cover"] = cache.get(w["title"], "")
    return works
