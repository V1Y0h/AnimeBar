"""捕获页：Mac 端的 Inbox / 复盘。数据与 DSH 端共用，写自己的 triage-mac.jsonl。"""

import json as _json

from notes_tab import _load_tags  # 复用同一份标签词表

CAPTURES_HTML = """
<main id="view-captures" hidden>
  <div class="caps-wrap">
    <div class="caps-head">
      <span id="cap-count"></span>
      <button type="button" id="cap-export">导出草稿</button>
    </div>
    <div id="cap-list"></div>
  </div>
</main>
<style>
  .caps-wrap { max-width: 880px; margin: 0 auto; padding: 4px 2px 20px; }
  .caps-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: #64748b; }
  .caps-head span { flex: 1; }
  .caps-head button { border: 1px solid #1e293b; background: transparent; color: #94a3b8; border-radius: 7px; padding: 3px 10px; font-size: 12px; cursor: pointer; }
  .cap-card { border: 1px solid #1e293b; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: #0b1220; }
  .cap-head-row { display: flex; gap: 8px; align-items: baseline; font-size: 13px; margin-bottom: 6px; }
  .cap-head-row b { font-variant-numeric: tabular-nums; color: #22c55e; }
  .cap-head-row em { font-style: normal; font-size: 11px; color: #22c55e; border: 1px solid #166534; border-radius: 999px; padding: 0 6px; }
  .cap-label { font-size: 11px; color: #64748b; margin: 6px 0 3px; }
  .cap-take { width: 100%; box-sizing: border-box; min-height: 48px; resize: vertical; background: #020617; border: 1px solid #1e293b; border-radius: 7px; color: #e2e8f0; font-size: 12px; padding: 6px 8px; font-family: inherit; }
  .cap-actions { margin-top: 8px; display: flex; gap: 6px; align-items: center; }
  .cap-actions button { border-radius: 7px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
  .cap-save { border: 1px solid #22c55e; background: #22c55e; color: #04140a; font-weight: 600; }
  .cap-clear, .cap-del { border: 1px solid #1e293b; background: transparent; color: #94a3b8; }
  .cap-del.confirm { border-color: #b91c1c; color: #fca5a5; }
</style>
"""

_TAGS_JSON = _json.dumps(
    [
        {
            "slug": t.get("slug"),
            "kind": t.get("kind"),
            "label": {
                k: ((t.get("label") or {}).get(k) or t.get("slug"))
                for k in ("zh", "en", "ja")
            },
        }
        for t in _load_tags()
        if t.get("kind") in ("phenomenon", "speculation")
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
  const send = (name, body) => {
    const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers[name];
    if (h) h.postMessage(body);
    return !!h;
  };

  let items = null;

  window.__initCaptures = (data) => {
    items = (data && data.items) || [];
    render();
  };

  window.__loadCaptures = () => send('captures', '1');

  function chipRow(kind, selected) {
    return (window.__TAGS__ || [])
      .filter((t) => t.kind === kind)
      .map((t) => '<button type="button" data-slug="' + esc(t.slug) + '"' +
        (selected.indexOf(t.slug) >= 0 ? ' class="on"' : '') + '>' + esc(labelOf(t)) + '</button>')
      .join('');
  }

  function render() {
    const box = $('cap-list');
    if (!box) return;
    const count = $('cap-count');
    if (items === null) {
      if (count) count.textContent = '';
      box.innerHTML = '<p class="empty">' + T('正在读取…', 'Loading…', '読み込み中…') + '</p>';
      return;
    }
    if (count) count.textContent = items.length + T(' 条捕获', ' captures', ' 件');
    if (!items.length) {
      box.innerHTML = '<p class="empty">' + T('还没有捕获。播放时按 ⌃⌥K。', 'No captures yet. Press ⌃⌥K while playing.', 'まだありません。⌃⌥K。') + '</p>';
      return;
    }
    box.innerHTML = items.map((item) => {
      const c = item.capture || {};
      const tr = item.triage;
      const ph = (tr && Array.isArray(tr.phenomena)) ? tr.phenomena : [];
      const sp = (tr && Array.isArray(tr.speculations))
        ? tr.speculations.map((x) => (x && x.tag) || '').filter(Boolean)
        : [];
      return '<div class="cap-card" data-id="' + esc(c.note_id) + '">' +
        '<div class="cap-head-row"><b>' + fmt(c.t_start) + '</b>' +
        '<span>' + esc(c.title || T('（无片名）', '(untitled)', '（無題）')) + '</span>' +
        (tr ? '<em>' + T('已复盘', 'done', '済') + '</em>' : '') + '</div>' +
        '<div class="cap-label">' + T('现象', 'Observed', '現象') + '</div>' +
        '<div class="chips" data-kind="phenomenon">' + chipRow('phenomenon', ph) + '</div>' +
        '<div class="cap-label">' + T('推测', 'Speculation', '推測') + '</div>' +
        '<div class="chips" data-kind="speculation">' + chipRow('speculation', sp) + '</div>' +
        '<div class="cap-label">' + T('如果是我', 'What I would do', '自分なら') + '</div>' +
        '<textarea class="cap-take">' + esc((tr && tr.my_take) || '') + '</textarea>' +
        '<div class="cap-actions">' +
          '<button type="button" class="cap-save">' + T('保存复盘', 'Save triage', '保存') + '</button>' +
          (tr ? '<button type="button" class="cap-clear">' + T('清空复盘', 'Clear triage', '整理をクリア') + '</button>' : '') +
          '<button type="button" class="cap-del">' + T('删除', 'Delete', '削除') + '</button>' +
        '</div>' +
        '</div>';
    }).join('');
  }

  // 导出草稿：纯本地生成，结果交给宿主的 copy 处理器进剪贴板
  function buildDraft() {
    const groups = new Map();
    (items || []).forEach((item) => {
      const c = item.capture || {};
      const key = c.title || T('（无标题）', '(untitled)', '（無題）');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    const pickLabel = (slug) => {
      const tag = (window.__TAGS__ || []).find((t) => t.slug === slug);
      return tag ? labelOf(tag) : slug;
    };
    const out = [T('# 季度复盘草稿', '# Season review draft', '# クール振り返り草稿'), ''];
    out.push(T('生成于 ', 'Generated ', '生成: ') + new Date().toLocaleString(), '');
    Array.from(groups.keys()).sort().forEach((title) => {
      const rows = groups.get(title).slice().sort((a, b) => (a.capture.t_start || 0) - (b.capture.t_start || 0));
      out.push('## ' + title, '');
      rows.forEach((item) => {
        const c = item.capture || {};
        const tr = item.triage || {};
        const ph = (Array.isArray(tr.phenomena) ? tr.phenomena : []).map(pickLabel);
        const sp = (Array.isArray(tr.speculations) ? tr.speculations : [])
          .map((x) => (x && x.tag ? pickLabel(x.tag) : '')).filter(Boolean);
        out.push('- **' + fmt(c.t_start) + '**' + (ph.length ? ' · ' + ph.join(' / ') : ''));
        if (sp.length) out.push('  - ' + T('推测', 'Speculation', '推測') + ': ' + sp.join(' / '));
        if (tr.my_take) out.push('  - ' + T('如果是我', 'What I would do', '自分なら') + ': ' + tr.my_take);
        if (!tr.note_id) out.push('  - ' + T('（尚未复盘）', '(not triaged)', '（未整理）'));
      });
      out.push('');
    });
    return out.join('\n');
  }

  document.addEventListener('click', (e) => {
    const chip = e.target.closest('#view-captures .chips button');
    if (chip) { chip.classList.toggle('on'); return; }

    if (e.target.closest('#cap-export')) {
      send('copy', buildDraft());
      const b = $('cap-export');
      if (b) { b.textContent = T('已复制', 'Copied', 'コピー済'); setTimeout(() => { b.textContent = T('导出草稿', 'Export draft', '書き出す'); }, 1500); }
      return;
    }

    const card = e.target.closest('#view-captures .cap-card');
    if (!card) return;
    const noteID = card.dataset.id;

    if (e.target.closest('.cap-save')) {
      const pick = (kind) => Array.from(card.querySelectorAll('.chips[data-kind="' + kind + '"] button.on')).map((b) => b.dataset.slug);
      send('triagesave', JSON.stringify({
        note_id: noteID,
        phenomena: pick('phenomenon'),
        speculations: pick('speculation').map((tag) => ({ tag })),
        my_take: card.querySelector('.cap-take').value,
      }));
      const b = card.querySelector('.cap-save');
      b.textContent = T('已保存', 'Saved', '保存しました');
      setTimeout(() => window.__loadCaptures(), 300);
      return;
    }

    if (e.target.closest('.cap-clear')) {
      send('triagesave', JSON.stringify({ note_id: noteID, clear: true }));
      setTimeout(() => window.__loadCaptures(), 300);
      return;
    }

    const del = e.target.closest('.cap-del');
    if (del) {
      // 两次点击确认，避免误删
      if (!del.classList.contains('confirm')) {
        del.classList.add('confirm');
        del.textContent = T('确认删除', 'Sure?', '削除する');
        return;
      }
      send('capturedelete', noteID);
      setTimeout(() => window.__loadCaptures(), 300);
    }
  });
})();
</script>
"""

CAPTURES_JS = CAPTURES_JS.replace("%%TAGS_JSON%%", _TAGS_JSON)
