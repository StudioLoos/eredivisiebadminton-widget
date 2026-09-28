// Service worker Eredivisie Badminton app: app werkt ook bij slecht bereik, data altijd zo vers mogelijk.
importScripts("https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.sw.js");
const C = 'edb-v4';
const SHELL = ['app.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(C).then(c => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k))))); self.clients.claim(); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  const fresh = u.pathname.endsWith('data.json') || u.pathname.endsWith('app.html') || u.pathname.endsWith('/');
  if (fresh) { // netwerk eerst, cache als terugval
    e.respondWith(fetch(e.request, {cache: 'no-store'}).then(r => { const k = r.clone(); caches.open(C).then(c => c.put(e.request.url.split('?')[0], k)); return r; })
      .catch(() => caches.match(e.request.url.split('?')[0])));
  } else { // foto's en iconen: cache eerst
    e.respondWith(caches.match(e.request).then(m => m || fetch(e.request).then(r => { const k = r.clone(); caches.open(C).then(c => c.put(e.request, k)); return r; })));
  }
});
