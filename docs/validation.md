# Tableau de validation

## Back-office dans l'admin Votona (depuis le 28/10/2026)

Le back-office est l'onglet **« Observatoire »** de l'admin de votona.fr (`?admin=1`, connecté
avec l'email admin). Files et décisions dans la base Supabase de Votona :
- `obs_queues` (une ligne par file : `ratings`, `attributions`, `parties`, `sources`), écrite
  par la routine : `python -m pipeline.supabase_sync push` après `validation_sync seed` ;
- `obs_decisions` (une ligne par décision), écrite par l'onglet ; la routine l'applique sur les
  files telles que l'admin les a vues puis la retire : `python -m pipeline.supabase_sync apply`.
- Lecture et écriture réservées à l'email admin (RLS) ; la routine passe par l'identifiant API
  « Supabase » de l'environnement cloud « Observatoire » (clé secrète, jamais dans le dépôt).

L'ancienne page ci-dessous reste lue pendant la transition (décisions encore présentes) et sert
de repli si l'accès Supabase manque. Code de l'onglet : bloc « ADMIN — OBSERVATOIRE » de
l'`index.html` de Votona.

## Ancienne page (repli)

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
