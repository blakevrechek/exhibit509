// Exhibit service worker — minimal app-shell caching for offline + fast repeat visits.
// Strategy:
//   • HTML navigations  → NETWORK-FIRST (always get the freshest page; fall back to
//     cache only when offline). This is what stops the "refresh shows a gray/stale
//     map" bug: a plain reload no longer gets handed an old cached shell.
//   • Other same-origin assets (data.js, fonts, self-hosted Leaflet, manifest) →
//     stale-while-revalidate; they're versioned/stable so instant-from-cache is fine.
//   • Cross-origin (Carto tiles, fonts) → network-first, cache as offline fallback.
const CACHE = 'exhibit-v1.93.7';
// Relative URLs resolve against the SW script location (the deploy root, e.g.
// /Exhibit/sw.js → entries cache as /Exhibit/index.html etc.). Hardcoding absolute
// paths like '/index.html' would resolve to the host root and fail on GH Pages
// project deploys (/Exhibit/...). Relative-from-scope is the portable form.
const SHELL = ['./', './index.html', './data/exhibit-data.js?v=1.93.7', './fonts/fonts.css', './vendor/leaflet/leaflet.js', './vendor/leaflet/leaflet.css', './methodology.html', './about.html', './terms.html', './contact.html', './manifest.json', './sitemap.xml', './404.html'];

self.addEventListener('install', e => {
  // Pre-cache the app shell, but don't fail install if one resource 404s
  // (e.g. about.html might not exist yet in a fresh deploy).
  e.waitUntil(
    caches.open(CACHE).then(c => Promise.all(
      SHELL.map(u => c.add(u).catch(()=>{}))
    )).then(()=>self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== CACHE).map(k => caches.delete(k))
    )).then(()=>self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // CROSS-ORIGIN (Carto map tiles, any CDN): do NOT intercept. Leaflet fetches
  // tiles no-cors → opaque responses; routing them through the SW broke with
  // NS_ERROR_INTERCEPTION_FAILED in Firefox and left the basemap gray. Let the
  // browser fetch them natively.
  if (url.origin !== location.origin) return;
  // HTML navigations: NETWORK-FIRST so a refresh always gets the live page.
  // (mode==='navigate' covers reloads/links; also catch explicit .html requests.)
  const isHTML = req.mode === 'navigate'
    || /\.html?$/.test(url.pathname)
    || url.pathname.endsWith('/');
  if (isHTML) {
    e.respondWith(
      fetch(req).then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(req, clone));
        }
        return resp;
      }).catch(() => caches.match(req).then(hit => hit || caches.match('./index.html')))
    );
    return;
  }
  // Other same-origin assets: stale-while-revalidate.
  e.respondWith(
    caches.match(req).then(hit => {
      const fetchAndUpdate = fetch(req).then(resp => {
        if (resp && resp.status === 200) {
          const clone = resp.clone();
          caches.open(CACHE).then(c => c.put(req, clone));
        }
        return resp;
      }).catch(() => hit);
      return hit || fetchAndUpdate;
    })
  );
});
