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

Code de l'onglet : bloc « ADMIN — OBSERVATOIRE » de l'`index.html` de Votona. Si l'accès
Supabase manque, la routine le signale en alerte : les décisions restent dans `obs_decisions` et
sont appliquées au passage suivant.

## Cycle (à chaque lancement de la routine)

1. **Appliquer les décisions** : `python -m pipeline.supabase_sync apply` → écrit `rating_map.csv`
   (decided_by = human), `data/validations/attributions.csv`, `data/seeds/affiliations_manual.csv`,
   puis retire les décisions appliquées. Idempotent.
2. **Relancer la routine** : `python -m pipeline.run_daily`.
3. **Préparer et déposer les files** : `python -m pipeline.validation_sync seed`, puis
   `python -m pipeline.supabase_sync push`.
4. Commiter et pousser.

L'ancienne page Claude de validation (artefact, source `web/validation/index.html`) n'est plus
lue par la routine depuis le 30/10/2026.

## Ce que valide chaque file

- **Verdicts** : niveau de l'échelle commune pour un libellé d'une source ; vaut pour toutes
  les vérifications passées et futures portant ce libellé.
- **Attributions** : personne du référentiel, ou « ne pas attribuer » ; s'applique à toutes
  les vérifications de la déclaration.
- **Partis** : parti à la date de la déclaration (ou « sans étiquette ») ; enregistré comme
  affiliation manuelle du jour de la déclaration, prioritaire sur Wikidata à cette date.
