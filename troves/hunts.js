// The hunting log: charts made from the session exports kept in data/troves/rockdrigo/hunts.json (see tools/hunts.py).
// Everything is drawn as inline SVG so it follows the light/dark theme and needs no library.
window.Hunt = (() => {
  const TXT = {
    en: {
      h:'Hunting log', n:'Every find from your exported hunting sessions, {from} to {to}. Times are in your own time zone.',
      kFinds:'finds', kTroves:'troves (with quantities)', kProps:'properties', kTypes:'trove types', kMin:'active minutes', kRate:'finds a minute', kDays:'days',
      sDay:'Finds per day', sDayN:'What each day gave, by where it came from.', sMin:'Active minutes', sRate:'Finds per active minute',
      kindStruct:'Structures', kindPlant:'Plants', kindBalloon:'Balloons',
      sHeat:'When you hunt', sHeatN:'Finds by day and hour. The darker the square, the more you found in that hour.',
      sSes:'Time spent against what you found', sSesN:'Each dot is one session (a break of 20 minutes or more starts a new one). Bigger dots visited more properties.', axMin:'minutes in the session', axFinds:'finds',
      sCor:'What goes with more finds', cor1:'Longer sessions give more finds: r = {r}.', cor2:'Visiting more different properties raises finds a minute: r = {r}.', cor3:'Share of plants in a session against finds a minute: r = {r}.', corNote:'r runs from −1 to 1; near 0 means no link.',
      sDisc:'How fast new troves appear', sDiscN:'Different trove types found so far, find after find. The flatter it gets, the more each new find repeats something you have.', axN:'find number', axT:'types',
      sPar:'A few troves are most of what you find', sParN:'Share of all finds covered by the top troves, most common first.', axRank:'trove types, most common first', axShare:'share of finds',
      sCity:'City by city', cCity:'City', cFinds:'Finds', cProps:'Properties', cPer:'Finds per property', cTypes:'Types', cPlant:'Plants', cMin:'Minutes', cRate:'Per minute',
      sCat:'What kind of troves', sCatN:'Area is the number of troves found. Colour is the category.', sCatCity:'Category mix per city',
      sLvl:'Finds against what you hold', sLvlN:'Each dot is one trove type: how many times you found it against how many you hold now. Colour is the banked level. Above the line you also crafted or earned it another way.', axHold:'held now',
      sLvlBar:'Banked level of the types you found', lv:'level {n}', lvNone:'level 0',
      sSrc:'Where the finds came from', sSrcN:'The sources that gave the most, and how many different troves each one gave.', cSrc:'Source', cDiff:'Different troves',
      sGap:'How long you waited between visits to the same place', sGapN:'Minutes between two finds at the same structure or plant. A visit again inside the hour gives Trove Dust, not a new trove.', axGap:'minutes since the last visit', axCount:'visits',
      sDust:'Trove Dust by waiting time', sDustN:'Share of finds that were Trove Dust, by minutes since the previous visit to that same place. Balloons are left out.', axDust:'share that was Trove Dust',
      sBal:'The balloon event', sBalN:'Balloons were an event and ended on Saturday 31 October. Here is how it went.', bF:'balloon finds', bB:'different balloons', bD:'days', bDust:'Trove Dust', bRep:'second visits',
      sBalDay:'Balloon finds per day, by balloon', sBalTop:'What balloons gave', sBalTable:'Day by day', cDay:'Day', cBal:'Balloons', cRep:'Revisits', cDustN:'Dust', cQty:'Troves',
      sBalVs:'A balloon against a structure', bVs:'Different troves per 100 finds: balloons {a}, structures {b}, plants {c}. Trove Dust: balloons {d}%, structures {e}%, plants {f}%.',
      none:'Nothing yet.', loading:'Loading the hunting log…', model:{traditional:'Classic', turkey:'Turkey', eye:'Eye', cat:'Cat', pumpkin:'Pumpkin'},
    },
    es: {
      h:'Registro de caza', n:'Todos los hallazgos de tus sesiones exportadas, del {from} al {to}. Las horas son de tu zona horaria.',
      kFinds:'hallazgos', kTroves:'troves (con cantidades)', kProps:'propiedades', kTypes:'tipos de trove', kMin:'minutos activos', kRate:'hallazgos por minuto', kDays:'días',
      sDay:'Hallazgos por día', sDayN:'Lo que dio cada día, según de dónde vino.', sMin:'Minutos activos', sRate:'Hallazgos por minuto activo',
      kindStruct:'Estructuras', kindPlant:'Plantas', kindBalloon:'Globos',
      sHeat:'Cuándo cazas', sHeatN:'Hallazgos por día y hora. Mientras más oscuro el cuadro, más encontraste en esa hora.',
      sSes:'Tiempo invertido contra lo que encontraste', sSesN:'Cada punto es una sesión (una pausa de 20 minutos o más inicia otra). Los puntos grandes visitaron más propiedades.', axMin:'minutos de la sesión', axFinds:'hallazgos',
      sCor:'Qué acompaña a más hallazgos', cor1:'Las sesiones más largas dan más hallazgos: r = {r}.', cor2:'Visitar más propiedades distintas sube los hallazgos por minuto: r = {r}.', cor3:'Parte de plantas en una sesión contra hallazgos por minuto: r = {r}.', corNote:'r va de −1 a 1; cerca de 0 es que no hay relación.',
      sDisc:'Qué tan rápido aparecen troves nuevos', sDiscN:'Tipos distintos de trove hallados hasta ahora, hallazgo tras hallazgo. Mientras más plana, más repite lo que ya tienes cada hallazgo nuevo.', axN:'número de hallazgo', axT:'tipos',
      sPar:'Pocos troves son la mayor parte de lo que encuentras', sParN:'Parte de todos los hallazgos que cubren los primeros troves, del más común al menos.', axRank:'tipos de trove, del más común', axShare:'parte de los hallazgos',
      sCity:'Ciudad por ciudad', cCity:'Ciudad', cFinds:'Hallazgos', cProps:'Propiedades', cPer:'Por propiedad', cTypes:'Tipos', cPlant:'Plantas', cMin:'Minutos', cRate:'Por minuto',
      sCat:'Qué tipo de troves', sCatN:'El área es la cantidad de troves hallados. El color es la categoría.', sCatCity:'Mezcla de categorías por ciudad',
      sLvl:'Hallazgos contra lo que tienes', sLvlN:'Cada punto es un tipo de trove: cuántas veces lo hallaste contra cuántos tienes ahora. El color es el nivel depositado. Sobre la línea también lo crafteaste u obtuviste de otra forma.', axHold:'que tienes ahora',
      sLvlBar:'Nivel depositado de los tipos que hallaste', lv:'nivel {n}', lvNone:'nivel 0',
      sSrc:'De dónde vinieron los hallazgos', sSrcN:'Las fuentes que más dieron y cuántos troves distintos dio cada una.', cSrc:'Fuente', cDiff:'Troves distintos',
      sGap:'Cuánto esperaste entre visitas al mismo lugar', sGapN:'Minutos entre dos hallazgos en la misma estructura o planta. Volver dentro de la hora da Trove Dust, no un trove nuevo.', axGap:'minutos desde la última visita', axCount:'visitas',
      sDust:'Trove Dust según la espera', sDustN:'Parte de los hallazgos que fueron Trove Dust, por minutos desde la visita anterior al mismo lugar. Sin globos.', axDust:'parte que fue Trove Dust',
      sBal:'El evento de globos', sBalN:'Los globos fueron un evento y terminó el sábado 31 de octubre. Así te fue.', bF:'hallazgos de globos', bB:'globos distintos', bD:'días', bDust:'Trove Dust', bRep:'segundas visitas',
      sBalDay:'Hallazgos de globos por día, por globo', sBalTop:'Lo que dieron los globos', sBalTable:'Día por día', cDay:'Día', cBal:'Globos', cRep:'Revisitas', cDustN:'Dust', cQty:'Troves',
      sBalVs:'Un globo contra una estructura', bVs:'Troves distintos por cada 100 hallazgos: globos {a}, estructuras {b}, plantas {c}. Trove Dust: globos {d}%, estructuras {e}%, plantas {f}%.',
      none:'Todavía nada.', loading:'Cargando el registro de caza…', model:{traditional:'Clásico', turkey:'Pavo', eye:'Ojo', cat:'Gato', pumpkin:'Calabaza'},
    },
  };
  const T = (k, v) => { const s = (TXT[Site.lang()] || TXT.en)[k] ?? TXT.en[k] ?? k; return typeof s === 'string' && v ? s.replace(/\{(\w+)\}/g, (_, x) => v[x] ?? '') : s; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;'}[c]));
  const n0 = x => Number(x).toLocaleString(Site.locale());
  const f1 = x => (Math.round(x * 10) / 10).toLocaleString(Site.locale());
  const pct = x => Math.round(x * 100) + '%';
  // Tableau's colour-blind-safe palette
  const CAT = {resources:'#1170aa', utility:'#fc7d0b', social:'#5fa2ce', care:'#c85200', valuables:'#57606c', junk:'#a3acb9'};
  const KIND = {structure:'#1170aa', plant:'#fc7d0b', balloon:'#a3acb9'};
  const LV = ['#7b848f', '#c85200', '#a3cce9', '#ffbc79'];
  const MODEL = ['#1170aa', '#fc7d0b', '#5fa2ce', '#c85200', '#a3acb9'];
  const AX = 'var(--muted)', GRID = 'var(--border)';

  // ---------- numbers ----------
  const pearson = (xs, ys) => {
    const n = xs.length; if(n < 3) return 0;
    const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sxx = 0, syy = 0;
    xs.forEach((x, i) => { sxy += (x - mx) * (ys[i] - my); sxx += (x - mx) ** 2; syy += (ys[i] - my) ** 2; });
    return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0;
  };
  const dayKey = ms => { const d = new Date(ms); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
  const dayLabel = k => { const [y, m, d] = k.split('-').map(Number); return new Date(y, m - 1, d).toLocaleDateString(Site.locale(), {month:'short', day:'numeric'}); };
  const niceMax = v => { if(v <= 0) return 1; const p = 10 ** Math.floor(Math.log10(v)), m = v / p; return (m <= 1.0001 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; };

  // ---------- svg pieces ----------
  const W = 640;
  const svg = (h, body, label) => `<svg viewBox="0 0 ${W} ${h}" role="img" aria-label="${esc(label || '')}" style="width:100%;height:auto;display:block;font-size:11px;font-family:inherit">${body}</svg>`;
  const legend = items => `<div class="small" style="display:flex;flex-wrap:wrap;gap:4px 14px;margin:6px 0 0">${items.map(i => `<span><b style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${i.c};vertical-align:-1px;margin-right:4px"></b>${esc(i.l)}</span>`).join('')}</div>`;
  const frame = (h, l, r, tp, b, ymax, ylab, xlab) => {
    let s = '';
    for(let i = 0; i <= 4; i++){
      const y = tp + (h - tp - b) * (1 - i / 4), v = ymax * i / 4;
      s += `<line x1="${l}" x2="${W - r}" y1="${y}" y2="${y}" stroke="${GRID}" stroke-width="1"/><text x="${l - 6}" y="${y + 3}" text-anchor="end" fill="${AX}">${v >= 1000 ? n0(Math.round(v)) : Number.isInteger(v) ? v : f1(v)}</text>`;
    }
    if(ylab) s += `<text x="${l}" y="${tp - 8}" fill="${AX}">${esc(ylab)}</text>`;
    if(xlab) s += `<text x="${W - r}" y="${h - 4}" text-anchor="end" fill="${AX}">${esc(xlab)}</text>`;
    return s;
  };
  // stacked columns: cols [{label, parts:[v...]}], colors per part
  const columns = (cols, colors, opts = {}) => {
    const h = opts.h || 190, l = 44, r = 8, tp = 16, b = 26, inner = W - l - r;
    const tot = cols.map(c => c.parts.reduce((a, b2) => a + b2, 0)), ymax = niceMax(Math.max(...tot, 1));
    const bw = inner / cols.length, pw = Math.min(bw * 0.72, 56);
    let s = frame(h, l, r, tp, b, ymax, opts.y, '');
    cols.forEach((c, i) => {
      let y = h - b; const x = l + bw * i + (bw - pw) / 2;
      c.parts.forEach((v, k) => { const hh = v / ymax * (h - tp - b); if(hh > 0){ y -= hh; s += `<rect x="${x}" y="${y}" width="${pw}" height="${hh}" fill="${colors[k]}"><title>${esc(c.label)}: ${opts.names ? esc(opts.names[k]) + ' ' : ''}${f1(v)}</title></rect>`; } });
      if(opts.total !== false && tot[i] > 0) s += `<text x="${x + pw / 2}" y="${y - 4}" text-anchor="middle" fill="var(--text)">${f1(tot[i])}</text>`;
      if(cols.length <= 14 || i % Math.ceil(cols.length / 14) === 0) s += `<text x="${x + pw / 2}" y="${h - 8}" text-anchor="middle" fill="${AX}">${esc(c.label)}</text>`;
    });
    return svg(h, s, opts.label);
  };
  const hbars = (rows, opts = {}) => {
    const rh = 22, l = opts.l || 150, r = 54, h = rows.length * rh + 8, mx = Math.max(...rows.map(x => x.v), 1);
    let s = '';
    rows.forEach((x, i) => {
      const y = 4 + i * rh, w = x.v / mx * (W - l - r);
      s += `<text x="${l - 6}" y="${y + 14}" text-anchor="end" fill="var(--text)">${esc(x.label.length > 26 ? x.label.slice(0, 25) + '…' : x.label)}</text><rect x="${l}" y="${y + 3}" width="${Math.max(w, 1)}" height="${rh - 7}" rx="3" fill="${x.c || '#1170aa'}"><title>${esc(x.label)}: ${n0(x.v)}</title></rect><text x="${l + w + 5}" y="${y + 14}" fill="${AX}">${opts.fmt ? opts.fmt(x.v) : n0(x.v)}</text>`;
    });
    return svg(h, s, opts.label);
  };
  const line = (pts, opts = {}) => {
    const h = opts.h || 200, l = 44, r = 10, tp = 16, b = 28;
    const xmax = opts.xmax || Math.max(...pts.map(p => p.x), 1), ymax = opts.ymax || niceMax(Math.max(...pts.map(p => p.y), 1));
    const X = x => l + x / xmax * (W - l - r), Y = y => h - b - y / ymax * (h - tp - b);
    let s = frame(h, l, r, tp, b, ymax, opts.ylab, opts.xlab);
    for(let i = 0; i <= 4; i++) s += `<text x="${X(xmax * i / 4)}" y="${h - 12}" text-anchor="middle" fill="${AX}">${opts.xfmt ? opts.xfmt(xmax * i / 4) : n0(Math.round(xmax * i / 4))}</text>`;
    const d = pts.map((p, i) => (i ? 'L' : 'M') + X(p.x).toFixed(1) + ' ' + Y(p.y).toFixed(1)).join('');
    s += `<path d="${d}L${X(pts[pts.length - 1].x).toFixed(1)} ${Y(0)}L${X(pts[0].x).toFixed(1)} ${Y(0)}Z" fill="${opts.c || '#1170aa'}" opacity=".16"/><path d="${d}" fill="none" stroke="${opts.c || '#1170aa'}" stroke-width="2"/>`;
    (opts.marks || []).forEach(m => { s += `<line x1="${X(m.x)}" x2="${X(m.x)}" y1="${tp}" y2="${h - b}" stroke="${AX}" stroke-dasharray="3 3"/><text x="${X(m.x) + 3}" y="${tp + 9}" fill="${AX}">${esc(m.label)}</text>`; });
    return svg(h, s, opts.label);
  };
  const scatter = (pts, opts = {}) => {
    const h = opts.h || 240, l = 44, r = 12, tp = 16, b = 30;
    const xmax = niceMax(Math.max(...pts.map(p => p.x), 1)), ymax = niceMax(Math.max(...pts.map(p => p.y), 1));
    const X = x => l + x / xmax * (W - l - r), Y = y => h - b - y / ymax * (h - tp - b);
    let s = frame(h, l, r, tp, b, ymax, opts.ylab, opts.xlab);
    for(let i = 0; i <= 4; i++) s += `<text x="${X(xmax * i / 4)}" y="${h - 14}" text-anchor="middle" fill="${AX}">${n0(Math.round(xmax * i / 4))}</text>`;
    if(opts.diag) s += `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(Math.min(xmax, ymax))}" y2="${Y(Math.min(xmax, ymax))}" stroke="${AX}" stroke-dasharray="4 4"/>`;
    pts.forEach(p => { s += `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="${p.r || 4}" fill="${p.c || '#1170aa'}" fill-opacity=".62" stroke="${p.c || '#1170aa'}"><title>${esc(p.title || '')}</title></circle>`; });
    return svg(h, s, opts.label);
  };
  const heat = (days, grid) => {
    const l = 62, r = 8, tp = 16, cw = (W - l - r) / 24, ch = 22, h = tp + days.length * ch + 20, mx = Math.max(...grid.flat(), 1);
    let s = '';
    for(let hr = 0; hr < 24; hr += 3) s += `<text x="${l + cw * hr + cw / 2}" y="${tp - 5}" text-anchor="middle" fill="${AX}">${hr}h</text>`;
    days.forEach((d, i) => {
      s += `<text x="${l - 6}" y="${tp + i * ch + 15}" text-anchor="end" fill="var(--text)">${esc(dayLabel(d))}</text>`;
      grid[i].forEach((v, hr) => { s += `<rect x="${l + cw * hr + 1}" y="${tp + i * ch + 1}" width="${cw - 2}" height="${ch - 2}" rx="3" fill="${v ? '#1170aa' : 'var(--surface-2)'}" fill-opacity="${v ? (0.14 + 0.86 * Math.sqrt(v / mx)).toFixed(2) : 1}"><title>${esc(dayLabel(d))} ${hr}h: ${v}</title></rect>`; });
    });
    return svg(h, s, '');
  };
  // slice-and-dice treemap: items [{label, v, c}] sorted by size
  const treemap = (items, h = 260) => {
    const tot = items.reduce((a, b) => a + b.v, 0) || 1; let s = '';
    const lay = (list, x, y, w, hh, vert) => {
      if(!list.length) return;
      if(list.length === 1){ const it = list[0]; s += cell(it, x, y, w, hh); return; }
      const sum = list.reduce((a, b) => a + b.v, 0); let acc = 0, k = 0;
      while(k < list.length - 1 && acc + list[k].v <= sum / 2) acc += list[k++].v;
      if(k === 0){ acc = list[0].v; k = 1; }
      const a = list.slice(0, k), bb = list.slice(k), fa = acc / sum;
      if(vert){ lay(a, x, y, w * fa, hh, !vert); lay(bb, x + w * fa, y, w * (1 - fa), hh, !vert); }
      else { lay(a, x, y, w, hh * fa, !vert); lay(bb, x, y + hh * fa, w, hh * (1 - fa), !vert); }
    };
    const cell = (it, x, y, w, hh) => `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(w - 2, 0).toFixed(1)}" height="${Math.max(hh - 2, 0).toFixed(1)}" rx="3" fill="${it.c}" fill-opacity="${it.o || 0.9}"><title>${esc(it.label)}: ${n0(it.v)}</title></rect>`
      + (w > 52 && hh > 16 ? `<text x="${(x + 5).toFixed(1)}" y="${(y + 13).toFixed(1)}" fill="#fff" style="font-size:${w > 90 ? 11 : 9}px;paint-order:stroke;stroke:rgba(0,0,0,.35);stroke-width:2px">${esc(it.label.length > Math.floor(w / 6.2) ? it.label.slice(0, Math.max(Math.floor(w / 6.2) - 1, 2)) + '…' : it.label)}</text>` : '');
    lay(items.slice().sort((a, b) => b.v - a.v), 0, 0, W, h, true);
    return svg(h, s, '');
  };
  const card = (title, note, body) => `<div class="card" style="margin-bottom:12px"><h2 style="margin:0 0 4px">${esc(title)}</h2>${note ? `<p class="hint" style="margin:0 0 8px">${esc(note)}</p>` : ''}${body}</div>`;
  const grid = parts => `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px">${parts.join('')}</div>`;
  const kpi = (v, l) => `<div style="flex:1 1 110px;background:var(--surface-2);border-radius:10px;padding:10px 12px"><div style="font-size:1.35rem;font-weight:700">${v}</div><div class="small muted">${esc(l)}</div></div>`;

  // ---------- the data ----------
  let memo = null;
  function prep(D, ctx){
    if(memo && memo.D === D && memo.bal === ctx.bal) return memo;
    const rows = D.finds.map(f => {
      const [name, skind] = D.src[f[2]], ms = f[0] * 1000;
      return {ms, day:dayKey(ms), hour:new Date(ms).getHours(), kind:skind === 'balloon' ? 'balloon' : (f[1] ? 'plant' : 'structure'), src:name, trove:D.troves[f[3]], q:f[4], pi:f[5], city:D.cities[D.props[f[5]][2]], inst:f[6]};
    });
    const days = [...new Set(rows.map(r => r.day))].sort();
    // sessions: a break of 20 minutes starts a new one
    const sessions = []; let cur = null;
    rows.forEach(r => { if(!cur || r.ms - cur.end > 20 * 6e4){ cur = {start:r.ms, end:r.ms, rows:[]}; sessions.push(cur); } cur.end = r.ms; cur.rows.push(r); });
    sessions.forEach(s => { s.min = Math.max((s.end - s.start) / 6e4, 1); s.props = new Set(s.rows.map(r => r.pi)).size; s.plants = s.rows.filter(r => r.kind === 'plant').length / s.rows.length; s.day = dayKey(s.start); });
    // gap since the last find at the same source
    const last = new Map(); rows.forEach(r => { const k = r.kind + ':' + r.inst; r.gap = last.has(k) ? (r.ms - last.get(k)) / 6e4 : null; last.set(k, r.ms); });
    memo = {D, bal:ctx.bal, rows, days, sessions};
    return memo;
  }

  function html(D, ctx){
    if(!D) return card(T('h'), '', `<p class="muted small" style="margin:0">${esc(T('loading'))}</p>`);
    const P = prep(D, ctx), rows = P.rows, days = P.days, cat = ctx.cat;
    const kinds = ['structure', 'plant', 'balloon'], kindName = {structure:T('kindStruct'), plant:T('kindPlant'), balloon:T('kindBalloon')};
    const qtotal = rows.reduce((a, r) => a + r.q, 0), minutes = P.sessions.reduce((a, s) => a + s.min, 0);
    const out = [];
    out.push(card(T('h'), T('n', {from:dayLabel(days[0]), to:dayLabel(days[days.length - 1])}),
      `<div style="display:flex;flex-wrap:wrap;gap:8px">${kpi(n0(rows.length), T('kFinds'))}${kpi(n0(qtotal), T('kTroves'))}${kpi(n0(D.props.length), T('kProps'))}${kpi(n0(D.troves.length), T('kTypes'))}${kpi(n0(Math.round(minutes)), T('kMin'))}${kpi(f1(rows.length / minutes), T('kRate'))}${kpi(days.length, T('kDays'))}</div>`));

    // per day
    const perDay = days.map(d => ({d, rows:rows.filter(r => r.day === d), min:P.sessions.filter(s => s.day === d).reduce((a, s) => a + s.min, 0)}));
    const kc = kinds.map(k => KIND[k]);
    out.push(card(T('sDay'), T('sDayN'),
      columns(perDay.map(x => ({label:dayLabel(x.d), parts:kinds.map(k => x.rows.filter(r => r.kind === k).length)})), kc, {names:kinds.map(k => kindName[k]), label:T('sDay')}) + legend(kinds.map(k => ({c:KIND[k], l:kindName[k]})))
      + grid([`<div><div class="small muted" style="margin:10px 0 2px">${esc(T('sMin'))}</div>${columns(perDay.map(x => ({label:dayLabel(x.d), parts:[Math.round(x.min)]})), ['#5fa2ce'], {h:150, label:T('sMin')})}</div>`,
        `<div><div class="small muted" style="margin:10px 0 2px">${esc(T('sRate'))}</div>${columns(perDay.map(x => ({label:dayLabel(x.d), parts:[x.min ? Math.round(x.rows.length / x.min * 10) / 10 : 0]})), ['#fc7d0b'], {h:150, label:T('sRate')})}</div>`])));

    // heat
    const g = days.map(d => { const a = new Array(24).fill(0); rows.forEach(r => { if(r.day === d) a[r.hour]++; }); return a; });
    out.push(card(T('sHeat'), T('sHeatN'), heat(days, g)));

    // sessions scatter + correlations
    const S = P.sessions.filter(s => s.rows.length >= 3);
    const rMin = pearson(S.map(s => s.min), S.map(s => s.rows.length)), rProp = pearson(S.map(s => s.props), S.map(s => s.rows.length / s.min)), rPl = pearson(S.map(s => s.plants), S.map(s => s.rows.length / s.min));
    out.push(card(T('sSes'), T('sSesN'), scatter(S.map(s => ({x:s.min, y:s.rows.length, r:Math.min(3 + Math.sqrt(s.props) * 1.3, 14), c:s.plants > .5 ? KIND.plant : KIND.structure, title:`${dayLabel(s.day)} · ${Math.round(s.min)} min · ${s.rows.length} · ${s.props}`})), {xlab:T('axMin'), ylab:T('axFinds'), label:T('sSes')})
      + legend([{c:KIND.structure, l:kindName.structure}, {c:KIND.plant, l:kindName.plant}])
      + `<h3 style="margin:12px 0 4px;font-size:1em">${esc(T('sCor'))}</h3><ul class="small" style="margin:0;padding-left:18px"><li>${esc(T('cor1', {r:f1(rMin)}))}</li><li>${esc(T('cor2', {r:f1(rProp)}))}</li><li>${esc(T('cor3', {r:f1(rPl)}))}</li></ul><p class="small muted" style="margin:4px 0 0">${esc(T('corNote'))}</p>`));

    // discovery curve + pareto
    const seen = new Set(), curve = [{x:0, y:0}]; rows.forEach((r, i) => { if(!seen.has(r.trove)){ seen.add(r.trove); } if(i % 10 === 0 || i === rows.length - 1) curve.push({x:i + 1, y:seen.size}); });
    const cnt = new Map(); rows.forEach(r => cnt.set(r.trove, (cnt.get(r.trove) || 0) + r.q));
    const rank = [...cnt.values()].sort((a, b) => b - a), tq = rank.reduce((a, b) => a + b, 0); let acc = 0;
    const par = [{x:0, y:0}].concat(rank.map((v, i) => { acc += v; return {x:i + 1, y:acc / tq * 100}; }));
    const dayMarks = []; days.forEach(d => { const i = rows.findIndex(r => r.day === d); if(i > 0) dayMarks.push({x:i, label:dayLabel(d)}); });
    out.push(card(T('sDisc'), T('sDiscN'), grid([
      `<div>${line(curve, {xlab:T('axN'), ylab:T('axT'), marks:dayMarks, label:T('sDisc'), h:210})}</div>`,
      `<div><div class="small muted" style="margin:0 0 2px">${esc(T('sPar'))} · ${esc(T('sParN'))}</div>${line(par, {xlab:T('axRank'), ylab:T('axShare') + ' %', ymax:100, xfmt:x => Math.round(x), c:'#fc7d0b', label:T('sPar'), h:210})}</div>`])));

    // cities
    const byCity = new Map(); rows.forEach(r => { if(!byCity.has(r.city)) byCity.set(r.city, []); byCity.get(r.city).push(r); });
    const cityRows = [...byCity.entries()].map(([c, rs]) => { const ss = P.sessions.map(s => s.rows.filter(r => r.city === c)).filter(a => a.length), min = ss.reduce((a, x) => a + Math.max((x[x.length - 1].ms - x[0].ms) / 6e4, 1), 0); return {c, n:rs.length, props:new Set(rs.map(r => r.pi)).size, types:new Set(rs.map(r => r.trove)).size, plant:rs.filter(r => r.kind === 'plant').length / rs.length, min, rate:rs.length / min}; }).sort((a, b) => b.n - a.n);
    const mxc = Math.max(...cityRows.map(x => x.n));
    out.push(card(T('sCity'), '', `<div class="tablewrap"><table><thead><tr><th>${esc(T('cCity'))}</th><th class="n">${esc(T('cFinds'))}</th><th class="n">${esc(T('cProps'))}</th><th class="n">${esc(T('cPer'))}</th><th class="n">${esc(T('cTypes'))}</th><th class="n">${esc(T('cPlant'))}</th><th class="n">${esc(T('cMin'))}</th><th class="n">${esc(T('cRate'))}</th></tr></thead><tbody>${cityRows.map(x => `<tr><td><b>${esc(x.c)}</b><div style="height:5px;border-radius:3px;background:var(--accent);width:${(x.n / mxc * 100).toFixed(0)}%;margin-top:3px"></div></td><td class="n">${n0(x.n)}</td><td class="n">${x.props}</td><td class="n">${f1(x.n / x.props)}</td><td class="n">${x.types}</td><td class="n">${pct(x.plant)}</td><td class="n">${Math.round(x.min)}</td><td class="n">${f1(x.rate)}</td></tr>`).join('')}</tbody></table></div>`));

    // categories
    const catOf = n => cat(n) || 'junk', cats = Object.keys(CAT);
    const catQ = {}; rows.forEach(r => { const c = catOf(r.trove); catQ[c] = (catQ[c] || 0) + r.q; });
    const tm = []; cnt.forEach((v, n) => tm.push({label:n, v, c:CAT[catOf(n)] || '#8a8a8a'}));
    const cityMix = cityRows.slice(0, 8).map(x => ({label:x.c, parts:cats.map(c => byCity.get(x.c).filter(r => catOf(r.trove) === c).reduce((a, r) => a + r.q, 0))}));
    const cityMixPct = cityMix.map(m => { const s = m.parts.reduce((a, b) => a + b, 0) || 1; return {label:m.label, parts:m.parts.map(v => v / s * 100)}; });
    out.push(card(T('sCat'), T('sCatN'), treemap(tm.slice(0, 80)) + legend(cats.map(c => ({c:CAT[c], l:c + ' ' + n0(catQ[c] || 0)})))
      + `<h3 style="margin:12px 0 4px;font-size:1em">${esc(T('sCatCity'))}</h3>` + columns(cityMixPct, cats.map(c => CAT[c]), {names:cats, total:false, label:T('sCatCity')})));

    // levels
    if(ctx.bal){
      const bal = new Map(ctx.bal.map(i => [i[0], i])), pts = [], lvc = [0, 0, 0, 0];
      cnt.forEach((v, n) => { const it = bal.get(n); if(!it) return; const l = Math.min(it[3], 3); lvc[l]++; pts.push({x:v, y:it[2], c:LV[l], r:4, title:`${n}: ${v} / ${it[2]} · ${l}`}); });
      out.push(card(T('sLvl'), T('sLvlN'), scatter(pts, {xlab:T('axFinds'), ylab:T('axHold'), diag:true, label:T('sLvl')}) + legend(LV.map((c, i) => ({c, l:i ? T('lv', {n:i}) : T('lvNone')})))
        + `<h3 style="margin:12px 0 4px;font-size:1em">${esc(T('sLvlBar'))}</h3>` + hbars(lvc.map((v, i) => ({label:i ? T('lv', {n:i}) : T('lvNone'), v, c:LV[i]})), {l:80, label:T('sLvlBar')})));
    }

    // sources
    const bySrc = new Map(); rows.forEach(r => { const e = bySrc.get(r.src) || {n:0, t:new Set(), kind:r.kind}; e.n++; e.t.add(r.trove); bySrc.set(r.src, e); });
    const srcRows = [...bySrc.entries()].sort((a, b) => b[1].n - a[1].n).slice(0, 18);
    out.push(card(T('sSrc'), T('sSrcN'), hbars(srcRows.map(([s, e]) => ({label:s, v:e.n, c:KIND[e.kind]})), {l:190, label:T('sSrc')}) + legend(kinds.map(k => ({c:KIND[k], l:kindName[k]})))
      + `<div class="tablewrap" style="margin-top:8px"><table><thead><tr><th>${esc(T('cSrc'))}</th><th class="n">${esc(T('cDiff'))}</th></tr></thead><tbody>${srcRows.map(([s, e]) => `<tr><td>${esc(s)}</td><td class="n">${e.t.size}</td></tr>`).join('')}</tbody></table></div>`));

    // cooldown & dust (not balloons)
    const rep = rows.filter(r => r.gap != null && r.kind !== 'balloon'), bins = new Array(37).fill(0), dust = new Array(37).fill(0).map(() => [0, 0]);
    rep.forEach(r => { const b = Math.min(Math.floor(r.gap / 5), 36); bins[b]++; dust[b][0] += r.trove === 'Trove Dust' ? 1 : 0; dust[b][1]++; });
    const hist = bins.map((v, i) => ({label:i * 5 + (i === 36 ? '+' : ''), parts:[v]}));
    out.push(card(T('sGap'), T('sGapN'), columns(hist, ['#1170aa'], {h:200, total:false, label:T('sGap')}) + `<p class="small muted" style="margin:2px 0 0">${esc(T('axGap'))} →</p>`));
    const dp = dust.map(([d, n], i) => ({x:i * 5, y:n >= 5 ? d / n * 100 : 0}));
    out.push(card(T('sDust'), T('sDustN'), line(dp, {xlab:T('axGap'), ylab:T('axDust') + ' %', ymax:100, c:'#c85200', xfmt:x => Math.round(x), label:T('sDust'), h:200})));

    // balloons
    const B = rows.filter(r => r.kind === 'balloon');
    if(B.length){
      const models = [...new Set(B.map(r => (r.src.match(/\((\w+)\)/) || [])[1]))].filter(Boolean), mname = m => T('model')[m] || m;
      const bd = [...new Set(B.map(r => r.day))].sort(), balloons = new Set(B.map(r => r.inst)), dustN = B.filter(r => r.trove === 'Trove Dust').length;
      const revisit = B.filter(r => r.gap != null).length;
      out.push(card(T('sBal'), T('sBalN'), `<div style="display:flex;flex-wrap:wrap;gap:8px">${kpi(n0(B.length), T('bF'))}${kpi(n0(balloons.size), T('bB'))}${kpi(bd.length, T('bD'))}${kpi(pct(dustN / B.length), T('bDust'))}${kpi(n0(revisit), T('bRep'))}</div>`
        + `<h3 style="margin:12px 0 4px;font-size:1em">${esc(T('sBalDay'))}</h3>` + columns(bd.map(d => ({label:dayLabel(d), parts:models.map(m => B.filter(r => r.day === d && r.src.includes('(' + m + ')')).length)})), MODEL, {names:models.map(mname), label:T('sBalDay')}) + legend(models.map((m, i) => ({c:MODEL[i], l:mname(m)})))
        + grid([`<div><h3 style="margin:12px 0 4px;font-size:1em">${esc(T('sBalTop'))}</h3>${hbars(Object.entries(B.reduce((a, r) => (a[r.trove] = (a[r.trove] || 0) + r.q, a), {})).sort((a, b) => b[1] - a[1]).slice(0, 12).map(([n, v]) => ({label:n, v, c:CAT[catOf(n)] || '#8a8a8a'})), {l:110, label:T('sBalTop')})}</div>`,
          `<div><h3 style="margin:12px 0 4px;font-size:1em">${esc(T('sBalTable'))}</h3><div class="tablewrap"><table><thead><tr><th>${esc(T('cDay'))}</th><th class="n">${esc(T('cFinds'))}</th><th class="n">${esc(T('cBal'))}</th><th class="n">${esc(T('cRep'))}</th><th class="n">${esc(T('cDustN'))}</th><th class="n">${esc(T('cQty'))}</th></tr></thead><tbody>${bd.map(d => { const x = B.filter(r => r.day === d); return `<tr><td>${esc(dayLabel(d))}</td><td class="n">${x.length}</td><td class="n">${new Set(x.map(r => r.inst)).size}</td><td class="n">${x.filter(r => r.gap != null).length}</td><td class="n">${x.filter(r => r.trove === 'Trove Dust').length}</td><td class="n">${n0(x.reduce((a, r) => a + r.q, 0))}</td></tr>`; }).join('')}</tbody></table></div></div>`])
        + (() => { const div = k => { const x = rows.filter(r => r.kind === k); return x.length ? [new Set(x.map(r => r.trove)).size / x.length * 100, x.filter(r => r.trove === 'Trove Dust').length / x.length * 100] : [0, 0]; }; const a = div('balloon'), b2 = div('structure'), c = div('plant'); return `<p class="small" style="margin:10px 0 0">${esc(T('bVs', {a:f1(a[0]), b:f1(b2[0]), c:f1(c[0]), d:f1(a[1]), e:f1(b2[1]), f:f1(c[1])}))}</p>`; })()));
    }
    return out.join('');
  }
  return {html};
})();
