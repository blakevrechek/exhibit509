// Exhibit service worker — minimal app-shell caching for offline + fast repeat visits.
// Strategy: stale-while-revalidate for the static shell (index.html, methodology.html,
// about.html, terms.html, manifest, sitemap, self-hosted Leaflet + fonts), network-first
// for everything else (Carto map tiles) so tiles stay fresh.
const CACHE = 'exhibit-v1.18.2';
// Relative URLs resolve against the SW script location (the deploy root, e.g.
// /Exhibit/sw.js → entries cache as /Exhibit/index.html etc.). Hardcoding absolute
// paths like '/index.html' would resolve to the host root and fail on GH Pages
// project deploys (/Exhibit/...). Relative-from-scope is the portable form.
const SHELL = ['./', './index.html', './data/exhibit-data.js', './fonts/fonts.css', './vendor/leaflet/leaflet.js', './vendor/leaflet/leaflet.css', './methodology.html', './about.html', './terms.html', './contact.html', './manifest.json', './sitemap.xml', './404.html'];

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
  // Stale-while-revalidate for same-origin shell.
  if (url.origin === location.origin) {
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
    return;
  }
  // Cross-origin (CDN tiles, fonts, Leaflet): network-first, cache as fallback.
  e.respondWith(
    fetch(req).then(resp => {
      if (resp && resp.status === 200 && (url.host.includes('basemaps.cartocdn') || url.host.includes('cdnjs') || url.host.includes('fonts.googleapis') || url.host.includes('fonts.gstatic'))) {
        const clone = resp.clone();
        caches.open(CACHE).then(c => c.put(req, clone));
      }
      return resp;
    }).catch(() => caches.match(req))
  );
});
