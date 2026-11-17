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

UA = {"User-Agent": "dsh-agent/1.0 (personal use)"}
SUBJECT = "https://api.bgm.tv/v0/subjects/{}"
EPISODES = "https://api.bgm.tv/v0/episodes?subject_id={}&type=0&limit=100"

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


def _classify_one(subject_id, today):
    sub = _get(SUBJECT.format(subject_id)) or {}
    eps = _get(EPISODES.format(subject_id)) or {}
    data = eps.get("data") or []
    total = sub.get("total_episodes") or 0
    dates = [d for d in (_parse(e.get("airdate")) for e in data) if d]
    dates.sort()

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
            log(f"   放送状态：查询 {len(todo)} 部（分集数据）")
        for n, sid in enumerate(todo, 1):
            entries[str(sid)] = _classify_one(sid, today)
            if n % 20 == 0:
                log(f"     {n}/{len(todo)}")
            time.sleep(0.12)
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
