// Network-first service worker: always serves the latest version when online,
// falls back to the last cached copy when offline. Nothing is served stale
// while a connection exists, so deploys still appear within a minute.
var CACHE = 'td-dashboard-v2';

// The business card must open with no signal at all, so its files are stored
// on install and served from the phone first (refreshed in the background).
var CARD_FILES = ['card.html', 'manifest-card.json', 'cicon-180.png', 'cicon-192.png', 'cicon-512.png'];

self.addEventListener('install', function (e) {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(CARD_FILES); }).catch(function () {}));
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
  var url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return;
  // Card: cache-first so it opens instantly offline or on poor signal.
  if (CARD_FILES.some(function (f) { return url.pathname.endsWith('/' + f); })) {
    e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(function (hit) {
      var net = fetch(e.request.url, { cache: 'no-cache', credentials: 'same-origin' }).then(function (res) {
        if (res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(e.request, copy); }); }
        return res;
      });
      if (hit) { net.catch(function () {}); return hit; }
      return net;
    }));
    return;
  }
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
