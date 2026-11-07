"use strict";
const CACHE = "ascend-shell-v29";
const SHELL = ["/", "/app", "/welcome", "/tracks", "/how-it-works", "/privacy", "/auth", "/boot.css", "/style.css", "/theme.css", "/product.css", "/profile.css", "/site.css", "/site-router.js", "/site.js", "/auth.js", "/session.js", "/art.js", "/effects.css", "/feedback.css", "/feedback.js", "/rewards.css", "/rewards.js", "/accounts.js", "/workspace-ui.css", "/workspace-ui.js", "/cursor-preview.js", "/context-rail.js", "/context-rail.css", "/app.js", "/challenge-work.js", "/playground.js", "/history-library.js", "/local-labs.js", "/effects.js", "/icon.svg", "/manifest.webmanifest", "/theme.js", "/guide.json", "/fonts/InterVariable.woff2"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (!SHELL.includes(url.pathname)) return;
  // Avoid pairing a newly loaded screen with an older HTTP-cached script.
  // Normalize versioned asset URLs for the existing offline shell.
  event.respondWith(fetch(event.request, {cache: 'no-store'}).then(response => { if (response.ok) { const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(url.pathname, copy)); } return response; }).catch(() => caches.match(url.pathname)));
});
self.addEventListener("push", event => {
  let payload = {title: "Ascend", body: "One small step is enough.", url: "/app#today"};
  try { if (event.data) payload = {...payload, ...event.data.json()}; } catch {}
  event.waitUntil(self.registration.showNotification(payload.title, {body: payload.body, icon: "/icon.svg", badge: "/icon.svg", tag: "ascend-reminder", data: {url: "/app#today"}}));
});
self.addEventListener("notificationclick", event => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(clients => {
    const client = clients.find(item => new URL(item.url).origin === self.location.origin);
    return client ? client.navigate('/app#today').then(() => client.focus()) : self.clients.openWindow("/app#today");
  }));
});
