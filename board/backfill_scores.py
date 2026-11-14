#!/usr/bin/env python3
"""补齐 AniList 分数缓存（慢速，避免 429）。"""
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

seen, todo = set(), []
for zh, orig in rows:
    key = f"{zh}|{orig}"
    if key in seen or ab._SCORES.get(key):
        continue
    seen.add(key)
    todo.append((zh, orig))
print(f"待补 {len(todo)} 条", flush=True)

ok = 0
for i, (zh, orig) in enumerate(todo, 1):
    for q in (orig, zh):
        if not q:
            continue
        got = ab.anilist_score(q)
        if got:
            ab._SCORES[f"{zh}|{orig}"] = got
            ok += 1
            break
    else:
        ab._SCORES[f"{zh}|{orig}"] = None
    if i % 25 == 0:
        ab.save_scores(ab._SCORES)
        print(f"  {i}/{len(todo)} ok={ok}", flush=True)
    time.sleep(1.1)
ab.save_scores(ab._SCORES)
print(f"done 新增 {ok}", flush=True)
