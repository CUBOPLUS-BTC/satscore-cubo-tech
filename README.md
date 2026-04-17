# Vulk

> CUBO+ Hackathon 2026 | "Don't trust, verify"

## Team

| Name | Role | GitHub |
|------|------|--------|
| | Tech Lead | @wkatir |
| | Tech | |
| | Non-Tech Lead | |
| | Non-Tech | |

## Tech Stack

- **Backend**: FastAPI (Python 3.11+) Dockerized
- **Database**: PostgreSQL 16 Dockerized
- **Frontend**: SvelteKit 2.57 + Svelte 5 + Tailwind 4 Cloudflare Pages
- **ORM**: SQLAlchemy + Alembic (migrations)
- **Validation**: Pydantic
- **Auth**: Nostr NIP-98

## Repository Structure

```
/src                Backend Python (FastAPI) + Dockerfile
/front-end-svelte   SvelteKit app (Cloudflare Pages)
/strategy           Business model & documentation (Non-Tech)
```

## Quick Start

### Backend + Database (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

### Frontend (SvelteKit)

```bash
cd front-end-svelte
cp .env.example .env    # API_URL=http://localhost:8000
bun install
bun run dev
```

- App: http://localhost:5173

### Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for full Hetzner + Cloudflare Pages guide.

## Submission

**Deadline**: April 21, 2026
