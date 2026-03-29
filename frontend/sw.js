const CACHE_NAME = 'nexus-cache-v1';
const ASSETS = [
    '/',
    '/static/style.css',
    '/static/app.js',
    '/static/icon-512.png',
    '/static/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
});

self.addEventListener('fetch', (event) => {
    // For API calls, always fetch from network
    if (event.request.url.includes('/auth/') || event.request.url.includes('/matches')) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});
