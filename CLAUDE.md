# Votona Observatoire (Observatoire de la parole politique)

Charte graphique et liste des candidats communes avec Votona (dépôt wvernay42-star/votona,
votona.fr) : data/seeds/candidates_2027.csv. Les vérifications n'entrent jamais dans le
classement de Votona.

Spécification complète : docs/cadrage.md (à lire avant toute tâche).
Suivi : docs/journal.md (état d'avancement) et docs/decisions.md. À la fin de chaque
session de travail, ajouter une entrée datée en haut de docs/journal.md et mettre à jour
le tableau d'état.

## Règles non négociables
- L'outil ne produit jamais de verdict. Il reprend celui de la source.
- Chaque entrée exportée a : url source, rating_original, rating_normalized,
  claim_date (ou review_date avec date_is_fallback=1), source_id.
- Verdict non convertible -> 'unrated'. Attribution incertaine -> 'to_review'.
- Seules les entrées auto_sure ou validated vont dans data/export/.
- Métadonnées uniquement : jamais le corps des articles.
- Respect du robots.txt, 1 requête / 2 s par domaine.

## Conventions
- Python 3.12, typage, pytest. Un connecteur = une classe héritant de
  connectors/base.py, testée sur des fixtures HTML/JSON locales.
- Dates en ISO 8601. Parti = affiliation en vigueur à claim_date.
- Ne jamais modifier rating_map.csv sans le signaler dans le résumé.

## Commandes
- python -m pipeline.run_daily      # routine complète
- python -m pipeline.run_daily --connector jsonld_crawler --dry-run
- python -m pipeline.validation_sync seed|apply <dossier>   # tableau de validation (docs/validation.md)
- python -m pipeline.build_beta   # artefact (web/beta/) + site statique (site/, Vercel, docs/hebergement.md)
- python -m pipeline.sync_candidates <votona>/index.html   # liste commune des candidats (Votona = source)
- pytest
