// Ornament prices collected every 12 hours into data/ (see tools/collect_prices.py), shared by the tools.
(function(){
  "use strict";
  const norm = s => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();

  // Usual UPX sale price for a design: last 30 days, else 90 days, else all history.
  function typical(s){
    if(!s) return null;
    for(const [k, p] of [['u30', 'p30'], ['u90', 'p90'], ['uAll', 'pAll']]) if(s[k] && s[k][0]) return {price:s[k][1], n:s[k][0], p};
    return null;
  }

  async function load(base = '../data/'){
    const state = await Upland.getJSON(base + 'state.json?t=' + Date.now());
    const v = encodeURIComponent(state.updatedAt || '');
    const get = f => Upland.getJSON(`${base}${f}?v=${v}`);
    const [designs, listings, shops, summary] = await Promise.all([get('designs.json'), get('listings.json'), get('shops.json'), get('summary.json')]);
    // Listings grouped by season and structure type, cheapest first.
    const bySlot = new Map();
    for(const r of listings.rows){
      const d = designs[r.key];
      if(!d || !d.s) continue;
      const k = d.s + '|' + norm(d.ty);
      (bySlot.get(k) || bySlot.set(k, []).get(k)).push(r);
    }
    for(const arr of bySlot.values()) arr.sort((a, b) => a.total - b.total);
    return {
      state, designs, shops, summary, listings: listings.rows,
      key: (name, type) => `${name} | ${type}`,
      design: key => designs[key] || null,
      typical: key => typical(summary[key]),
      shop: id => shops[String(id)] || null,
      // Cheapest listings for a season and structure type, leaving out the given seller.
      forSlot(season, type, exclude){
        const ex = norm(exclude);
        return (bySlot.get(season + '|' + norm(type)) || []).filter(r => !ex || norm(r.seller) !== ex);
      }
    };
  }

  window.Prices = {load, typical, norm};
})();
