// Reading Upland's public game data. These routes are undocumented and may change without notice.
(function(){
  "use strict";
  const API = 'https://api.prod.upland.me';
  const IMG = 'https://static.upland.me/';

  async function getJSON(url, opts){
    const r = await fetch(url, {headers:{Accept:'application/json'}, ...opts});
    if(!r.ok){ const e = new Error(String(r.status)); e.status = r.status; throw e; }
    return r.json();
  }
  // Run fn over items with at most n requests in flight; failed items come back as null.
  async function pool(items, n, fn){
    const out = new Array(items.length); let i = 0;
    await Promise.all(Array.from({length:Math.min(n, items.length)}, async () => {
      while(i < items.length){ const j = i++; try{ out[j] = await fn(items[j]); }catch(e){ out[j] = null; } }
    }));
    return out;
  }
  const u = encodeURIComponent;

  window.Upland = {
    API, IMG, getJSON, pool,
    ornaments: user => getJSON(`${API}/nft/assets/v2/decorations/${u(user)}`),
    structures: user => getJSON(`${API}/nft/assets/structures/${u(user)}`),
    property: id => getJSON(`${API}/api/properties/${id}`),
    decorationPreview: id => getJSON(`${API}/business/decorations/${id}/preview`),
    shop: id => getJSON(`${API}/metaventures/secondary-shop/${id}`),
    shopItems: id => getJSON(`${API}/metaventures/secondary-shop/${id}/items`, {method:'POST', headers:{Accept:'application/json','Content-Type':'application/json'}, body:'{}'}),
    image: path => path ? IMG + encodeURI(path) : ''
  };
})();
