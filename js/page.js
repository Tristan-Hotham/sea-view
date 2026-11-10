/* Can you see the sea? Every 1 km square of the UK on a plain MapLibre base map (OpenFreeMap Positron), coloured by the
 * distance to the nearest sea in view or by the share of the horizon that is sea, for four eye heights; tap a square for its
 * numbers, search any settlement for its own result, and see the named viewpoints used to check the model.
 * Dr Tristan Hotham, Independent researcher, 2026. MIT licence. */
(function () {
  'use strict';
  const qs = new URLSearchParams(location.search);
  const STYLE = 'https://tiles.openfreemap.org/styles/positron';
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const norm = s => String(s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const small = matchMedia('(max-width:800px)').matches;
  const EYES = ['1.7', '5', '15', '50'];
  const EYEL = { '1.7': 'Standing, 1.7 m', '5': 'Upstairs window, 5 m', '15': 'Fifth floor, 15 m', '50': 'Tall tower, 50 m' };
  let map = null, site = null, places = null, grids = null, eye = EYES.includes(qs.get('eye')) ? qs.get('eye') : '1.7', measure = qs.get('m') === 'hz' ? 'hz' : 'near';
  document.getElementById('theme').addEventListener('click', () => { const r = document.documentElement, d = r.dataset.theme ? r.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; r.dataset.theme = d ? 'light' : 'dark'; });
  const ct = document.getElementById('cartouche'); const fold = f => ct.classList.toggle('folded', f);
  if (small) fold(true);
  document.getElementById('ctToggle').addEventListener('click', () => fold(!ct.classList.contains('folded')));
  document.getElementById('ctFold').addEventListener('click', () => fold(true));
  const km = v => v == null ? 'none within 50 km' : (v < 1 ? 'under 1 km' : `${v < 10 ? v.toFixed(1) : Math.round(v)} km`);

  // ---- lookup grids: decoded once, on the first tap ----
  function loadImg(src) { return new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = src; }); }
  async function getGrids() {
    if (grids) return grids;
    const ims = await Promise.all(['data/grid_a.png', 'data/grid_b.png', 'data/grid_c.png'].map(loadImg));
    grids = ims.map(im => { const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(im, 0, 0); return x.getImageData(0, 0, im.width, im.height).data; });
    return grids;
  }
  function px(lon, lat) {
    const g = site.grid, n = 256 * Math.pow(2, g.z), r = lat * Math.PI / 180;
    const X = (lon + 180) / 360 * n, Y = (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * n;
    const i = Math.floor((X - g.x0) / (g.x1 - g.x0) * g.w), j = Math.floor((Y - g.y0) / (g.y1 - g.y0) * g.h);
    return (i < 0 || j < 0 || i >= g.w || j >= g.h) ? -1 : (j * g.w + i) * 4;
  }
  const dn = v => v === 255 ? null : v / 5;
  const dh = v => v === 255 ? null : v / 2;
  async function squareAt(lon, lat) {
    const G = await getGrids(); const k = px(lon, lat);
    if (k < 0 || G[0][k + 1] === 255) return null;
    return { ground: G[0][k + 2] * 6, near: [dn(G[0][k]), dn(G[1][k]), dn(G[1][k + 1]), dn(G[1][k + 2])], hz: [dh(G[0][k + 1]), dh(G[2][k]), dh(G[2][k + 1]), dh(G[2][k + 2])] };
  }
  function nearestPlace(lon, lat) {
    if (!places) return null; let best = null, bd = 1e9; const c = Math.cos(lat * Math.PI / 180);
    for (const p of places) { if (p[4] < 500) continue; const d = Math.hypot((p[2] - lon) * c, p[3] - lat); if (d < bd) { bd = d; best = p; } }
    return best ? [best, bd * 111] : null;
  }
  function table(near, hz) {
    return '<table>' + EYES.map((e, i) => `<tr${e === eye ? ' style="font-weight:600"' : ''}><td>${e} m</td><td>${near[i] == null ? 'no sea' : 'sea ' + km(near[i])}</td><td>${hz[i] ? hz[i].toFixed(hz[i] < 10 ? 1 : 0) + '% of horizon' : ''}</td></tr>`).join('') + '</table>';
  }
  async function popSquare(lngLat) {
    const s = await squareAt(lngLat.lng, lngLat.lat);
    let h;
    if (!s) h = '<b class="t">Not a mapped square</b><p class="nt">Only the 1 km squares of the United Kingdom are computed. Ireland and the Isle of Man are terrain only.</p>';
    else {
      const i = EYES.indexOf(eye), np = nearestPlace(lngLat.lng, lngLat.lat);
      h = `<b class="t">${s.near[i] == null ? 'No sea in view' : 'Sea in view, ' + km(s.near[i]) + ' away'}</b>` +
        `<div>Eyes ${eye} m above the ground (${s.ground} m above sea level, roughly)${np ? `, near ${esc(np[0][0])}` : ''}.</div>` + table(s.near, s.hz) +
        `<p class="nt">The 1 km square under your tap, bare terrain with no buildings or trees. "Horizon" is the share of 360 sight lines that reach visible sea within 50 km.</p>`;
    }
    new maplibregl.Popup({ maxWidth: '320px' }).setLngLat(lngLat).setHTML(h).addTo(map);
  }
  function popPlace(p) {
    const h = `<b class="t">${esc(p[0])}</b><div>${esc(p[1])}${p[4] ? ` · population ${p[4].toLocaleString('en-GB')} (Wikidata)` : ''}</div>` +
      `<div>${p[5][EYES.indexOf(eye)] == null ? 'No sea in view from the settlement point' : 'Sea in view from the settlement point, ' + km(p[5][EYES.indexOf(eye)]) + ' away'} (eyes ${eye} m).</div>` +
      table(p[5], p[6].map(v => v / 3.6)) + '<p class="nt">Computed at the Wikidata point for the place; other streets may differ.</p>';
    new maplibregl.Popup({ maxWidth: '320px' }).setLngLat([p[2], p[3]]).setHTML(h).addTo(map);
  }

  // ---- overlay, key and controls ----
  const ovUrl = () => `img/ov_${measure}_${eye}.png`;
  function refresh() {
    clearTimeout(refresh.t);
    refresh.t = setTimeout(() => { const u = ovUrl(); if (map && map.getSource('ov') && refresh.u !== u) { refresh.u = u; map.getSource('ov').updateImage({ url: u, coordinates: site.bounds }); } }, 180);
    document.querySelectorAll('.chip[data-m]').forEach(x => x.setAttribute('aria-pressed', x.dataset.m === measure));
    document.getElementById('keyNear').hidden = measure !== 'near'; document.getElementById('keyHz').hidden = measure !== 'hz';
    document.getElementById('eyeTxt').textContent = EYEL[eye];
    document.getElementById('eyePc').textContent = `${Math.round(site.eye_pc[eye])}% of UK land sees the sea`;
    document.getElementById('eye').value = EYES.indexOf(eye);
    const u = new URL(location.href); u.searchParams.set('eye', eye); u.searchParams.set('m', measure); history.replaceState(null, '', u);
  }
  document.querySelectorAll('.chip[data-m]').forEach(b => b.addEventListener('click', () => { measure = b.dataset.m; refresh(); }));
  document.getElementById('eye').addEventListener('input', e => { eye = EYES[+e.target.value]; refresh(); });
  document.querySelectorAll('.tl .ch button').forEach(b => b.addEventListener('click', () => { eye = b.dataset.eye; refresh(); }));
  const lp = document.getElementById('lp'), lb = document.getElementById('lyrBtn');
  lb.addEventListener('click', () => { const o = !lp.classList.contains('open'); lp.classList.toggle('open', o); lb.setAttribute('aria-expanded', o); });
  function vis(ids, on) { ids.forEach(id => { if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'); }); }

  // ---- search ----
  const q = document.getElementById('q'), sug = document.getElementById('sug');
  let hits = [], cur = -1;
  function show() { sug.innerHTML = hits.map((p, i) => `<li role="option" data-i="${i}" aria-selected="${i === cur}">${esc(p[0])} <span>${esc(p[1])}</span></li>`).join(''); sug.style.display = hits.length ? 'block' : 'none'; }
  function pick(p) { sug.style.display = 'none'; q.value = p[0]; map.flyTo({ center: [p[2], p[3]], zoom: Math.max(map.getZoom(), 10.5) }); map.once('moveend', () => popPlace(p)); }
  q.addEventListener('input', () => {
    const t = norm(q.value.trim()); cur = -1;
    if (t.length < 2 || !places) { hits = []; show(); return; }
    const a = [], b = [];
    for (const p of places) { const n = norm(p[0]); if (n.startsWith(t)) a.push(p); else if (n.includes(t)) b.push(p); if (a.length > 12) break; }
    hits = a.concat(b).slice(0, 12); show();
  });
  q.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { cur = Math.min(cur + 1, hits.length - 1); show(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { cur = Math.max(cur - 1, 0); show(); e.preventDefault(); }
    else if (e.key === 'Enter' && hits.length) { pick(hits[Math.max(cur, 0)]); }
    else if (e.key === 'Escape') { sug.style.display = 'none'; }
  });
  sug.addEventListener('click', e => { const li = e.target.closest('li'); if (li) pick(hits[+li.dataset.i]); });
  document.addEventListener('click', e => { if (!e.target.closest('.srch')) sug.style.display = 'none'; });
  document.querySelectorAll('[data-go]').forEach(a => a.addEventListener('click', e => {
    e.preventDefault(); const [lon, lat, z] = a.dataset.go.split(',').map(Number);
    document.getElementById('mapWrap').scrollIntoView({ behavior: 'smooth' });
    map.flyTo({ center: [lon, lat], zoom: z || 9 }); map.once('moveend', () => popSquare({ lng: lon, lat: lat }));
  }));

  // ---- the map ----
  fetch('data/site.json').then(r => r.json()).then(S => {
    site = S; refresh();
    if (!window.maplibregl) { document.getElementById('nojs').textContent = 'The map could not load (MapLibre GL JS missing).'; return; }
    map = new maplibregl.Map({ container: 'map', style: STYLE, bounds: [[-8.6, 49.8], [2.1, 59.5]], fitBoundsOptions: { padding: small ? 10 : 40 }, maxZoom: 13, minZoom: 3.5, attributionControl: false, cooperativeGestures: false });
    window.__map = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: 'Sea view: Dr Tristan Hotham (AWS Terrain Tiles; OpenStreetMap sea via OpenFreeMap)' }), 'bottom-right');
    map.on('load', () => {
      document.getElementById('nojs').remove();
      const at_ = document.querySelector('.maplibregl-ctrl-attrib'); if (at_ && small) at_.classList.remove('maplibregl-compact-show');
      const first = map.getStyle().layers.find(l => l.type === 'symbol');
      refresh.u = ovUrl(); map.addSource('ov', { type: 'image', url: refresh.u, coordinates: site.bounds });
      map.addLayer({ id: 'ov', type: 'raster', source: 'ov', paint: { 'raster-opacity': 0.82, 'raster-resampling': 'nearest', 'raster-fade-duration': 0 } }, first && first.id);
      const vf = site.views.map(v => ({ type: 'Feature', properties: v, geometry: { type: 'Point', coordinates: [v.lon, v.lat] } }));
      map.addSource('views', { type: 'geojson', data: { type: 'FeatureCollection', features: vf } });
      map.addLayer({ id: 'views', type: 'circle', source: 'views', paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 5, 10, 9], 'circle-color': ['case', ['==', ['get', 'p'], 1], '#2D6FAE', '#B3202A'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } });
      map.addLayer({ id: 'views-l', type: 'symbol', source: 'views', minzoom: 6, layout: { 'text-field': ['get', 'name'], 'text-size': 12, 'text-offset': [0, 1.1], 'text-anchor': 'top', 'text-font': ['Noto Sans Regular'] }, paint: { 'text-color': '#1D2128', 'text-halo-color': '#fff', 'text-halo-width': 1.5 } });
      const ff = site.far.map((f, i) => ({ type: 'Feature', properties: Object.assign({ rank: i + 1 }, f), geometry: { type: 'Point', coordinates: [f.lon, f.lat] } }));
      map.addSource('far', { type: 'geojson', data: { type: 'FeatureCollection', features: ff } });
      map.addLayer({ id: 'far', type: 'circle', source: 'far', paint: { 'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 6, 10, 10], 'circle-color': '#D08A1E', 'circle-stroke-color': '#1D2128', 'circle-stroke-width': 1.5 } });
      map.on('click', e => {
        const f = map.queryRenderedFeatures(e.point, { layers: ['views', 'far'] })[0];
        if (f && f.layer.id === 'views') {
          const v = f.properties;
          new maplibregl.Popup({ maxWidth: '320px' }).setLngLat(f.geometry.coordinates).setHTML(`<b class="t">${esc(v.name)}</b><div>${v.h} m. Documented: ${esc(v.doc)}</div>` +
            `<table><tr><td>At the terrain height</td><td>${v.t ? 'sea in view, ' + km(v.nt) : 'no sea within 50 km'}</td></tr><tr><td>At the published height</td><td>${v.p ? 'sea in view, ' + km(v.np) : 'no sea within 50 km'}</td></tr></table>` +
            `<p class="nt">Source: ${esc(v.src)}</p>`).addTo(map);
          return;
        }
        if (f && f.layer.id === 'far') {
          const v = f.properties;
          new maplibregl.Popup({ maxWidth: '300px' }).setLngLat(f.geometry.coordinates).setHTML(`<b class="t">${v.rank === 1 ? 'Farthest from a sea view' : 'Far from a sea view'}</b><div>${v.km} km from the nearest square that sees the sea, near ${esc(v.near)}, ${esc(v.county)}.</div>`).addTo(map);
          return;
        }
        popSquare(e.lngLat);
      });
      ['views', 'far'].forEach(id => { map.on('mouseenter', id, () => map.getCanvas().style.cursor = 'pointer'); map.on('mouseleave', id, () => map.getCanvas().style.cursor = ''); });
      const labels = map.getStyle().layers.filter(l => l.type === 'symbol' && !['views-l'].includes(l.id)).map(l => l.id);
      document.getElementById('lyO').addEventListener('change', e => vis(['ov'], e.target.checked));
      document.getElementById('lyV').addEventListener('change', e => vis(['views', 'views-l'], e.target.checked));
      document.getElementById('lyF').addEventListener('change', e => vis(['far'], e.target.checked));
      document.getElementById('lyL').addEventListener('change', e => vis(labels, e.target.checked));
      document.getElementById('opa').addEventListener('input', e => map.setPaintProperty('ov', 'raster-opacity', +e.target.value));
      fetch('data/places.json').then(r => r.json()).then(P => { places = P.places; });
      const at = qs.get('at');
      if (at) { const [lon, lat] = at.split(',').map(Number); map.jumpTo({ center: [lon, lat], zoom: 10 }); popSquare({ lng: lon, lat: lat }); }
    });
  }).catch(err => { document.getElementById('nojs').textContent = 'The map data could not load.'; console.error(err); });
})();
