# Soom React frontend on Railway

Railway service: `Soom` (production)

- GitHub repo: `o-seonghwan/Soom`, branch `main`
- Root directory: `/app/frontend`
- Dockerfile: `Dockerfile` in this root
- App listener: Nginx, TCP 8080
- Healthcheck path: `/`
- API requests: browser uses `/api/...`; Nginx proxies to the existing `soom-backend` HTTPS endpoint
- Build-time `VITE_API_BASE_URL` is the empty string to keep requests on this origin
- Build-time `VITE_USE_MOCK` is `false`; actual API is used

The existing React page layout and navigation are unchanged. A CARTO map
tile API key is still required for the current basemap, unless the app's
basemap provider is changed in a separate reviewed change.
