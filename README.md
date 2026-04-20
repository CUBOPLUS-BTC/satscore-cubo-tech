# Magma

> CUBO+ Hackathon 2026 | "Don't trust, verify"

Bitcoin financial toolkit for El Salvador and Latin America. Named after volcanic/geothermal Bitcoin mining (Volcano Energy, Lava Pool).

## Team

| Name | Role | GitHub |
|------|------|--------|
| | Tech Lead | @wkatir |
| ivane009 | Tech | @ivane009 |
| | Non-Tech Lead | |
| | Non-Tech | |

## Tech Stack

- **Backend**: Python 3.11+ (custom http.server, no framework)
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Frontend**: SvelteKit 2.57 + Svelte 5 (runes) + Tailwind 4 + shadcn-svelte
- **Auth**: Nostr NIP-07/NIP-98 + LNURL-auth (LUD-04)
- **Deploy**: Hetzner (backend) + Cloudflare Pages (frontend)

## Repository Structure

```
/src                Backend Python + SQLite
/front-end-svelte   SvelteKit app (Cloudflare Pages)
/strategy           Business model & documentation (Non-Tech)
```

## Quick Start

### Backend

```bash
cd src
cp .env.example .env
python main.py
```

- API: http://localhost:8000

### Frontend

```bash
cd front-end-svelte
cp .env.example .env    # API_URL=http://localhost:8000
bun install
bun run dev
```

- App: http://localhost:5173

### Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for Hetzner + Cloudflare Pages guide.

## Submission

**Deadline**: April 21, 2026
