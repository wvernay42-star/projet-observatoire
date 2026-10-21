# Tableau de validation

Page privée : https://claude.ai/artifact/At6BYDaT6SbwLv5P2LuSLU (source : `web/validation/index.html`).
Base partagée de la page : collection `queues` (3 documents : `ratings`, `attributions`,
`parties`, déposés par Claude) et collection `decisions` (un document par décision, écrit par
la page ; écriture réservée aux éditeurs du projet).

## Cycle (à chaque lancement de la routine, par Claude)

1. **Rapatrier les décisions** : `ArtifactData list` de la collection `decisions` avec
   `out_dir` = un dossier temporaire, puis
   `python -m pipeline.validation_sync apply <dossier>/decisions`
   → écrit `rating_map.csv` (decided_by = human), `data/validations/attributions.csv`,
   `data/seeds/affiliations_manual.csv`. Idempotent.
2. **Supprimer** dans la base les décisions appliquées (`ArtifactData batch delete`).
3. **Relancer la routine** : `python -m pipeline.run_daily`.
4. **Préparer les files** : `python -m pipeline.validation_sync seed`, puis déposer
   `data/review_queue/validation/{ratings,attributions,parties}.json` dans `queues`
   (`ArtifactData batch set` avec `file_path`, `if_version` = version lue).
5. Commiter et pousser.

## Ce que valide chaque file

- **Verdicts** : niveau de l'échelle commune pour un libellé d'une source ; vaut pour toutes
  les vérifications passées et futures portant ce libellé.
- **Attributions** : personne du référentiel, ou « ne pas attribuer » ; s'applique à toutes
  les vérifications de la déclaration.
- **Partis** : parti à la date de la déclaration (ou « sans étiquette ») ; enregistré comme
  affiliation manuelle du jour de la déclaration, prioritaire sur Wikidata à cette date.
