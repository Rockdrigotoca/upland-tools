/* Click a column header to sort any table on the page; click again to reverse. Works on tables that are drawn again later:
   the chosen order is kept per table (by its position and the active tab) and re-applied after every redraw. */
(function(){
  const css = document.createElement('style');
  css.textContent = 'th.sortable{cursor:pointer;user-select:none}th.sortable:hover{color:var(--text)}th.sortable.asc::after{content:" ▲";font-size:.7em}th.sortable.desc::after{content:" ▼";font-size:.7em}';
  document.head.appendChild(css);
  const state = {};
  const tabOf = () => { const b = document.querySelector('.boxtab.on'); return b ? b.dataset.tab : ''; };
  const keyOf = table => [...document.querySelectorAll('table')].indexOf(table) + '|' + tabOf();
  const num = s => { const m = String(s).replace(/,/g, '').match(/-?\d+(\.\d+)?/); return m ? parseFloat(m[0]) : null; };
  function sortTable(table, col, dir){
    const body = table.tBodies[0]; if(!body) return;
    const rows = [...body.rows].filter(r => r.cells.length > col);
    if(!rows.length) return;
    const numeric = rows.some(r => r.cells[col].classList.contains('n'));
    const val = r => { const c = r.cells[col]; const s = c.dataset.v !== undefined ? c.dataset.v : c.textContent.trim(); return numeric ? num(s) : s.toLowerCase(); };
    const keyed = rows.map((r, i) => ({r, i, v: val(r)}));
    keyed.sort((a, b) => {
      const av = a.v, bv = b.v;
      if(av === null || av === '') return bv === null || bv === '' ? a.i - b.i : 1;
      if(bv === null || bv === '') return -1;
      const c = numeric ? av - bv : String(av).localeCompare(String(bv), undefined, {numeric: true});
      return (dir === 'desc' ? -c : c) || a.i - b.i;
    });
    keyed.forEach(k => body.appendChild(k.r));
    table.querySelectorAll('th').forEach((th, i) => { th.classList.toggle('asc', i === col && dir === 'asc'); th.classList.toggle('desc', i === col && dir === 'desc'); });
  }
  let busy = false;
  function refresh(){
    if(busy) return; busy = true;
    document.querySelectorAll('table').forEach(table => {
      table.querySelectorAll('thead th').forEach(th => { if(th.textContent.trim()) th.classList.add('sortable'); });
      const s = state[keyOf(table)];
      if(s && !table.dataset.sorted) { sortTable(table, s.col, s.dir); table.dataset.sorted = '1'; }
    });
    busy = false;
  }
  document.addEventListener('click', e => {
    const th = e.target.closest('th.sortable'); if(!th) return;
    const table = th.closest('table'), col = [...th.parentNode.children].indexOf(th), k = keyOf(table), cur = state[k];
    const dir = cur && cur.col === col && cur.dir === 'asc' ? 'desc' : (cur && cur.col === col ? 'asc' : (th.classList.contains('n') ? 'desc' : 'asc'));
    state[k] = {col, dir};
    sortTable(table, col, dir);
  });
  let timer = null;
  new MutationObserver(() => { if(busy) return; clearTimeout(timer); timer = setTimeout(refresh, 30); }).observe(document.body, {childList: true, subtree: true});
  refresh();
})();
