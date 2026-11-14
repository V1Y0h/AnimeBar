"""捕获页：Mac 端的 Inbox / 复盘。数据与 DSH 端共用，写自己的 triage-mac.jsonl。"""

import json as _json

from notes_tab import _load_tags  # 复用同一份标签词表

CAPTURES_HTML = """
<main id="view-captures" hidden>
  <div class="caps-wrap">
    <div id="cap-list"></div>
  </div>
</main>
<style>
  .caps-wrap { max-width: 880px; margin: 0 auto; padding: 4px 2px 20px; }
  .cap-card { border: 1px solid #1e293b; border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: #0b1220; }
  .cap-head { display: flex; gap: 8px; align-items: baseline; font-size: 13px; margin-bottom: 6px; }
  .cap-head b { font-variant-numeric: tabular-nums; color: #22c55e; }
  .cap-head em { font-style: normal; font-size: 11px; color: #22c55e; border: 1px solid #166534; border-radius: 999px; padding: 0 6px; }
  .cap-label { font-size: 11px; color: #64748b; margin: 6px 0 3px; }
  .cap-take { width: 100%; box-sizing: border-box; min-height: 48px; resize: vertical; background: #020617; border: 1px solid #1e293b; border-radius: 7px; color: #e2e8f0; font-size: 12px; padding: 6px 8px; font-family: inherit; }
  .cap-save { margin-top: 8px; border: 1px solid #22c55e; background: #22c55e; color: #04140a; border-radius: 7px; padding: 5px 14px; font-size: 12px; font-weight: 600; cursor: pointer; }
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

  let items = null;

  window.__initCaptures = (data) => {
    items = (data && data.items) || [];
    render();
  };

  window.__loadCaptures = () => {
    const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.captures;
    if (h) h.postMessage('1');
  };

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
    if (items === null) {
      box.innerHTML = '<p class="empty">' + T('正在读取…', 'Loading…', '読み込み中…') + '</p>';
      return;
    }
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
        '<div class="cap-head"><b>' + fmt(c.t_start) + '</b>' +
        '<span>' + esc(c.title || T('（无片名）', '(untitled)', '（無題）')) + '</span>' +
        (tr ? '<em>' + T('已复盘', 'done', '済') + '</em>' : '') + '</div>' +
        '<div class="cap-label">' + T('现象', 'Observed', '現象') + '</div>' +
        '<div class="chips" data-kind="phenomenon">' + chipRow('phenomenon', ph) + '</div>' +
        '<div class="cap-label">' + T('推测', 'Speculation', '推測') + '</div>' +
        '<div class="chips" data-kind="speculation">' + chipRow('speculation', sp) + '</div>' +
        '<div class="cap-label">' + T('如果是我', 'What I would do', '自分なら') + '</div>' +
        '<textarea class="cap-take">' + esc((tr && tr.my_take) || '') + '</textarea>' +
        '<button type="button" class="cap-save">' + T('保存复盘', 'Save triage', '保存') + '</button>' +
        '</div>';
    }).join('');
  }

  document.addEventListener('click', (e) => {
    const chip = e.target.closest('#view-captures .chips button');
    if (chip) { chip.classList.toggle('on'); return; }

    const save = e.target.closest('#view-captures .cap-save');
    if (!save) return;
    const card = save.closest('.cap-card');
    if (!card) return;

    const pick = (kind) => Array.from(
      card.querySelectorAll('.chips[data-kind="' + kind + '"] button.on')
    ).map((b) => b.dataset.slug);

    const payload = {
      note_id: card.dataset.id,
      phenomena: pick('phenomenon'),
      speculations: pick('speculation').map((tag) => ({ tag })),
      my_take: card.querySelector('.cap-take').value,
    };

    const h = window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.triagesave;
    if (h) {
      h.postMessage(JSON.stringify(payload));
      save.textContent = T('已保存', 'Saved', '保存しました');
      setTimeout(() => window.__loadCaptures(), 300);
    }
  });
})();
</script>
"""

CAPTURES_JS = CAPTURES_JS.replace("%%TAGS_JSON%%", _TAGS_JSON)
