/*
 * Algora service worker.
 * Copyright © 2026 Kian Dolatabadi. All rights reserved.
 * Proprietary software — evaluation use only. See LICENSE and TERMS.md.
 */
const CACHE_NAME = 'algora-v1.4';

const PRECACHE_URLS = [
  './algora.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
  './vendor/three/build/three.module.js',
  './vendor/three/examples/jsm/controls/OrbitControls.js',
  './vendor/three/examples/jsm/loaders/GLTFLoader.js',
  './vendor/three/examples/jsm/utils/BufferGeometryUtils.js',
  './male_body.glb',
  './low_poly_female_body__teeth__tongue_lp.glb',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

// Cache-first: works fully offline once installed; falls back to network for anything uncached.
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
