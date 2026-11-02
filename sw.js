// Network-first service worker: always serves the latest version when online,
// falls back to the last cached copy when offline. Nothing is served stale
// while a connection exists, so deploys still appear within a minute.
var CACHE = 'td-dashboard-v2';

self.addEventListener('install', function (e) {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  // Drop caches from older versions of this worker.
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  // Only handle our own files. Leave cross-origin requests (Firebase auth /
  // Firestore streams, Google Fonts) untouched so sync works normally.
  if (new URL(e.request.url).origin !== self.location.origin) return;
  // cache: 'no-cache' makes the browser check with GitHub every time instead
  // of trusting its own copy for up to 10 minutes (GitHub Pages' max-age), so a
  // deploy shows up on the next open. Plain same-origin GETs only, so asking
  // by URL is equivalent to the original request.
  e.respondWith(
    fetch(e.request.url, { cache: 'no-cache', credentials: 'same-origin' })
      .then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      })
      .catch(function () {
        return caches.match(e.request);
      })
  );
});
