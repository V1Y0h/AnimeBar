"""从しょぼいカレンダー取精确放送时间与频道。

Bangumi 只知道「这部在星期几播」，しょぼいカレンダー 知道「TOKYO MX 周二 24:30」，
还有每一集的 StTime，因此相邻两集的间隔超过 7 天就能看出中间停播过。

用法只做**增量显示**：拿不到就什么都不显示，绝不因此隐藏作品。

接口要点（2026-11 实测）：
  - TitleLookup 的 Title 参数已废除，只能 TID=* 拉全量（约 780KB）再本地匹配
  - ProgLookup 的 TID 支持逗号分隔，一次可以查很多部
  - Flag 字段的位含义没有公开文档，所以停播判定改用「相邻集时间差」，不猜 Flag
"""

import datetime
import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "dsh-agent/1.0 (personal use)"}
DB = "https://cal.syoboi.jp/db.php"

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
TITLES_CACHE = os.path.join(ASSETS, "syoboi-titles.json")
SCHEDULE_CACHE = os.path.join(ASSETS, "syoboi-schedule.json")
TITLES_TTL = 7 * 86400      # 标题表一周更新一次足够
SCHEDULE_TTL = 6 * 3600     # 放送表 6 小时


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _norm(text):
    keep = []
    for ch in text or "":
        if ch.isalnum() or "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
            keep.append(ch.lower())
    return "".join(keep)


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_json(path, data):
    os.makedirs(ASSETS, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def titles(log=print):
    """返回 {归一化标题: [TID, 原标题]}，缓存一周。"""
    cached = _load_json(TITLES_CACHE)
    if cached and time.time() - cached.get("fetched_at", 0) < TITLES_TTL:
        return {k: tuple(v) for k, v in cached["map"].items()}

    log("   Syoboi：拉取全量标题表…")
    raw = _get(f"{DB}?Command=TitleLookup&TID=*&Fields=TID,Title")
    root = ET.fromstring(raw)
    table = {}
    for item in root.iter("TitleItem"):
        tid = item.findtext("TID")
        title = item.findtext("Title")
        if tid and title:
            table[_norm(title)] = [tid, title]
    _save_json(TITLES_CACHE, {"fetched_at": int(time.time()), "map": table})
    log(f"   Syoboi：{len(table)} 条标题已缓存")
    return {k: tuple(v) for k, v in table.items()}


def match(tid_table, name):
    """标题匹配：先要求完全相等，再允许长度接近的包含关系。拿不准就返回 None。"""
    key = _norm(name)
    if not key or len(key) < 4:
        return None
    if key in tid_table:
        return tid_table[key]
    best = None
    for other, value in tid_table.items():
        if len(other) < 5:
            continue
        if key in other or other in key:
            if abs(len(key) - len(other)) <= 3:
                if best is None or len(other) > len(best[1]):
                    best = value + (other,)
    return (best[0], best[1]) if best else None


def schedule(items, log=print):
    """返回 {bangumi_id: {tid, title, time, channel, weekday}}，只含匹配上的。"""
    cached = _load_json(SCHEDULE_CACHE)
    if cached and time.time() - cached.get("fetched_at", 0) < SCHEDULE_TTL:
        return cached["entries"]

    tid_table = titles(log=log)
    matched = {}
    for it in items:
        m = match(tid_table, it.get("name") or "")
        if m:
            matched[str(it["id"])] = m
    log(f"   Syoboi：标题匹配上 {len(matched)}/{len(items)} 部")
    if not matched:
        return {}

    # 一次查未来两周的节目（TID 逗号分隔）
    now = datetime.datetime.now()
    start = (now - datetime.timedelta(days=8)).strftime("%Y%m%d_000000")
    end = (now + datetime.timedelta(days=20)).strftime("%Y%m%d_000000")
    tids = ",".join(sorted({m[0] for m in matched.values()}))
    raw = _get(f"{DB}?Command=ProgLookup&TID={tids}&Range={start}-{end}"
               "&Fields=TID,StTime,Count,ChID&JOIN=SubTitles&STSubTitle=1")

    # 首播频道：同一天可能有重播台，只看主台才不会把星期搞错
    first_ch = {}
    try:
        raw_t = _get(f"{DB}?Command=TitleLookup&TID={tids}&Fields=TID,FirstCh")
        for t in ET.fromstring(raw_t).iter("TitleItem"):
            tid = t.findtext("TID")
            ch = (t.findtext("FirstCh") or "").strip()
            if tid and ch and ch != "0":
                first_ch[tid] = ch
    except Exception:
        first_ch = {}  # 拿不到就不过滤，退回全部频道

    ch_names = channel_names(log=log)
    # FirstCh 给的是频道名，节目里是 ChID，得反查
    ch_ids = {name: cid for cid, name in ch_names.items()}
    progs = {}
    root = ET.fromstring(raw)
    for p in root.iter("ProgItem"):
        tid = p.findtext("TID")
        st = p.findtext("StTime")
        chid = p.findtext("ChID")
        count = p.findtext("Count")
        if not (tid and st):
            continue
        progs.setdefault(tid, []).append({
            "st": st,
            "chid": chid,
            "count": count,
            "sub": p.findtext("STSubTitle") or "",
        })

    entries = {}
    for bgm_id, (tid, title) in matched.items():
        all_rows = progs.get(tid, [])
        main = ch_ids.get(first_ch.get(tid, ""))
        rows = [r for r in all_rows if r.get("chid") == main] if main else all_rows
        if not rows:
            rows = all_rows
        rows = sorted(rows, key=lambda x: x["st"])
        if not rows:
            continue
        # 只取「现在之后最近的一场」；窗口里更早的多半是重播或上一集
        now_key = now.strftime("%Y-%m-%d %H:%M:%S")
        upcoming = [r for r in rows if r["st"] >= now_key]
        if not upcoming:
            continue
        pick = upcoming[0]
        try:
            when = datetime.datetime.strptime(pick["st"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        # 停播判定：相邻两集间隔超过 8 天，说明中间空过一周
        gap_week = False
        for a, b in zip(rows, rows[1:]):
            try:
                da = datetime.datetime.strptime(a["st"], "%Y-%m-%d %H:%M:%S")
                db = datetime.datetime.strptime(b["st"], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if (db - da).days >= 13:
                gap_week = True
                break
        # 与 Bangumi 的星期不一致时不显示：宁可少一行，也不要给两条矛盾信息
        bgm_wd = None
        for it in items:
            if str(it.get("id")) == bgm_id:
                bgm_wd = it.get("air_weekday")
                break
        if bgm_wd and when.isoweekday() != bgm_wd:
            continue

        entries[bgm_id] = {
            "tid": tid,
            "title": title,
            "weekday": when.isoweekday(),
            "time": f"{when.hour:02d}:{when.minute:02d}",
            "channel": ch_names.get(pick["chid"], ""),
            "skip_week": gap_week,
        }

    _save_json(SCHEDULE_CACHE, {"fetched_at": int(time.time()), "entries": entries})
    return entries


def channel_names(log=print):
    raw = _get(f"{DB}?Command=ChLookup&Fields=ChID,ChName")
    out = {}
    root = ET.fromstring(raw)
    for ch in root.iter("ChItem"):
        chid = ch.findtext("ChID")
        name = ch.findtext("ChName")
        if chid and name:
            out[chid] = name
    return out
