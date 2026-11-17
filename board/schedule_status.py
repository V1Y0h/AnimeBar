"""判定放送表里的条目是否真的在「本周更新」。

Bangumi 的 /calendar 返回的是「作品在星期几播出」，不是「本周这一天有没有新一集」。
于是两类作品会一直挂在表里：

  已完结   —— 上一季甚至更早播完的，Bangumi 不会自动摘掉
  一次性放出 —— 全季同一天上线（Netflix 式），从来没有周更

判定只看分集数据，规则确定，不猜平台：

  一次性放出 = 所有集放送日期相同 且 总集数 > 1
  已完结     = 收录集数 ≥ 总集数 且 最后一集日期 + 7 天 ≤ 今天

拿不到分集数据的条目一律保留（判不了就别删，宁可多留）。
结果缓存到 assets/schedule-status.json，6 小时内不重复请求。
"""

import datetime
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "dsh-agent/1.0 (personal use)"}
SUBJECT = "https://api.bgm.tv/v0/subjects/{}"
EPISODES = "https://api.bgm.tv/v0/episodes?subject_id={}&type=0&limit=100"

ANILIST = "https://graphql.anilist.co"
ANILIST_QUERY = """
query ($q: String) {
  Page(perPage: 3) {
    media(search: $q, type: ANIME, sort: SEARCH_MATCH) {
      status
      episodes
      title { romaji english native }
      synonyms
    }
  }
}
"""

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
CACHE_PATH = os.path.join(ASSETS, "schedule-status.json")
CACHE_TTL = 6 * 3600

WEEKLY = "weekly"
ENDED = "ended"
BATCH = "batch"
UNKNOWN = "unknown"


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    return None


def _parse(value):
    """分集日期可能是 '2027' / '2026-10' / '2026-10-20'，只接受能解析的。"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("entries"), dict):
            return data
    except Exception:
        pass
    return {"checked_at": 0, "entries": {}}


def _save_cache(entries):
    os.makedirs(ASSETS, exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"checked_at": int(time.time()), "entries": entries}, f,
                  ensure_ascii=False, indent=1)
    os.replace(tmp, CACHE_PATH)


def _norm(text):
    """归一化标题：去标点/空白，统一大小写。中日文保留字符。"""
    if not text:
        return ""
    keep = [ch.lower() for ch in text if ch.isalnum()]
    return "".join(keep)


def _anilist_status(names):
    """按标题查 AniList。只有严格匹配才采用，否则返回 None 交给启发式。"""
    candidates = [_norm(n) for n in names if n]
    candidates = [c for c in candidates if len(c) >= 3]
    if not candidates:
        return None

    payload = json.dumps({"query": ANILIST_QUERY, "variables": {"q": names[0]}}).encode()
    req = urllib.request.Request(
        ANILIST,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "dsh-agent/1.0 (personal use)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception:
        return None

    media = ((data.get("data") or {}).get("Page") or {}).get("media") or []
    for m in media:
        titles = [m.get("title", {}).get(k) for k in ("romaji", "english", "native")]
        titles += m.get("synonyms") or []
        for t in titles:
            n = _norm(t)
            if not n:
                continue
            # 严格匹配：完全相等，或一方包含另一方且长度接近
            if n in candidates:
                return {"status": m.get("status"), "episodes": m.get("episodes"), "matched": t}
            for c in candidates:
                if (n in c or c in n) and abs(len(n) - len(c)) <= 4 and min(len(n), len(c)) >= 5:
                    return {"status": m.get("status"), "episodes": m.get("episodes"), "matched": t}
    return None


def _classify_one(subject_id, today):
    sub = _get(SUBJECT.format(subject_id)) or {}
    eps = _get(EPISODES.format(subject_id)) or {}
    data = eps.get("data") or []
    total = sub.get("total_episodes") or 0
    dates = [d for d in (_parse(e.get("airdate")) for e in data) if d]
    dates.sort()

    # 本地分集数据里还有未来日期的集数 → 一定在播，不再听信外部判定
    # （标题匹配会误中同名作品，之前就这样误藏过还在播的番）
    if dates and dates[-1] > today:
        return {"kind": WEEKLY, "source": "local", "total": total, "epcount": len(data),
                "last": dates[-1].isoformat()}

    # 本地看不出未来集数时，再用 AniList 的片方状态兜底
    al = _anilist_status([sub.get("name"), sub.get("name_cn")])
    if al:
        status = al.get("status")
        if status in ("FINISHED", "CANCELLED"):
            return {"kind": ENDED, "source": "anilist", "matched": al.get("matched"),
                    "total": total, "epcount": len(data)}
        if status == "RELEASING":
            return {"kind": WEEKLY, "source": "anilist", "matched": al.get("matched"),
                    "total": total, "epcount": len(data)}
    if not dates:
        return {"kind": UNKNOWN, "total": total, "epcount": len(data)}

    first, last = dates[0], dates[-1]
    if len(set(dates)) == 1 and total > 1:
        return {"kind": BATCH, "total": total, "epcount": len(data), "last": last.isoformat()}
    if first > today:
        return {"kind": UNKNOWN, "total": total, "epcount": len(data), "reason": "upcoming"}
    if total and len(data) >= total and (last + datetime.timedelta(days=7)) <= today:
        return {"kind": ENDED, "total": total, "epcount": len(data), "last": last.isoformat()}
    return {"kind": WEEKLY, "total": total, "epcount": len(data), "last": last.isoformat()}


def classify_all(subject_ids, today=None, force=False, log=print):
    """返回 {subject_id: kind}。缓存未过期且覆盖所有 id 时直接复用。"""
    today = today or datetime.date.today()
    cache = _load_cache()
    entries = cache["entries"]
    fresh = (time.time() - cache["checked_at"]) < CACHE_TTL
    missing = [i for i in subject_ids if str(i) not in entries]

    if fresh and not missing and not force:
        log("   放送状态：用缓存")
    else:
        todo = subject_ids if force else missing
        if todo:
            log(f"   放送状态：查询 {len(todo)} 部（分集数据，4 并发）")

        def work(sid):
            try:
                return sid, _classify_one(sid, today)
            except Exception:
                return sid, {"kind": UNKNOWN}  # 查不到就算未知，保留

        done = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            for sid, result in pool.map(work, todo):
                entries[str(sid)] = result
                done += 1
                if done % 20 == 0:
                    log(f"     {done}/{len(todo)}")
        _save_cache(entries)

    return {i: entries.get(str(i), {}).get("kind", UNKNOWN) for i in subject_ids}


def drop_finished(items, today=None, force=False, log=print):
    """去掉已完结与一次性放出的条目，其余原样返回。"""
    kinds = classify_all([i["id"] for i in items], today=today, force=force, log=log)
    kept, dropped = [], []
    for it in items:
        kind = kinds.get(it["id"], UNKNOWN)
        if kind in (ENDED, BATCH):
            dropped.append((it, kind))
        else:
            kept.append(it)
    return kept, dropped
