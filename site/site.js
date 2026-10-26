/* site.js — optional progressive enhancement. Without JS every table is shown in full, journal names link to
   the journal homepage and the filter tags are plain links (publications.html?journal=…), chips are anchors.
   URL params: q, year, project, journal, venue, topic, status (all tables) and status-<section> (one table). */
(function () {
  const bar = document.querySelector('.filters');
  const tables = [...document.querySelectorAll('table.data[data-filterable]')];
  if (!bar || !tables.length) return;
  bar.hidden = false;
  const rows = tables.flatMap(t => [...t.tBodies[0].rows]);
  const f = n => bar.elements[n], count = bar.querySelector('.count');
  const uniq = a => [...new Set(a.filter(Boolean))];
  // Year
  uniq(rows.map(r => r.dataset.year)).sort().reverse()
    .forEach(v => f('year').add(new Option(v === 'in-review' ? 'Submitted / accepted (no date)' : v, v)));
  // Project (labels = chip short titles; fct = funder)
  const pLabel = k => { const b = document.querySelector(`.c-projects .badge.project[data-project="${k}"]`); return b ? b.textContent : (k === 'fct' ? 'FCT (funder)' : k); };
  uniq(rows.flatMap(r => r.dataset.projects.split(' '))).map(k => [k, pLabel(k)])
    .sort((a, b) => a[1].localeCompare(b[1])).forEach(([k, l]) => f('project').add(new Option(l, k)));
  // Journal / venue: one select, two optgroups; value "journal:<slug>" or "venue:<id>"
  const grp = (label, kind) => {
    const g = document.createElement('optgroup'); g.label = label;
    const m = new Map(rows.filter(r => r.dataset[kind]).map(r => [r.dataset[kind], r.dataset[kind + 'Label']]));
    [...m].sort((a, b) => a[1].localeCompare(b[1])).forEach(([v, l]) => g.append(new Option(l, kind + ':' + v)));
    f('venue').append(g);
  };
  grp('Journals', 'journal'); grp('Conference series', 'venue');
  // Per-table status segmented controls
  const st = {};
  document.querySelectorAll('.status-filter').forEach(g => {
    g.hidden = false; st[g.dataset.section] = '';
    g.addEventListener('click', ev => { const b = ev.target.closest('button'); if (!b) return; st[g.dataset.section] = b.dataset.status; apply(); });
  });
  const qs = new URLSearchParams(location.search);
  ['q', 'year', 'project'].forEach(n => qs.get(n) && (f(n).value = qs.get(n)));
  if (qs.get('journal')) f('venue').value = 'journal:' + qs.get('journal');
  else if (qs.get('venue')) f('venue').value = 'venue:' + qs.get('venue');
  Object.keys(st).forEach(id => {
    const v = qs.get('status-' + id) || qs.get('status') || '';
    if (document.querySelector(`.status-filter[data-section="${id}"] [data-status="${v}"]`)) st[id] = v;
  });
  // Filter tags next to journal / venue names
  document.addEventListener('click', ev => {
    const a = ev.target.closest('a.tag-filter'); if (!a) return;
    ev.preventDefault(); f('venue').value = a.dataset.filter + ':' + a.dataset.value; apply();
    bar.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  function apply() {
    const tp = qs.get('topic');   // homepage research-topic chips: ?topic=<id> (bib `keywords`)
    const q = f('q').value.trim().toLowerCase(), y = f('year').value, p = f('project').value;
    const [vk, vv] = f('venue').value ? f('venue').value.split(/:(.*)/) : [null, null];
    let shown = 0;
    tables.forEach(t => {
      const id = t.dataset.section, s = st[id] || '';
      let n = 0;
      for (const r of t.tBodies[0].rows) {
        const d = r.dataset;
        const ok = (!q || r.textContent.toLowerCase().includes(q)) && (!y || d.year === y) &&
          (!p || (' ' + d.projects + ' ').includes(' ' + p + ' ')) && (!vk || d[vk] === vv) &&
          (!s || d.status === s) && (!tp || (' ' + (d.topics || '') + ' ').includes(' ' + tp + ' '));
        r.hidden = !ok; n += ok;
      }
      const sec = t.closest('section');
      document.querySelectorAll(`[data-for="${id}"]`).forEach(el => el.textContent = n);
      document.querySelector(`.chip[href="#${id}"]`)?.classList.toggle('is-empty', !n);
      sec.querySelectorAll('.status-filter button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.status === s)));
      sec.querySelector('.table-wrap').hidden = !n; sec.querySelector('.empty-msg').hidden = !!n;
      shown += n;
    });
    count.textContent = shown + ' of ' + rows.length;
    const u = new URL(location);
    ['q', 'year', 'project'].forEach(n => f(n).value ? u.searchParams.set(n, f(n).value) : u.searchParams.delete(n));
    ['journal', 'venue', 'status', 'award'].forEach(n => u.searchParams.delete(n));
    if (vk) u.searchParams.set(vk, vv);
    Object.entries(st).forEach(([id, v]) => v ? u.searchParams.set('status-' + id, v) : u.searchParams.delete('status-' + id));
    tp ? u.searchParams.set('topic', tp) : u.searchParams.delete('topic');
    history.replaceState(null, '', u);
  }
  bar.addEventListener('input', apply);
  bar.addEventListener('reset', () => { qs.delete('topic'); Object.keys(st).forEach(k => st[k] = ''); setTimeout(apply); });
  apply();
})();
