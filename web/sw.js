"use strict";
const CACHE = "ascend-shell-v6";
const SHELL = ["/", "/style.css", "/effects.css", "/app.js", "/effects.js", "/icon.svg", "/manifest.webmanifest", "/theme.js", "/guide.json", "/fonts/InterVariable.woff2"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting())));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (!SHELL.includes(url.pathname)) return;
  event.respondWith(fetch(event.request).then(response => { if (response.ok) { const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, copy)); } return response; }).catch(() => caches.match(event.request)));
});
self.addEventListener("push", event => {
  let payload = {title: "Ascend", body: "One small step is enough.", url: "/"};
  try { if (event.data) payload = {...payload, ...event.data.json()}; } catch {}
  event.waitUntil(self.registration.showNotification(payload.title, {body: payload.body, icon: "/icon.svg", badge: "/icon.svg", tag: "ascend-reminder", data: {url: "/"}}));
});
self.addEventListener("notificationclick", event => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(clients => {
    const client = clients.find(item => new URL(item.url).origin === self.location.origin);
    return client ? client.focus() : self.clients.openWindow("/");
  }));
});
