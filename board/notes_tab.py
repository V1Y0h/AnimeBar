"""记录页：制作人视角。独立模块，主模板只做两处占位插入。"""

NOTES_HTML = """
<main id="view-notes" hidden>
  <div class="notes-wrap">
    <label><span class="l-zh">作品名</span><span class="l-en">Title</span></label>
    <input id="n-title" data-zh="哪一部" data-en="Which title" placeholder="哪一部">
    <label><span class="l-zh">现象</span><span class="l-en">Symptoms</span></label>
    <div class="chips" id="n-phenomena">
      <button type="button" data-tag="静止画多"><span class="l-zh">静止画多</span><span class="l-en">Many stills</span></button>
      <button type="button" data-tag="精度落差"><span class="l-zh">精度落差</span><span class="l-en">Quality drop</span></button>
      <button type="button" data-tag="画风突变"><span class="l-zh">画风突变</span><span class="l-en">Style shift</span></button>
      <button type="button" data-tag="重复镜头"><span class="l-zh">重复镜头</span><span class="l-en">Repeated shots</span></button>
      <button type="button" data-tag="演出神回"><span class="l-zh">演出神回</span><span class="l-en">Standout episode</span></button>
      <button type="button" data-tag="评分分歧"><span class="l-zh">评分分歧</span><span class="l-en">Score divergence</span></button>
    </div>
    <label><span class="l-zh">推测</span><span class="l-en">Speculation</span></label>
    <div class="chips" id="n-speculations">
      <button type="button" data-tag="疑似外包"><span class="l-zh">疑似外包</span><span class="l-en">Outsourcing?</span></button>
      <button type="button" data-tag="工期紧张"><span class="l-zh">工期紧张</span><span class="l-en">Schedule crunch</span></button>
      <button type="button" data-tag="作监尽力"><span class="l-zh">作监尽力</span><span class="l-en">AD carried it</span></button>
      <button type="button" data-tag="资方干预"><span class="l-zh">资方干预</span><span class="l-en">Producer meddling</span></button>
    </div>
    <input id="n-evidence" data-zh="依据" data-en="Evidence" placeholder="依据">
    <label><span class="l-zh">维度</span><span class="l-en">Dimensions</span></label>
    <label><span class="l-zh">作画</span><span class="l-en">sakuga</span><span class="l-ja">作画</span></label>
    <div class="chips" data-dim="art">
      <button type="button" data-tag="值得学习"><span class="l-zh">值得学习</span><span class="l-en">Worth studying</span></button>
      <button type="button" data-tag="中规中矩"><span class="l-zh">中规中矩</span><span class="l-en">By the book</span></button>
      <button type="button" data-tag="有待提高"><span class="l-zh">有待提高</span><span class="l-en">Needs work</span></button>
    </div>
    <label><span class="l-zh">演出</span><span class="l-en">direction</span><span class="l-ja">演出</span></label>
    <div class="chips" data-dim="staging">
      <button type="button" data-tag="有巧思"><span class="l-zh">有巧思</span><span class="l-en">Clever</span></button>
      <button type="button" data-tag="平淡"><span class="l-zh">平淡</span><span class="l-en">Flat</span></button>
      <button type="button" data-tag="用力过猛"><span class="l-zh">用力过猛</span><span class="l-en">Overwrought</span></button>
    </div>
    <label><span class="l-zh">声音</span><span class="l-en">sound</span><span class="l-ja">音響</span></label>
    <div class="chips" data-dim="sound">
      <button type="button" data-tag="加分项"><span class="l-zh">加分项</span><span class="l-en">Adds value</span></button>
      <button type="button" data-tag="无感"><span class="l-zh">无感</span><span class="l-en">Forgettable</span></button>
      <button type="button" data-tag="出戏"><span class="l-zh">出戏</span><span class="l-en">Breaks immersion</span></button>
    </div>
    <label><span class="l-zh">如果是我</span><span class="l-en">What I would do</span></label>
    <textarea id="n-reflection" data-zh="反思" data-en="Reflection" placeholder="反思"></textarea>
    <div class="nbar">
      <button type="button" id="n-save" class="primary"><span class="l-zh">保存</span><span class="l-en">Save</span></button>
      <button type="button" id="n-copy" class="ghost"><span class="l-zh">复制 Markdown</span><span class="l-en">Copy Markdown</span></button>
      <span id="n-count"></span>
    </div>
    <div id="n-list"></div>
  </div>
</main>
"""

NOTES_JS = r"""
<script>
(function () {
  const KEY = 'animebar.notes.v1';
  const $ = (id) => document.getElementById(id);
  const lang = () => (document.body.classList.contains('ja') ? 'ja' : document.body.classList.contains('en') ? 'en' : 'zh');
  const T = (zh, en, ja) => (lang() === 'ja' ? (ja || en) : lang() === 'en' ? en : zh);
  const esc = (t) => String(t == null ? '' : t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let notes = (() => { try { return JSON.parse(localStorage.getItem(KEY) || '[]'); } catch (e) { return []; } })();
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(notes)); } catch (e) {} };

  document.querySelectorAll('#view-notes .chips').forEach((box) => {
    box.addEventListener('click', (e) => {
      const b = e.target.closest('button[data-tag]');
      if (!b) return;
      if (box.dataset.dim) {
        box.querySelectorAll('button').forEach((x) => x.classList.remove('on'));
        b.classList.add('on');
      } else b.classList.toggle('on');
    });
  });

  function render() {
    $('n-count').textContent = notes.length + T(' 条记录', ' notes');
    const list = $('n-list');
    if (!notes.length) { list.innerHTML = '<p class="empty">' + T('还没有记录', 'No notes yet') + '</p>'; return; }
    list.innerHTML = notes.map((n) => '<div class="note"><div class="note-head"><b>' + esc(n.title) + '</b>'
      + '<button class="del" data-id="' + n.id + '">' + T('删除', 'Delete') + '</button></div>'
      + (n.tags.length ? '<div class="note-tags">' + esc(n.tags.join(' · ')) + '</div>' : '')
      + (n.reflection ? '<div class="note-ref">' + T('如果是我：', 'If it were me: ') + esc(n.reflection) + '</div>' : '')
      + '</div>').join('');
    list.querySelectorAll('.del').forEach((b) => {
      b.onclick = () => { notes = notes.filter((x) => x.id !== b.dataset.id); save(); render(); };
    });
  }

  $('n-save').onclick = () => {
    const title = $('n-title').value.trim();
    if (!title) { $('n-title').focus(); return; }
    const tags = [];
    ['n-phenomena', 'n-speculations'].forEach((id) => {
      document.querySelectorAll('#' + id + ' button.on').forEach((b) => tags.push(b.dataset.tag));
    });
    document.querySelectorAll('#view-notes .chips[data-dim] button.on').forEach((b) => tags.push(b.dataset.tag));
    notes = [{ id: String(Date.now()), title, tags, evidence: $('n-evidence').value.trim(), reflection: $('n-reflection').value.trim() }].concat(notes);
    save(); render();
    $('n-reflection').value = ''; $('n-evidence').value = '';
    document.querySelectorAll('#view-notes .chips button.on').forEach((b) => b.classList.remove('on'));
  };

  $('n-copy').onclick = () => {
    const byTitle = {};
    notes.forEach((n) => { (byTitle[n.title] = byTitle[n.title] || []).push(n); });
    const out = ['# 制作人视角记录', ''];
    Object.keys(byTitle).forEach((t) => {
      out.push('## ' + t, '');
      byTitle[t].forEach((n) => {
        out.push('- 记录');
        if (n.tags.length) out.push('  - 标签：' + n.tags.join('、'));
        if (n.evidence) out.push('  - 依据：' + n.evidence);
        if (n.reflection) out.push('  - 如果是我：' + n.reflection);
      });
      out.push('');
    });
    const ta = document.createElement('textarea');
    ta.value = out.join('\n');
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
    $('n-copy').querySelectorAll('span').forEach((s) => { s.textContent = T('已复制', 'Copied'); });
    setTimeout(() => { $('n-copy').querySelectorAll('span').forEach((s) => { s.textContent = s.className === 'l-en' ? 'Copy Markdown' : '复制 Markdown'; }); }, 1500);
  };

  document.addEventListener('click', (e) => {
    const b = e.target.closest('button.note');
    if (!b) return;
    const tab = document.querySelector('button[data-mode="notes"]');
    if (tab) tab.click();
    const card = b.closest('.card');
    const h3 = card && card.querySelector('h3');
    $('n-title').value = (h3 && h3.getAttribute('title')) || b.dataset.name || '';
    $('n-title').focus();
  });

  function syncPlaceholders() {
    const en = isEn();
    document.querySelectorAll('#view-notes [data-zh][data-en]').forEach((el) => {
      el.placeholder = en ? el.dataset.en : el.dataset.zh;
    });
  }
  const langBtn = document.getElementById('lang');
  if (langBtn) langBtn.addEventListener('click', () => setTimeout(syncPlaceholders, 0));
  syncPlaceholders();
  document.addEventListener('animebar-lang', () => { syncPlaceholders(); render(); });
  render();
})();
</script>
"""
