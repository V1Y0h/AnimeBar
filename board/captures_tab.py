"""记录页：捕获与手记合并成一个列表，共用一套卡片表单。

数据仍是两份存储（A 方案）：
  捕获 → triage-mac.jsonl（宿主路由写入）
  手记 → notes.json（沿用原格式，标签存中文）
"""

import json as _json

from notes_tab import _load_tags  # 复用同一份标签词表

CAPTURES_PAGE = """
<main id="view-notes" hidden>
  <div class="caps-wrap">
    <div class="caps-head">
      <span id="cap-count"></span>
      <button type="button" id="cap-new">＋ <span class="l-zh">新建手记</span><span class="l-en">New note</span><span class="l-ja">手記を作成</span></button>
      <button type="button" id="cap-export"><span class="l-zh">导出草稿</span><span class="l-en">Export draft</span><span class="l-ja">書き出す</span></button>
    </div>
    <div id="cap-list"></div>
  </div>
</main>
<style>
  .caps-wrap { max-width: 880px; margin: 0 auto; padding: 4px 2px 20px; }
  .caps-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: #64748b; }
  .caps-head #cap-count { flex: 1; }
  .caps-head button { border: 1px solid #1e293b; background: transparent; color: #94a3b8; border-radius: 7px; padding: 3px 10px; font-size: 12px; cursor: pointer; }
  .cap-card { border: 1px solid #1e293b; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: #0b1220; }
  .cap-head-row { display: flex; gap: 8px; align-items: center; font-size: 13px; margin-bottom: 6px; }
  .cap-head-row b { font-variant-numeric: tabular-nums; color: #22c55e; }
  .cap-head-row em { font-style: normal; font-size: 11px; color: #64748b; border: 1px solid #1e293b; border-radius: 999px; padding: 0 6px; }
  .cap-title { flex: 1; min-width: 0; box-sizing: border-box; background: #020617; border: 1px solid #1e293b; border-radius: 7px; color: #e2e8f0; font-size: 13px; padding: 4px 8px; font-family: inherit; }
  .cap-label { font-size: 11px; color: #64748b; margin: 6px 0 3px; }
  .cap-ep { display: flex; gap: 6px; align-items: center; font-size: 11px; color: #64748b; margin-bottom: 2px; }
  .cap-ep input { width: 64px; box-sizing: border-box; background: #020617; border: 1px solid #1e293b; border-radius: 7px; color: #e2e8f0; font-size: 12px; padding: 4px 6px; font-family: inherit; }
  .cap-take { width: 100%; box-sizing: border-box; min-height: 48px; resize: vertical; background: #020617; border: 1px solid #1e293b; border-radius: 7px; color: #e2e8f0; font-size: 12px; padding: 6px 8px; font-family: inherit; }
  .cap-ev { width: 100%; box-sizing: border-box; background: #020617; border: 1px solid #1e293b; border-radius: 7px; color: #e2e8f0; font-size: 12px; padding: 4px 8px; font-family: inherit; }
  .cap-actions { margin-top: 8px; display: flex; gap: 6px; align-items: center; }
  .cap-actions button { border-radius: 7px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
  .cap-save { border: 1px solid #22c55e; background: #22c55e; color: #04140a; font-weight: 600; }
  .cap-clear, .cap-del { border: 1px solid #1e293b; background: transparent; color: #94a3b8; }
  .cap-del.confirm { border-color: #b91c1c; color: #fca5a5; }
  .cap-more { margin: 8px 0 2px; border: 1px solid #1e293b; background: transparent; color: #94a3b8; border-radius: 7px; padding: 3px 10px; font-size: 12px; cursor: pointer; font-family: inherit; }
  .cap-more:hover { color: #e2e8f0; border-color: #334155; }
  .cap-more .caret { display: inline-block; width: 12px; transition: transform .15s ease; }
  .cap-more[aria-expanded="true"] .caret { transform: rotate(90deg); }
  .cap-dims { margin-top: 4px; padding: 6px 8px; border-left: 2px solid #1e293b; }
  .cap-card button:focus-visible, .cap-card input:focus-visible, .cap-card textarea:focus-visible { outline: 2px solid #22c55e; outline-offset: 1px; }
</style>
"""

_TAGS_JSON = _json.dumps(
    [
        {
            "slug": t.get("slug"),
            "kind": t.get("kind"),
            "facet": t.get("facet"),
            "label": {
                k: ((t.get("label") or {}).get(k) or t.get("slug"))
                for k in ("zh", "en", "ja")
            },
        }
        for t in _load_tags()
    ],
    ensure_ascii=False,
)

CAPTURES_JS = r"""
<script>
(function () {
  window.__TAGS__ = %%TAGS_JSON%%;

  const $ = (id) => document.getElementById(id);
  const lang = () => (document.body.classList.contains('ja') ? 'ja' : document.body.classList.contains('en') ? 'en' : 'zh');
  const T = (zh, en, ja) => (lang() === 'ja' ? (ja || en) : lang() === 'en' ? en : zh);
  const esc = (t) => String(t == null ? '' : t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (sec) => {
    const v = Math.max(0, Math.round(Number(sec) || 0));
    return String(Math.floor(v / 60)).padStart(2, '0') + ':' + String(v % 60).padStart(2, '0');
  };
  const labelOf = (tag) => {
    const l = tag.label || {};
    if (lang() === 'ja') return l.ja || l.en || tag.slug;
    if (lang() === 'en') return l.en || l.zh || tag.slug;
    return l.zh || l.en || tag.slug;
  };
  const tagsOf = (kind, facet) => (window.__TAGS__ || []).filter((t) => t.kind === kind && (!facet || t.facet === facet));
  const slugToZh = (slug) => {
    const t = (window.__TAGS__ || []).find((x) => x.slug === slug);
    return (t && t.label && t.label.zh) || slug;
  };
  const zhToSlug = (zh) => {
    const t = (window.__TAGS__ || []).find((x) => x.label && x.label.zh === zh);
    return t ? t.slug : zh;
  };
  const send = (name, body) => {
    const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers[name];
    if (h) h.postMessage(body);
    return !!h;
  };

  // 从片名猜集数：'第7集' / 'S01E07' / 'EP05' / ' - 03 [1080p]' 都认；
  // 分辨率（1080/720…）和年份不当作集数
  const guessEpisode = (title) => {
    const t = String(title || '');
    let m = t.match(/第\s*(\d{1,3})\s*[集話话]/);
    if (m) return String(parseInt(m[1], 10));
    m = t.match(/S\d{1,2}E(\d{1,3})/i) || t.match(/\bE(?:P)?(\d{1,3})\b/i);
    if (m) return String(parseInt(m[1], 10));
    const skip = new Set(['480', '720', '1080', '1440', '2160', '264', '265']);
    const tokens = t.match(/(?:^|[\s\-_\[\]\(\)])(\d{1,3})(?=[\s\-_\[\]\(\)\.]|$)/g) || [];
    for (const tok of tokens) {
      const n = tok.replace(/\D/g, '');
      if (!n) continue;
      const v = parseInt(n, 10);
      if (skip.has(n) || v === 0 || v >= 190) continue;
      return String(v);
    }
    return '';
  };

  let items = null;
  let lastPayload = '';
  let pendingPayload = null;

  // 页面是 innerHTML 重绘的，重绘会清掉正在输入的内容。
  window.__initCaptures = (data) => {
    const next = JSON.stringify((data && data.items) || []);
    const active = document.activeElement;
    const editing = active && active.closest && active.closest('#cap-hub');
    if (editing) {
      pendingPayload = { next: next, items: (data && data.items) || [] };
      return;
    }
    if (next === lastPayload) return;
    lastPayload = next;
    items = (data && data.items) || [];
    render();
  };

  window.__loadCaptures = () => send('captures', '1');

  document.addEventListener('focusout', (e) => {
    if (!e.target.closest || !e.target.closest('#cap-hub')) return;
    setTimeout(() => {
      const active = document.activeElement;
      if (active && active.closest && active.closest('#cap-hub')) return;
      if (!pendingPayload) return;
      const payload = pendingPayload;
      pendingPayload = null;
      if (payload.next !== lastPayload) {
        lastPayload = payload.next;
        items = payload.items;
        render();
      }
    }, 0);
  });

  document.addEventListener('animebar-lang', () => {
    const active = document.activeElement;
    if (active && active.closest && active.closest('#cap-hub')) return;
    lastPayload = '';
    render();
  });

  setInterval(() => {
    const view = $('view-notes');
    if (view && !view.hidden) window.__loadCaptures();
  }, 4000);

  function chipRow(kind, selected, units) {
    // units: 'slug'（捕获，用 slug）或 'zh'（手记，沿用中文标签）
    return tagsOf(kind).map((t) => {
      const key = units === 'zh' ? (t.label.zh || t.slug) : t.slug;
      const on = selected.indexOf(key) >= 0;
      return '<button type="button" data-key="' + esc(key) + '"' + (on ? ' class="on"' : '') + '>' + esc(labelOf(t)) + '</button>';
    }).join('');
  }

  // 维度：与现象/推测同一套芯片，每个维度单选；折叠条也用按钮，不用原生 details
  function dimsBlock(selected) {
    const dims = selected || {};
    const group = (facet, label) => {
      const chips = tagsOf('note', facet).map((t) => {
        const zh = t.label.zh || t.slug;
        const on = dims[facet] === zh;
        return '<button type="button" data-dim-value="' + esc(zh) + '"' + (on ? ' class="on"' : '') + '>' + esc(labelOf(t)) + '</button>';
      }).join('');
      return '<div class="cap-label">' + label + '</div>' +
        '<div class="chips" data-dim="' + facet + '">' + chips + '</div>';
    };
    return '<button type="button" class="cap-more" aria-expanded="false">' +
        '<span class="caret">▸</span>' + T('更多（维度）', 'More (dimensions)', 'その他（評価軸）') + '</button>' +
      '<div class="cap-dims" hidden>' +
        group('art', T('作画', 'sakuga', '作画')) +
        group('staging', T('演出', 'direction', '演出')) +
        group('sound', T('声音', 'sound', '音響')) +
      '</div>';
  }

  function noteCard(item) {
    const c = item.capture || {};
    const n = item.note || {};
    const ph = Array.isArray(n.phenomena) ? n.phenomena : [];
    const sp = Array.isArray(n.speculations) ? n.speculations : [];
    const dims = n.dims && typeof n.dims === 'object' ? n.dims : {};
    return '<div class="cap-card" data-id="' + esc(c.note_id) + '" data-kind="note">' +
      '<div class="cap-head-row"><em>' + T('手记', 'Note', '手記') + '</em>' +
      '<input class="cap-title" placeholder="' + T('作品名', 'Title', '作品名') + '" value="' + esc(n.title || c.title || '') + '"></div>' +
      '<div class="cap-label">' + T('现象', 'Observed', '現象') + '</div>' +
      '<div class="chips" data-field="phenomena">' + chipRow('phenomenon', ph, 'zh') + '</div>' +
      '<div class="cap-label">' + T('推测', 'Speculation', '推測') + '</div>' +
      '<div class="chips" data-field="speculations">' + chipRow('speculation', sp, 'zh') + '</div>' +
      dimsBlock(dims) +
      '<div class="cap-label">' + T('依据', 'Evidence', '根拠') + '</div>' +
      '<input class="cap-ev" value="' + esc(n.evidence || '') + '">' +
      '<div class="cap-label">' + T('如果是我', 'What I would do', '自分なら') + '</div>' +
      '<textarea class="cap-take">' + esc(n.my_take || '') + '</textarea>' +
      '<div class="cap-actions"><button type="button" class="cap-save">' + T('保存', 'Save', '保存') + '</button>' +
      '<button type="button" class="cap-del">' + T('删除', 'Delete', '削除') + '</button></div>' +
      '</div>';
  }

  function captureCard(item) {
    const c = item.capture || {};
    const tr = item.triage;
    const ph = (tr && Array.isArray(tr.phenomena)) ? tr.phenomena : [];
    const sp = (tr && Array.isArray(tr.speculations)) ? tr.speculations.map((x) => (x && x.tag) || '').filter(Boolean) : [];
    const epi = (tr && tr.episode) ? tr.episode : guessEpisode(c.title);
    return '<div class="cap-card" data-id="' + esc(c.note_id) + '" data-kind="capture">' +
      '<div class="cap-head-row"><b>' + fmt(c.t_start) + '</b><span>' + esc(c.title || T('（无片名）', '(untitled)', '（無題）')) + '</span>' +
      (tr ? '<em>' + T('已复盘', 'done', '済') + '</em>' : '') + '</div>' +
      '<div class="cap-ep"><span>' + T('集数', 'Episode', '話') + '</span>' +
      '<input type="number" min="0" class="cap-epi" value="' + esc(epi) + '"></div>' +
      '<div class="cap-label">' + T('现象', 'Observed', '現象') + '</div>' +
      '<div class="chips" data-field="phenomena">' + chipRow('phenomenon', ph, 'slug') + '</div>' +
      '<div class="cap-label">' + T('推测', 'Speculation', '推測') + '</div>' +
      '<div class="chips" data-field="speculations">' + chipRow('speculation', sp, 'slug') + '</div>' +
      '<div class="cap-label">' + T('如果是我', 'What I would do', '自分なら') + '</div>' +
      '<textarea class="cap-take">' + esc((tr && tr.my_take) || '') + '</textarea>' +
      '<div class="cap-actions"><button type="button" class="cap-save">' + T('保存复盘', 'Save triage', '保存') + '</button>' +
      (tr ? '<button type="button" class="cap-clear">' + T('清空复盘', 'Clear', 'クリア') + '</button>' : '') +
      '<button type="button" class="cap-del">' + T('删除', 'Delete', '削除') + '</button></div>' +
      '</div>';
  }

  function render() {
    const box = $('cap-list');
    if (!box) return;
    const count = $('cap-count');
    if (items === null) {
      box.innerHTML = '<p class="empty">' + T('正在读取…', 'Loading…', '読み込み中…') + '</p>';
      return;
    }
    if (count) count.textContent = items.length + T(' 条记录', ' records', ' 件');
    if (!items.length) {
      box.innerHTML = '<p class="empty">' + T('还没有记录。播放时按 ⌃⌥K，或点右上「新建手记」。', 'No records yet.', 'まだありません。') + '</p>';
      return;
    }
    box.innerHTML = items.map((it) => (it.note ? noteCard(it) : captureCard(it))).join('');
  }

  function buildDraft() {
    const groups = new Map();
    (items || []).forEach((item) => {
      const c = item.capture || {};
      const n = item.note;
      const title = (n && n.title) || c.title || T('（无标题）', '(untitled)', '（無題）');
      if (!groups.has(title)) groups.set(title, []);
      groups.get(title).push(item);
    });
    const out = [T('# 季度复盘草稿', '# Season review draft', '# クール振り返り草稿'), ''];
    out.push(T('生成于 ', 'Generated ', '生成: ') + new Date().toLocaleString(), '');
    Array.from(groups.keys()).sort().forEach((title) => {
      out.push('## ' + title, '');
      groups.get(title).forEach((item) => {
        const c = item.capture || {};
        const tr = item.triage || {};
        const n = item.note || {};
        const body = item.note ? n : tr;
        const ph = (Array.isArray(body.phenomena) ? body.phenomena : []).map((x) => (item.note ? x : labelOf((window.__TAGS__ || []).find((t) => t.slug === x) || { label: {}, slug: x })));
        out.push('- **' + (item.note ? T('手记', 'note', '手記') : fmt(c.t_start)) + '**' + (ph.length ? ' · ' + ph.join(' / ') : ''));
        if (body.my_take) out.push('  - ' + T('如果是我', 'What I would do', '自分なら') + ': ' + body.my_take);
      });
      out.push('');
    });
    return out.join('\n');
  }

  document.addEventListener('click', (e) => {
    const more = e.target.closest('.cap-more');
    if (more) {
      const box = more.nextElementSibling;
      const open = more.getAttribute('aria-expanded') === 'true';
      more.setAttribute('aria-expanded', open ? 'false' : 'true');
      if (box) box.hidden = open;
      return;
    }

    const dimChip = e.target.closest('#cap-hub .chips[data-dim] button');
    if (dimChip) {
      // 每个维度单选
      const box = dimChip.parentElement;
      Array.from(box.querySelectorAll('button.on')).forEach((b) => b.classList.remove('on'));
      dimChip.classList.add('on');
      return;
    }

    const chip = e.target.closest('#cap-hub .chips button');
    if (chip) { chip.classList.toggle('on'); return; }

    if (e.target.closest('#cap-new')) { send('noteadd', '1'); return; }
    if (e.target.closest('#cap-export')) {
      send('copy', buildDraft());
      const b = $('cap-export');
      if (b) { const old = b.innerHTML; b.innerHTML = T('已复制', 'Copied', 'コピー済'); setTimeout(() => { b.innerHTML = old; }, 1500); }
      return;
    }

    const card = e.target.closest('.cap-card');
    if (!card) return;
    const id = card.dataset.id;
    const kind = card.dataset.kind;

    const pick = (field) => Array.from(card.querySelectorAll('.chips[data-field="' + field + '"] button.on')).map((b) => b.dataset.key);

    if (e.target.closest('.cap-save')) {
      if (kind === 'note') {
        const dims = {};
        card.querySelectorAll('.chips[data-dim]').forEach((box) => {
          const on = box.querySelector('button.on');
          if (on) dims[box.dataset.dim] = on.dataset.dimValue;
        });
        send('noteupdate', JSON.stringify({
          id: id,
          title: card.querySelector('.cap-title').value,
          phenomena: pick('phenomena'),
          speculations: pick('speculations'),
          evidence: card.querySelector('.cap-ev').value,
          my_take: card.querySelector('.cap-take').value,
          dims: dims,
        }));
      } else {
        send('triagesave', JSON.stringify({
          note_id: id,
          episode: Number(card.querySelector('.cap-epi').value) || undefined,
          phenomena: pick('phenomena'),
          speculations: pick('speculations').map((tag) => ({ tag })),
          my_take: card.querySelector('.cap-take').value,
        }));
      }
      const b = card.querySelector('.cap-save');
      b.textContent = T('已保存', 'Saved', '保存しました');
      lastPayload = '';
      setTimeout(() => window.__loadCaptures(), 300);
      return;
    }

    if (e.target.closest('.cap-clear')) {
      send('triagesave', JSON.stringify({ note_id: id, clear: true }));
      lastPayload = '';
      setTimeout(() => window.__loadCaptures(), 300);
      return;
    }

    const del = e.target.closest('.cap-del');
    if (del) {
      if (!del.classList.contains('confirm')) {
        del.classList.add('confirm');
        del.textContent = T('确认删除', 'Sure?', '削除する');
        return;
      }
      send(kind === 'note' ? 'notedelete' : 'capturedelete', id);
      lastPayload = '';
      setTimeout(() => window.__loadCaptures(), 300);
    }
  });
})();
</script>
"""

CAPTURES_JS = CAPTURES_JS.replace("%%TAGS_JSON%%", _TAGS_JSON)
