// Network-first service worker: always serves the latest version when online,
// falls back to the last cached copy when offline. Nothing is served stale
// while a connection exists, so deploys still appear within a minute.
var CACHE = 'td-dashboard-v1';

self.addEventListener('install', function (e) {
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  // Only handle our own files. Leave cross-origin requests (Firebase auth /
  // Firestore streams, Google Fonts) untouched so sync works normally.
  if (new URL(e.request.url).origin !== self.location.origin) return;
  e.respondWith(
    fetch(e.request)
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
