#!/usr/bin/env python3
"""补抓失败的官方英文名（只补空值，慢速重试）。"""
import sys, time
sys.path.insert(0, "board")
import anime_board as ab

rows = []
for day in ab.fetch():
    for it in day.get("items", []):
        rows.append((it.get("name_cn") or it.get("name"), it.get("name")))
for m in ab.fetch_movies():
    rows.append((m["name"], m["orig"]))
for m in ab.fetch_showings():
    rows.append((m["name"], m["name"]))

todo, seen = [], set()
for zh, orig in rows:
    key = f"{zh}|{orig}"
    if key in seen:
        continue
    seen.add(key)
    if ab._CACHE.get(key):
        continue
    todo.append((zh, orig))

print(f"待补 {len(todo)} 条", flush=True)
ok = 0
for i, (zh, orig) in enumerate(todo, 1):
    for q in (orig, zh):
        if not q:
            continue
        en = ab.anilist_english(q)
        if en:
            ab._CACHE[f"{zh}|{orig}"] = en
            ok += 1
            break
    if i % 20 == 0:
        ab.save_cache(ab._CACHE)
        print(f"  {i}/{len(todo)} ok={ok}", flush=True)
    time.sleep(1.2)
ab.save_cache(ab._CACHE)
print(f"done 新增 {ok} / 缓存 {len(ab._CACHE)}", flush=True)
