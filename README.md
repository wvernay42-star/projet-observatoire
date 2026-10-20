# Observatoire de la parole politique

Agrège les vérifications publiées par des fact-checkers reconnus, les rattache à des
personnalités politiques identifiées et les rend filtrables. L'outil ne produit jamais de verdict.

Spécification : [docs/cadrage.md](docs/cadrage.md) · Règles pour Claude Code : [CLAUDE.md](CLAUDE.md)

## Installation

```bash
uv sync                      # Python 3.12 + dépendances
cp .env.example .env         # puis renseigner GOOGLE_FACTCHECK_API_KEY
uv run python -m pipeline.init_db
uv run pytest
```
