# CUBO+ Hackathon Project

> Evaluation: Camino a la Fase Tech — "Don't trust, verify"

## Team
<!-- Completar con los miembros del equipo -->
| Nombre | Rol | GitHub |
|--------|-----|--------|
| | Tech Lead | @wkatir |
| | Tech | |
| | Non-Tech Lead | |
| | Non-Tech | |

## Project Idea
<!-- Describir brevemente el proyecto elegido -->

## Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Database**: SQLite (desarrollo) / PostgreSQL (producción)
- **ORM**: SQLAlchemy
- **Validation**: Pydantic

## Repository Structure
```
/src        → Python code (led by Tech profile)
/strategy   → Business model & documentation (led by Non-Tech profile)
```

## Quick Start
```bash
# 1. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# 2. Instalar dependencias
pip install -r src/requirements.txt

# 3. Copiar variables de entorno
cp .env.example .env

# 4. Ejecutar servidor
uvicorn src.main:app --reload

# 5. Ver documentación API
# http://localhost:8000/docs
```

## Submission
**Deadline**: April 21, 2026
