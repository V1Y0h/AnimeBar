import sys, time
sys.path.insert(0, "board")
import anime_board as ab, ja_titles as jt

jt._QUOTA = 100000
rows = []
for day in ab.fetch():
    for it in day.get("items", []):
        rows.append(it.get("name") or "")
for m in ab.fetch_movies():
    rows.append(m["orig"])
for m in ab.fetch_showings():
    rows.append(m["name"])

todo = [o for o in dict.fromkeys(rows) if o and not jt._has_kana(o) and o not in jt._CACHE]
print("待查", len(todo), flush=True)
ok = 0
for i, o in enumerate(todo, 1):
    r = jt.lookup(o)
    if r and jt._has_kana(r):
        ok += 1
    if i % 20 == 0:
        jt.flush(); print(f"  {i}/{len(todo)} ok={ok}", flush=True)
    time.sleep(0.7)
jt.flush()
print("done", ok, flush=True)
