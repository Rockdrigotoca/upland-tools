// Shared header, settings (language + Cunk mode), footer and translations for every tool.
(function(){
  "use strict";
  const store = {
    get(k, d){ try{ const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); }catch{ return d; } },
    set(k, v){ try{ localStorage.setItem(k, JSON.stringify(v)); }catch{} }
  };

  const SITE_T = {
    en:{
      siteName:'Rockdrigo’s Upland Tools', by:'by Rockdrigo', settings:'Settings', language:'Language', tone:'Tone',
      cunkOn:'Cunk mode', cunkOff:'Plain', textSize:'Text size', sizeNames:'Normal|Large|Larger|Largest', cunkDesc:'Deadpan documentary-style labels. Turn it off for plain labels.',
      home:'← All tools', footNote:'Uses Upland’s public game data. Not affiliated with Upland.'
    },
    es:{
      siteName:'Herramientas de Upland de Rockdrigo', by:'por Rockdrigo', settings:'Ajustes', language:'Idioma', tone:'Tono',
      cunkOn:'Modo Cunk', cunkOff:'Normal', textSize:'Tamaño de letra', sizeNames:'Normal|Grande|Más grande|Muy grande', cunkDesc:'Textos en tono de documental absurdo. Apágalo para textos normales.',
      home:'← Todas las herramientas', footNote:'Usa datos públicos del juego Upland. Sin relación oficial con Upland.'
    },
    en_cunk:{
      textSize:'Size of the words', sizeNames:'Normal|Big|Bigger|Enormous',
      cunkDesc:'Everything is currently narrated by someone who once read about houses. Switch it off for plain, sensible labels.',
      home:'← Back to all the tools', footNote:'Uses Upland’s public game data. Not affiliated with Upland, or with reality.'
    },
    es_cunk:{
      textSize:'Tamaño de las palabras', sizeNames:'Normal|Grande|Más grande|Enorme',
      cunkDesc:'Todo lo narra ahora alguien que una vez leyó sobre casas. Apágalo para textos normales y sensatos.',
      home:'← Volver a todas las herramientas', footNote:'Usa datos públicos del juego Upland. Sin relación con Upland, ni con la realidad.'
    }
  };

  let lang = store.get('rut:lang', (navigator.language || 'en').toLowerCase().startsWith('es') ? 'es' : 'en');
  let cunk = store.get('rut:cunk', true);   // Cunk mode is on unless the visitor turns it off
  const SIZES = [1, 1.15, 1.3, 1.5];
  let textScale = store.get('rut:textScale', 1);
  if(!SIZES.includes(textScale)) textScale = 1;
  const applyScale = () => document.documentElement.style.setProperty('--text-scale', String(textScale));
  applyScale();
  const dicts = [SITE_T];
  let onChange = () => {};

  function t(key, vars){
    const order = (cunk ? [lang + '_cunk', lang, 'en_cunk', 'en'] : [lang, 'en']);
    let s;
    outer: for(const v of order) for(const d of dicts){ if(d[v] && d[v][key] != null){ s = d[v][key]; break outer; } }
    if(s == null) s = key;
    if(vars) for(const k in vars) s = s.replaceAll('{' + k + '}', vars[k]);
    return s;
  }
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function renderChrome(){
    const head = document.getElementById('site-header');
    if(head){
      const isHome = head.dataset.home === 'true';
      head.className = 'site-head';
      head.innerHTML = `<div>
          ${isHome ? '' : `<a class="home" href="../">${esc(t('home'))}</a>`}
          <h1>${esc(t('title'))}<small>${esc(t('subtitle'))}</small></h1>
        </div>
        <details class="settings" id="site-settings">
          <summary>⚙ ${esc(t('settings'))} <span class="tag">${esc(lang.toUpperCase())}${cunk ? ' · Cunk' : ''}${textScale > 1 ? ' · A+' : ''}</span></summary>
          <div class="panel">
            <div class="grp"><div class="lbl">${esc(t('language'))}</div>
              <div class="seg"><button type="button" data-lang="en" class="${lang === 'en' ? 'on' : ''}">English</button><button type="button" data-lang="es" class="${lang === 'es' ? 'on' : ''}">Español</button></div></div>
            <div class="grp"><div class="lbl">${esc(t('textSize'))}</div>
              <div class="seg sizes">${SIZES.map((z, i) => `<button type="button" data-size="${z}" class="${z === textScale ? 'on' : ''}" aria-label="${esc(t('sizeNames').split('|')[i])}" title="${esc(t('sizeNames').split('|')[i])}">A</button>`).join('')}</div></div>
            <div class="grp"><div class="lbl">${esc(t('tone'))}</div>
              <label class="switch"><input type="checkbox" id="cunk-toggle" ${cunk ? 'checked' : ''}><span class="track"></span>
                <span class="txt"><b>${esc(cunk ? t('cunkOn') : t('cunkOff'))}</b><span>${esc(t('cunkDesc'))}</span></span></label></div>
          </div>
        </details>`;
    }
    const foot = document.getElementById('site-footer');
    if(foot){
      foot.className = 'site-foot';
      const extra = t('foot');
      foot.innerHTML = `<div><a href="${foot.dataset.home === 'true' ? './' : '../'}">${esc(t('siteName'))}</a> · ${esc(t('by'))}</div>
        <div>${esc(t('footNote'))}</div>${extra !== 'foot' ? `<div>${esc(extra)}</div>` : ''}`;
    }
    document.documentElement.lang = lang;
    document.title = t('title');
    document.querySelectorAll('[data-i]').forEach(el => el.textContent = t(el.dataset.i));
    document.querySelectorAll('[data-i-ph]').forEach(el => el.placeholder = t(el.dataset.iPh));
  }

  function refresh(keepOpen){
    const wasOpen = keepOpen && document.getElementById('site-settings') && document.getElementById('site-settings').open;
    renderChrome();
    if(wasOpen) document.getElementById('site-settings').open = true;
    onChange();
  }

  document.addEventListener('click', e => {
    const b = e.target.closest('#site-settings [data-lang]');
    if(b){ lang = b.dataset.lang; store.set('rut:lang', lang); refresh(true); return; }
    const z = e.target.closest('#site-settings [data-size]');
    if(z){ textScale = Number(z.dataset.size); store.set('rut:textScale', textScale); applyScale(); refresh(true); return; }
    const s = document.getElementById('site-settings');
    if(s && s.open && !s.contains(e.target)) s.open = false;
  });
  document.addEventListener('change', e => {
    if(e.target.id === 'cunk-toggle'){ cunk = e.target.checked; store.set('rut:cunk', cunk); refresh(true); }
  });

  window.Site = {
    store, t, esc,
    lang: () => lang,
    locale: () => lang === 'es' ? 'es-MX' : 'en-US',
    cunk: () => cunk,
    register(T){ dicts.unshift(T); },
    mount(opts = {}){ onChange = opts.onChange || onChange; refresh(false); }
  };
})();
