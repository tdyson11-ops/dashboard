// Ask the browser to treat this app's storage as durable so it is not
// silently evicted (iOS/Safari can clear a web-app's localStorage under
// storage pressure or after a period of disuse). No-op where unsupported.
(function () {
  try {
    if (navigator.storage && navigator.storage.persist && navigator.storage.persisted) {
      navigator.storage.persisted().then(function (already) {
        if (!already) navigator.storage.persist();
      }).catch(function () {});
    }
  } catch (e) {}
})();
