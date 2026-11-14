#!/usr/bin/env python3
"""生成新番可视化页面：code/anime_board.html

数据来源：Bangumi 放送表（https://api.bgm.tv/calendar，公开接口）
用法：python3 code/anime_board.py
"""
import html
import json

from captures_tab import CAPTURES_PAGE, CAPTURES_JS
import scores
import ja_titles
import os
import sys
import re
import urllib.parse
import urllib.request
from datetime import date

API = "https://api.bgm.tv/calendar"
OUT = os.environ.get("ANIMEBAR_OUT") or "code/anime_board.html"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
try:
    import pykakasi
    _kks = pykakasi.kakasi()
except Exception:
    _kks = None
try:
    from pypinyin import pinyin, Style
except Exception:
    pinyin = None

KANA = range(0x3040, 0x30FF)


def has_kana(text):
    return any(ord(ch) in KANA for ch in text)

CJK = range(0x3040, 0xA000)
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "titles-en.json")
_ANILIST = "https://graphql.anilist.co"


def load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)


_CACHE = load_cache()
_QUOTA = 25


def anilist_english(query):
    """向 AniList 查官方英文名；查不到返回空。"""
    body = json.dumps({
        "query": "query($s:String){Media(search:$s,type:ANIME){title{english}}}",
        "variables": {"s": query},
    }).encode()
    req = urllib.request.Request(_ANILIST, data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": UA},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
        t = ((data.get("data") or {}).get("Media") or {}).get("title") or {}
        return (t.get("english") or "").strip()
    except Exception:
        return ""


def english_title(zh, orig):
    """优先缓存里的官方英文名；没缓存就查一次（每次生成有配额）。"""
    global _QUOTA
    key = f"{zh}|{orig}"
    if key in _CACHE:
        return _CACHE[key] or None
    if _QUOTA <= 0:
        return None
    _QUOTA -= 1
    for q in (orig, zh):
        if not q:
            continue
        en = anilist_english(q)
        if en:
            _CACHE[key] = en
            return en
    _CACHE[key] = ""
    return None


def romanize(text):
    """整串判定语种：含假名→日文罗马字；纯汉字→中文拼音；拉丁原样。"""
    if not text:
        return ""
    if not any(ord(ch) in CJK for ch in text):
        return text
    parts = [w for w in re.split(r"[\s　・:：~]+", text) if w]
    if has_kana(text):
        out = []
        for w in parts:
            r = "".join(x["hepburn"] for x in _kks.convert(w)).strip() if _kks else w
            out.append(r[:1].upper() + r[1:] if r else r)
        return " ".join(out).strip()
    if pinyin is None:
        return text
    out = []
    for w in parts:
        syl = ["".join(x) for x in pinyin(w, style=Style.NORMAL)]
        out.append(" ".join(x.capitalize() for x in syl))
    return " ".join(out).strip()


def romaji(text):
    return romanize(text)


def titles(cn, orig):
    """返回 (中文侧标题, 英文侧标题)。英文优先用官方名，其次罗马字/拼音。"""
    zh = cn or orig
    return zh, (english_title(zh, orig) or romanize(orig or zh))

UA = "dsh-agent/1.0 (personal use)"
DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
EN_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fetch():
    req = urllib.request.Request(API, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


GHOST = "assets/cover-placeholder.png"

JA = {
    "本季新番": "今期の新作", "部": "作品", "部剧场版": "劇場版", "部上映中": "上映中",
    "新番": "新作", "剧场版": "劇場版", "上映中": "上映中", "记录": "記録", "捕获": "キャプチャ",
    "全部": "全て", "周一": "月", "周二": "火", "周三": "水", "周四": "木", "周五": "金", "周六": "土", "周日": "日",
    "按热度": "人気順", "按最新": "新着順",
    "详情": "詳細", "复制": "コピー", "打点": "記録する", "AniCh": "視聴",
    "作品名": "作品名", "现象": "兆候", "推测": "推測", "维度": "軸",
    "作画": "作画", "演出": "演出", "声音": "音響",
    "如果是我": "自分なら", "保存": "保存", "复制 Markdown": "Markdown をコピー",
    "条记录": " 件", "还没有记录": "まだ記録なし", "删除": "削除", "如果是我：": "自分なら：",
    "上映": "公開", "人评": " 人評価", "原": "原作", "リバイバル": "リバイバル", "人評価": "人評価",
    "静止画多": "静止画が多い", "精度落差": "精度の落差", "画风突变": "絵柄の変化",
    "重复镜头": "繰り返しカット", "演出神回": "神回の演出", "评分分歧": "評価の乖離",
    "疑似外包": "外注の可能性", "工期紧张": "工期逼迫", "作监尽力": "作監の踏ん張り", "资方干预": "出資者の介入",
    "值得学习": "参考になる", "中规中矩": "可もなく不可もなく", "有待提高": "要改善",
    "有巧思": "工夫がある", "平淡": "平凡", "用力过猛": "やりすぎ",
    "加分项": "加点", "无感": "響かない", "出戏": "没入できない",
}


def L(zh, en):
    return f'<span class="l-zh">{zh}</span><span class="l-en">{en}</span>'


def card(it):
    name = it.get("name_cn") or it.get("name") or ""
    orig = it.get("name") or ""
    score = (it.get("rating") or {}).get("score", 0) or 0
    total = (it.get("rating") or {}).get("total", 0) or 0
    imgs = it.get("images") or {}
    img = imgs.get("large") or imgs.get("common") or imgs.get("medium") or ""
    wd = it.get("air_weekday", 0)
    url = (it.get("url") or "").replace("http://", "https://") or f"https://bgm.tv/subject/{it.get('id')}"
    air = it.get("air_date") or ""
    img = img.replace("http://", "https://") or GHOST

    cls = "hi" if score >= 8 else ("mid" if score >= 7 else "")
    zh, en = titles(name, orig)
    q = urllib.parse.quote(name)
    return f"""
    <article class="card {cls}" data-wd="{wd}" data-name="{esc(name)}{esc(orig)}" data-score="{score}" data-pop="{total}" data-date="{esc(air)}">
      <a class="cover" href="{esc(url)}" target="_blank" rel="noopener">
        <img loading="lazy" src="{esc(img or GHOST)}" alt="{esc(name)}" onerror="this.onerror=null;this.src='{GHOST}'">
        {scores.badges(score, scores.alt(name, orig), scores.kitsu_alt(name, orig))}
      </a>
      <div class="body">
        <h3 title="{esc(orig)}"><span class="l-zh">{esc(zh)}</span><span class="l-en">{esc(en)}</span><span class="l-ja">{esc(ja_titles.lookup(orig))}</span></h3>
        <p class="meta">{L(DAYS[wd-1], EN_DAYS[wd-1]) if 1 <= wd <= 7 else '—'} · {esc(air)} · {total}{L(' 人评',' ratings')}</p>
        <div class="acts">
          <a class="detail" href="{esc(url)}" data-bgm="{esc(url)}" data-title="{esc(name)}" data-en="{esc(en)}" data-ja="{esc(ja_titles.lookup(orig))}" target="_blank" rel="noopener">{L('详情','Details')}</a>
          <button class="cp" data-name="{esc(name)}">{L('复制','Copy')}</button>
          <button class="note" data-name="{esc(name)}">{L('打点','Note')}</button>
          <button class="watch" data-name="{esc(name)}" data-en="{esc(en)}" data-ja="{esc(ja_titles.lookup(orig))}">{L('AniCh','Watch')}</button>
        </div>
      </div>
    </article>"""


def fetch_movies(limit=48, pages=8):
    """Bangumi 搜索「劇場版」，每页 20 条，翻页累积后按评分排序。"""
    items, seen = [], set()
    for page in range(pages):
        body = json.dumps({"keyword": "劇場版", "filter": {"type": [2]}, "sort": "heat"}).encode()
        req = urllib.request.Request(
            f"https://api.bgm.tv/v0/search/subjects?limit=20&offset={page * 20}",
            data=body,
            headers={"User-Agent": UA, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
        except Exception:
            break
        rows = data.get("data", [])
        if not rows:
            break
        for it in rows:
            if it.get("id") in seen:
                continue
            seen.add(it.get("id"))
            items.append({
                "name": it.get("name_cn") or it.get("name") or "",
                "orig": it.get("name") or "",
                "score": (it.get("rating") or {}).get("score", 0) or 0,
                "total": (it.get("rating") or {}).get("total", 0) or 0,
                "img": (it.get("images") or {}).get("large") or "",
                "url": f"https://bgm.tv/subject/{it.get('id')}",
                "date": (it.get("date") or "")[:10],
            })
    items.sort(key=lambda x: -x["score"])
    top = items[:limit]
    recent = [i for i in items if i["date"] >= "2025-01"]
    merged, seen_ids = [], set()
    for i in top + sorted(recent, key=lambda x: x["date"], reverse=True):
        key = i["url"]
        if key in seen_ids:
            continue
        seen_ids.add(key)
        merged.append(i)
    return merged


SHOWING_URL = "https://eiga.com/now/%E3%82%A2%E3%83%8B%E3%83%A1/"


def _bgm_lookup(title):
    """用 Bangumi 搜一次，拿高清封面、评分和原始上映年份。失败返回空。"""
    body = json.dumps({"keyword": title, "filter": {"type": [2]}}).encode()
    req = urllib.request.Request(
        "https://api.bgm.tv/v0/search/subjects?limit=3",
        data=body,
        headers={"User-Agent": UA, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            rows = json.load(r).get("data", [])
    except Exception:
        return {}
    if not rows:
        return {}
    it = rows[0]
    return {
        "img": (it.get("images") or {}).get("large") or "",
        "score": (it.get("rating") or {}).get("score", 0) or 0,
        "date": (it.get("date") or "")[:10],
        "url": f"https://bgm.tv/subject/{it.get('id')}",
    }


def fetch_showings():
    """映画.com 的「上映中のアニメ映画」，再用 Bangumi 补封面和原始年份。"""
    req = urllib.request.Request(SHOWING_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "ignore")
    chunks = page.split('id="mv')[1:]
    out, seen = [], set()
    for chunk in chunks:
        m_link = re.search(r'<h2 class="title"><a href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
        if not m_link:
            continue
        href = "https://eiga.com" + m_link.group(1)
        if href in seen:
            continue
        seen.add(href)
        name = html.unescape(re.sub(r"<[^>]+>", "", m_link.group(2))).strip()
        m_img = re.search(r'<img[^>]*src="([^"]+)"', chunk)
        m_time = re.search(r'<small class="time">([^<]*)</small>', chunk)
        img = (m_img.group(1) if m_img else "").replace("/320.jpg", "/640.jpg")
        meta = _bgm_lookup(name)
        out.append({
            "name": name,
            "img": meta.get("img") or img,
            "date": (m_time.group(1).strip() if m_time else ""),
            "url": href,
            "score": meta.get("score", 0),
            "original": meta.get("date", ""),
        })
    return out


# 截断时按公开日排序（页面默认已是）
def movie_card(m):
    q = urllib.parse.quote(m["name"])
    cls = "hi" if m["score"] >= 8 else ("mid" if m["score"] >= 7 else "")
    return f"""
    <article class="card {cls}" data-name="{esc(m['name'])}{esc(m['orig'])}" data-score="{m['score']}" data-pop="{m['total']}" data-date="{m['date']}">
      <a class="cover" href="{esc(m['url'])}" target="_blank" rel="noopener">
        <img loading="lazy" src="{esc(m['img'] or GHOST)}" alt="{esc(m['name'])}" onerror="this.onerror=null;this.src='{GHOST}'">
        {scores.badges(m['score'], scores.alt(m['name'], m['orig']), scores.kitsu_alt(m['name'], m['orig']))}
      </a>
      <div class="body">
        <h3 title="{esc(m['orig'])}"><span class="l-zh">{esc(m['name'])}</span><span class="l-en">{esc(titles(m['name'], m['orig'])[1])}</span><span class="l-ja">{esc(ja_titles.lookup(m['orig'] or m['name']))}</span></h3>
        <p class="meta">{L('上映','Released')} {esc(m['date']) or '—'} · {m['total']}{L(' 人评',' ratings')}</p>
        <div class="acts">
          <a class="detail" href="{esc(m['url'])}" data-bgm="{esc(m['url'])}" data-title="{esc(m['name'])}" data-en="{esc(titles(m['name'], m['orig'])[1])}" data-ja="{esc(ja_titles.lookup(m['orig'] or m['name']))}" target="_blank" rel="noopener">{L('详情','Details')}</a>
          <button class="cp" data-name="{esc(m['name'])}">{L('复制','Copy')}</button>
          <button class="note" data-name="{esc(m['name'])}">{L('打点','Note')}</button>
          <button class="watch" data-name="{esc(m['name'])}" data-en="{esc(titles(m['name'], m['orig'])[1])}" data-ja="{esc(ja_titles.lookup(m['orig'] or m['name']))}">{L('AniCh','Watch')}</button>
        </div>
      </div>
    </article>"""


MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def date_en(text):
    """「11月13日公開」→「Opened Nov 13」"""
    m = re.match(r"(\d+)月(\d+)日", text or "")
    if not m:
        return text
    return f"Opened {MONTHS_EN[int(m.group(1)) - 1]} {int(m.group(2))}"


def showing_card(m):
    cls = "hi" if m["score"] >= 8 else ("mid" if m["score"] >= 7 else "")
    badge = f'{m["score"]:.1f}' if m["score"] else L('上映中', 'Now')
    revival = ""
    if m.get("original") and m["original"] < "2025-01":
        revival = '<span class="revival">' + L('リバイバル', 'Revival') + '</span>'
    return f"""
    <article class="card showing {cls}" data-name="{esc(m['name'])}" data-score="{m['score']}">
      <a class="cover" href="{esc(m['url'])}" target="_blank" rel="noopener">
        <img loading="lazy" src="{esc(m['img'] or GHOST)}" alt="{esc(m['name'])}" onerror="this.onerror=null;this.src='{GHOST}'">
        {scores.badges(m['score'], scores.alt(m['name'], m['name']), scores.kitsu_alt(m['name'], m['name'])) if m['score'] else f'<span class="score">{badge}</span>'}
        {revival}
      </a>
      <div class="body">
        <h3><span class="l-zh">{esc(m['name'])}</span><span class="l-en">{esc(titles(m['name'], m['name'])[1])}</span><span class="l-ja">{esc(ja_titles.lookup(m['name']))}</span></h3>
        <p class="meta">{L(esc(m['date']) or '上映中', date_en(m['date']) if m['date'] else 'In cinemas')}{(' · ' + L('原','orig.') + ' ' + esc(m['original'])) if m.get('original') else ''}</p>
        <div class="acts">
          <a class="detail" href="{esc(m['url'])}" data-bgm="{esc(m['url'])}" data-title="{esc(m['name'])}" data-en="{esc(titles(m['name'], m['name'])[1])}" data-ja="{esc(ja_titles.lookup(m['name']))}" target="_blank" rel="noopener" title="映画.com">{L('详情','Details')}</a>
          <button class="cp" data-name="{esc(m['name'])}">{L('复制','Copy')}</button>
          <button class="note" data-name="{esc(m['name'])}">{L('打点','Note')}</button>
          <button class="watch" data-name="{esc(m['name'])}" data-en="{esc(titles(m['name'], m['name'])[1])}" data-ja="{esc(ja_titles.lookup(m['name']))}">{L('AniCh','Watch')}</button>
        </div>
      </div>
    </article>"""


def main():
    data = fetch()
    items, seen = [], set()
    for day in data:
        for it in day.get("items", []):
            if it["id"] in seen:
                continue
            seen.add(it["id"])
            items.append(it)
    items.sort(key=lambda x: -((x.get("rating") or {}).get("score", 0) or 0))

    today_wd = date.today().isoweekday()
    cards = "\n".join(card(i) for i in items)
    try:
        movies = fetch_movies()
    except Exception:
        movies = []
    movie_cards = "\n".join(movie_card(m) for m in movies)
    try:
        showings = fetch_showings()
    except Exception:
        showings = []
    showing_cards = "\n".join(showing_card(m) for m in showings)
    en_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    tabs = "".join(
        f'<button data-wd="{i}">{L(d, en_days[i-1])}</button>'
        for i, d in enumerate(DAYS, 1)
    )

    html = f"""<!doctype html>
<html lang="zh"><meta charset="utf-8">
<title>本季新番</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{ --bg:#020617; --surface:#0f172a; --surface2:#1e293b; --line:#1e293b; --line2:#334155; --txt:#e2e8f0; --dim:#94a3b8; --accent:#22c55e; --warn:#f59e0b; --link:#93c5fd; }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:"Fira Sans",-apple-system,"Hiragino Sans","PingFang SC",sans-serif; font-size:14px; line-height:1.5; -webkit-font-smoothing:antialiased; }}
  header {{ position:sticky; top:0; z-index:5; padding:16px 20px 12px; background:rgba(2,6,23,.86); backdrop-filter:blur(12px); border-bottom:1px solid var(--line); }}
  h1 {{ margin:0 0 12px; font-size:15px; font-weight:600; letter-spacing:.01em; }}
  h1 small {{ color:var(--dim); font-size:12px; font-weight:400; margin-left:8px; }}
  .tools {{ display:flex; gap:6px; flex-wrap:wrap; align-items:center; }}
  button, input {{ font:inherit; font-size:12px; color:var(--txt); background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:6px 11px; }}
  button {{ cursor:pointer; transition:background .12s,border-color .12s; }}
  button:hover {{ background:var(--surface2); border-color:var(--line2); }}
  button.on {{ background:var(--accent); border-color:var(--accent); color:#04140a; font-weight:600; }}
  .sep {{ width:1px; height:18px; background:var(--line2); margin:0 6px; }}
  .sortgroup {{ display:inline-flex; gap:6px; }}
  input {{ min-width:200px; }}
  input::placeholder {{ color:#64748b; }}
  :focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
  [hidden] {{ display:none !important; }}
  .l-en {{ display:none; }}
  .l-ja {{ display:none; }}
  body.en .l-zh {{ display:none; }}
  body.en .l-en {{ display:inline; }}
  body.ja .l-zh {{ display:none; }}
  body.ja .l-en {{ display:none; }}
  body.ja .l-ja {{ display:inline; }}
  .langs {{ margin-left:auto; display:inline-flex; gap:4px; }}
  .langs button {{ font-size:11px; padding:3px 9px; border-radius:7px; border:1px solid var(--line); background:transparent; color:var(--dim); cursor:pointer; }}
  .langs button.on {{ background:var(--accent); border-color:var(--accent); color:#04140a; font-weight:600; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:16px; padding:20px; }}
  .card {{ background:var(--surface); border:1px solid var(--line); border-radius:14px; overflow:hidden; display:flex; flex-direction:column; transition:transform .14s ease,border-color .14s ease; }}
  .card:hover {{ transform:translateY(-2px); border-color:var(--line2); }}
  .cover {{ position:relative; display:block; aspect-ratio:3/4; background:var(--surface2) url('assets/cover-placeholder.png') center/cover no-repeat; }}
  .cover img {{ width:100%; height:100%; object-fit:cover; display:block; }}
  .scores {{ position:absolute; right:8px; top:8px; display:flex; gap:4px; }}
  .scores .score {{ position:static; }}
  .score.AniList {{ color:#93c5fd; }}
  .score.Kitsu {{ color:#f472b6; }}
  .scores.score-hi .score {{ border:1px solid #78350f; }}
  .score {{ position:absolute; right:8px; top:8px; padding:3px 8px; border-radius:999px; font-family:"Fira Code",ui-monospace,monospace; font-size:11px; font-weight:600; background:rgba(2,6,23,.78); color:var(--dim); }}
  .card.hi .score {{ color:var(--accent); }}
  .revival {{ position:absolute; left:8px; top:8px; padding:2px 7px; border-radius:6px; font-size:10px; background:rgba(2,6,23,.8); color:var(--warn); border:1px solid #78350f; }}
  .card.mid .score {{ color:var(--warn); }}
  .body {{ padding:12px; display:flex; flex-direction:column; gap:8px; flex:1; }}
  h3 {{ margin:0; font-size:13px; font-weight:600; line-height:1.35; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .meta {{ margin:0; font-size:11px; color:var(--dim); font-variant-numeric:tabular-nums; }}
  .acts {{ display:flex; gap:6px; margin-top:auto; flex-wrap:wrap; }}
  .acts a, .acts button {{ font-size:11px; padding:4px 9px; border-radius:7px; border:1px solid var(--line); background:transparent; color:var(--dim); text-decoration:none; line-height:1.4; }}
  .acts a:hover, .acts button:hover {{ background:var(--surface2); color:var(--txt); border-color:var(--line2); }}
  .acts .watch {{ color:var(--link); border-color:#1e3a5f; }}
  .acts .note {{ color:var(--accent); border-color:#166534; }}
  .acts .cp.done {{ color:var(--accent); border-color:var(--accent); }}
  .notes-wrap {{ padding:20px; max-width:720px; margin:0 auto; }}
  .notes-wrap label {{ display:block; font-size:11px; color:var(--dim); margin:10px 0 4px; }}
  .notes-wrap input, .notes-wrap textarea {{ width:100%; box-sizing:border-box; background:var(--surface); border:1px solid var(--line); border-radius:8px; color:var(--txt); font:inherit; font-size:13px; padding:7px 10px; }}
  .notes-wrap textarea {{ min-height:58px; resize:vertical; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .chips button {{ font-size:12px; padding:4px 10px; border-radius:999px; border:1px solid var(--line); background:transparent; color:var(--dim); cursor:pointer; }}
  .chips button.on {{ background:rgba(34,197,94,.16); border-color:#166534; color:var(--accent); }}
  .nbar {{ display:flex; gap:8px; align-items:center; margin-top:12px; }}
  .nbar .primary {{ background:var(--accent); border-color:var(--accent); color:#04140a; font-weight:600; }}
  .nbar .ghost {{ background:transparent; }}
  #n-count {{ font-size:11px; color:var(--dim); margin-left:auto; }}
  #n-list {{ margin-top:16px; border-top:1px solid var(--line); }}
  .note {{ padding:10px 2px; border-bottom:1px solid var(--line); }}
  .note-head {{ display:flex; align-items:baseline; gap:8px; }}
  .note-head b {{ font-size:13px; }}
  .note-head .del {{ margin-left:auto; font-size:11px; border:1px solid var(--line); background:transparent; color:var(--dim); border-radius:6px; padding:2px 7px; cursor:pointer; }}
  .note-tags {{ font-size:11px; color:var(--dim); margin-top:3px; }}
  .note-ref {{ font-size:12px; margin-top:3px; opacity:.85; }}
  .empty {{ font-size:12px; color:var(--dim); padding:16px 0; }}
</style>
<header>
  <h1>{L('本季新番','This season')} <small>{len(items)} {L('部','TV')} · {len(movies)} {L('部剧场版','films')} · {len(showings)} {L('部上映中','in cinemas')}</small></h1>
  <div class="tools">
    <button data-mode="tv" class="on">{L('新番','TV')}</button>
    <button data-mode="movie">{L('剧场版','Films')}</button>
    <button data-mode="showing">{L('上映中','In cinemas')}</button>
    <button data-mode="notes">{L('记录','Notes')}</button>
    <span class="sep"></span>
    <span id="filters" class="tools">
      <button data-wd="0" class="on">{L('全部','All')}</button>{tabs}
    </span>
    <span id="sorts" class="sortgroup">
      <button data-sort="pop" class="on">{L('按热度','Popular')}</button>
      <button data-sort="date">{L('按最新','Newest')}</button>
    </span>
    <span class="langs">
    <button data-lang="zh">中文</button>
    <button data-lang="en">EN</button>
    <button data-lang="ja">日本語</button>
    </span>
    <input id="q" data-zh="搜名字…" data-en="Search title…" data-ja="検索…" placeholder="搜名字…">
  </div>
</header>
<main class="grid" id="view-tv">{cards}</main>
<main class="grid" id="view-movie" hidden>{movie_cards}</main>
<main class="grid" id="view-showing" hidden>{showing_cards}</main>
{CAPTURES_PAGE}
<script>
  let wd = 0, scoreFilter = 'all';
  const q = document.getElementById('q');
  const cards = [...document.querySelectorAll('.card')];
  function inScore(s) {{
    if (scoreFilter === 'all') return true;
    if (scoreFilter === '8') return s >= 8;
    if (scoreFilter === '7') return s >= 7 && s < 8;
    return s < 7;
  }}
  function apply() {{
    const kw = q.value.trim().toLowerCase();
    cards.forEach(c => {{
      const okWd = wd === 0 || +c.dataset.wd === wd;
      const okKw = !kw || c.dataset.name.toLowerCase().includes(kw);
      const okScore = inScore(+c.dataset.score || 0);
      c.style.display = okWd && okKw && okScore ? '' : 'none';
    }});
  }}
  document.querySelectorAll('button[data-wd]').forEach(b => b.onclick = () => {{
    wd = +b.dataset.wd;
    document.querySelectorAll('button[data-wd]').forEach(x => x.classList.toggle('on', x === b));
    apply();
  }});
  const LANGS = ['zh', 'en', 'ja'];
  let curLang = localStorage.getItem('animebar-lang') || 'zh';
  function applyLang(lang) {{
    curLang = LANGS.includes(lang) ? lang : 'zh';
    document.body.classList.remove('en', 'ja');
    if (curLang === 'en') document.body.classList.add('en');
    if (curLang === 'ja') document.body.classList.add('ja');
    document.querySelectorAll('button[data-lang]').forEach((b) => {{
      b.classList.toggle('on', b.dataset.lang === curLang);
    }});
    document.dispatchEvent(new CustomEvent('animebar-lang'));
    localStorage.setItem('animebar-lang', curLang);
    const q = document.getElementById('q');
    if (q) q.placeholder = curLang === 'ja' ? q.dataset.ja : curLang === 'en' ? q.dataset.en : q.dataset.zh;
    document.querySelectorAll('a.detail[data-bgm]').forEach((a) => {{
      if (curLang === 'zh') {{
        a.href = a.dataset.bgm;
      }} else if (curLang === 'ja') {{
        a.href = 'https://www.google.com/search?q=' + encodeURIComponent((a.dataset.ja || a.dataset.title) + ' アニメ');
      }} else {{
        a.href = 'https://myanimelist.net/anime.php?q=' + encodeURIComponent(a.dataset.en || a.dataset.title);
      }}
    }});
  }}
  document.querySelectorAll('button[data-lang]').forEach((b) => {{
    b.onclick = () => applyLang(b.dataset.lang);
  }});
  applyLang(curLang);

  let sortKey = 'pop';
  function reorder() {{
    for (const id of ['view-tv', 'view-movie']) {{
      const grid = document.getElementById(id);
      const kids = [...grid.children];
      kids.sort((a, b) => sortKey === 'date'
        ? (b.dataset.date || '').localeCompare(a.dataset.date || '')
        : (parseFloat(b.dataset.pop) || 0) - (parseFloat(a.dataset.pop) || 0));
      kids.forEach(k => grid.appendChild(k));
    }}
  }}
  document.querySelectorAll('a.detail').forEach(a => a.addEventListener('click', (e) => {{
    e.preventDefault();
    const langNow = document.body.classList.contains('ja') ? 'ja' : document.body.classList.contains('en') ? 'en' : 'zh';
    let u = a.dataset.bgm;
    if (langNow === 'en') u = 'https://myanimelist.net/anime.php?q=' + encodeURIComponent(a.dataset.en || a.dataset.title);
    else if (langNow === 'ja') u = 'https://www.google.com/search?q=' + encodeURIComponent((a.dataset.ja || a.dataset.title) + ' アニメ');
    const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.openurl;
    if (h) {{ h.postMessage(u); }} else {{ window.open(u, '_blank'); }}
  }}));
  document.querySelectorAll('button[data-sort]').forEach(b => b.onclick = () => {{
    sortKey = b.dataset.sort;
    document.querySelectorAll('button[data-sort]').forEach(x => x.classList.toggle('on', x === b));
    reorder();
  }});
  document.querySelectorAll('button[data-mode]').forEach(b => b.onclick = () => {{
    const mode = b.dataset.mode;
    document.querySelectorAll('button[data-mode]').forEach(x => x.classList.toggle('on', x === b));
    for (const id of ['tv', 'movie', 'showing', 'notes']) {{
      document.getElementById('view-' + id).hidden = (id !== mode);
    }}
    document.getElementById('filters').hidden = mode !== 'tv';
    document.getElementById('sorts').hidden = mode === 'showing' || mode === 'notes';
    if (mode === 'notes' && window.__loadCaptures) window.__loadCaptures();
    apply();
  }});
  document.querySelectorAll('button[data-score]').forEach(b => b.onclick = () => {{
    scoreFilter = b.dataset.score;
    document.querySelectorAll('button[data-score]').forEach(x => x.classList.toggle('on', x === b));
    apply();
  }});
  q.oninput = apply;
  document.querySelectorAll('.watch').forEach(b => b.onclick = () => {{
    const n = b.dataset.name;
    const langNow = document.body.classList.contains('ja') ? 'ja' : document.body.classList.contains('en') ? 'en' : 'zh';
    const openUrl = (u) => {{
      const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.openurl;
      if (h) h.postMessage(u); else window.open(u, '_blank');
    }};
    if (langNow === 'en') {{ openUrl('https://www.justwatch.com/us/search?q=' + encodeURIComponent(b.dataset.en || n)); return; }}
    if (langNow === 'ja') {{ openUrl('https://www.justwatch.com/jp/search?q=' + encodeURIComponent(b.dataset.ja || n)); return; }}
    const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.anich;
    if (h) {{ h.postMessage(n); b.textContent = '已送出'; }}
    else {{ navigator.clipboard.writeText(n).catch(()=>{{}}); b.textContent = '已复制'; }}
    setTimeout(() => {{ b.textContent = 'AniCh'; }}, 1400);
  }});
  document.querySelectorAll('.cp').forEach(b => b.onclick = async () => {{
    try {{ await navigator.clipboard.writeText(b.dataset.name); }} catch (e) {{}}
    b.textContent = '已复制'; b.classList.add('done');
    setTimeout(() => {{ b.textContent = '复制'; b.classList.remove('done'); }}, 1200);
  }});
</script>

{CAPTURES_JS}
</html>"""
    def _ja_of(zh, en):
        key = zh.strip()
        if key in JA:
            return JA[key]
        if any('\u3040' <= ch <= '\u30ff' for ch in key):  # 含假名，本身是日文
            return zh
        if '月' in key and '日' in key:  # 日期，保持原文
            return zh
        return en
    import re as _re
    html = _re.sub(
        r'<span class="l-zh">([^<]*)</span><span class="l-en">([^<]*)</span>(?!<span class="l-ja">)',
        lambda m: (
            f'<span class="l-zh">{m.group(1)}</span>'
            f'<span class="l-en">{m.group(2)}</span>'
            f'<span class="l-ja">{_ja_of(m.group(1), m.group(2))}</span>'
        ),
        html,
    )
    scores.flush()
    ja_titles.flush()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    save_cache(_CACHE)
    print(f"写入 {OUT}：{len(items)} 部")


if __name__ == "__main__":
    main()
