# Observatoire de la parole politique — Cadrage projet

Oct 20, 2026 · @William Vernay

## Vision et principes

L'outil agrège chaque jour les vérifications publiées par des fact-checkers reconnus et des organismes officiels, les rattache à des personnalités politiques identifiées, et les rend filtrables par période, pays, parti, personne et verdict. **Il ne juge jamais lui-même** : chaque entrée renvoie vers sa source.

**Périmètre beta** : France, personnalités à affiliation publique (élus, candidats, porte-paroles), fact-checks datés, petite base alimentée par la routine quotidienne, interface en artefact.

**Principes non négociables** (à reprendre tels quels dans le CLAUDE.md) :

1. Aucun verdict produit par l'outil. Le verdict affiché est celui de la source, avec son libellé d'origine visible.
2. Traçabilité totale : chaque entrée = lien source + date de la déclaration + date de la vérification + éditeur.
3. Un verdict qui ne se place pas sur l'axe vrai/faux va en « non classable », jamais forcé.
4. Chaque compteur s'affiche avec son dénominateur (nombre de déclarations vérifiées) et la mention « sur les déclarations vérifiées, pas sur l'ensemble des propos ».
5. Rattachement partisan uniquement pour les affiliations publiques et sourcées, datées dans le temps.
6. Métadonnées seulement (titre, verdict, date, lien) : jamais le contenu des articles.
7. Toute attribution incertaine reste en file de validation humaine avant publication.

## Les 3 modules fonctionnels

Les trois options retenues deviennent trois modules. A et C sont dans la beta ; B arrive en V2 sur un thème pilote.

| Module | Rôle | Ce que voit l'utilisateur | Phase |
| --- | --- | --- | --- |
| A — Agrégation échelle complète | Collecter les fact-checks sur toute l'échelle (vrai → faux), en priorisant les sources qui publient aussi des « vrai » | Liste datée de vérifications, verdict d'origine + verdict normalisé | Beta |
| B — Mise en regard avec la donnée officielle | Pour une affirmation chiffrée, afficher la série officielle correspondante (INSEE, Eurostat…) avec son lien, **sans verdict** | Déclaration à gauche, donnée officielle à droite, l'utilisateur juge | V2 (thème pilote : emploi ou finances publiques) |
| C — Indicateurs honnêtes | Afficher chaque compteur avec son dénominateur et la couverture | « 12 vérifications : 2 vrai, 3 plutôt vrai… » + mention de périmètre | Beta |

**Module A — règle de priorisation.** Les connecteurs portent un attribut `full_scale` (la source publie-t-elle des verdicts positifs ?). L'affichage par défaut ne change pas, mais le tableau de bord interne suit la part de verdicts positifs par source pour piloter l'ajout de nouvelles sources.

**Module B — garde-fous.** Une mise en regard n'est publiée que si la série officielle correspond à la même période, au même périmètre géographique et à la même unité que l'affirmation. Sinon elle reste en file de validation. Le libellé à l'écran est « Donnée officielle de référence », jamais « Vrai » ou « Faux ».

**Module C — affichage minimal obligatoire** pour chaque personne ou parti : nombre total de vérifications sur la période, répartition par verdict normalisé, nombre de sources distinctes, date de la vérification la plus récente.

## Sources et connecteurs

La beta tourne avec trois connecteurs sans demande d'accès ; les autres arrivent par phase. Chaque connecteur convertit sa source vers le schéma commun (section suivante), rien d'autre.

| Connecteur | Type d'accès | Module | Phase | Point d'attention |
| --- | --- | --- | --- | --- |
| `jsonld_crawler` — balisage ClaimReview des pages de fact-checkers FR (AFP Factuel, Les Décodeurs, Libération CheckNews, franceinfo Vrai ou Fake, Les Surligneurs) | RSS / sitemap + extraction JSON-LD | A | Beta | Respect du robots.txt, 1 requête / 2 s par domaine |
| `google_factcheck` — Fact Check Claim Search API | Clé API Google Cloud (gratuite) | A | Beta | Quota par jour, requêtes par nom de personnalité |
| `datacommons_feed` — flux ClaimReview Data Commons | Téléchargement quotidien, CC BY | A | Beta | Fort recoupement avec Google : dédoublonnage obligatoire |
| `fullscale_intl` — fact-checkers à échelle complète (PolitiFact, Pagella Politica…) | JSON-LD / RSS | A | V2 | Utile surtout à l'extension multi-pays |
| `dbkf` — Database of Known Fakes (vera.ai) | Sur demande | A | V2 | Faire la demande dès le lancement de la beta |
| `official_stats` — INSEE, Eurostat | API publiques | B | V2 | Correspondance période / périmètre / unité |
| `euvsdisinfo` — base EUvsDisinfo | Serveur MCP sur demande | Onglet « ingérences » | V3 | Vise des médias, pas des politiques nationaux |

**Exclus du compteur principal** : Community Notes de X (contributions d'utilisateurs, pas de vérification professionnelle) et tout jeu de données sous licence « recherche uniquement » (ex. Fact-Check Insights).

**Sources d'attribution** (pas des fact-checks) : open data Assemblée nationale et Sénat, Wikidata (historique des partis), ParlGov pour normaliser les partis entre pays.

## Modèle de données et datation

Chaque fait porte trois dates distinctes ; le tri par période utilise la **date de la déclaration**, avec repli sur la date de vérification quand la source ne la fournit pas.

| Date | Champ | Source | Usage |
| --- | --- | --- | --- |
| Déclaration | `claim_date` | `itemReviewed.datePublished` du ClaimReview, sinon extraite de l'article | Filtre « période » par défaut |
| Vérification | `review_date` | `datePublished` du ClaimReview | Repli + filtre « vérifié entre… » |
| Collecte | `ingested_at` | Horodatage de la routine | Suivi interne, jamais affiché comme date du fait |

Un champ `date_precision` (`day`, `month`, `unknown`) et un indicateur `date_is_fallback` signalent les dates incertaines ; l'interface les affiche en italique.

```sql
-- Beta : SQLite. V2 : Postgres, même schéma.
CREATE TABLE sources (
  id TEXT PRIMARY KEY,            -- 'afp_factuel'
  name TEXT, country TEXT, url TEXT,
  full_scale INTEGER,             -- publie des verdicts positifs ?
  licence TEXT, connector TEXT
);

CREATE TABLE persons (
  id TEXT PRIMARY KEY,            -- QID Wikidata, ex. 'Q12345'
  full_name TEXT, aliases TEXT,   -- JSON
  country TEXT, public_role TEXT
);

CREATE TABLE parties (
  id TEXT PRIMARY KEY, name TEXT, short_name TEXT,
  country TEXT, parlgov_id INTEGER
);

CREATE TABLE affiliations (       -- datées : un politique peut changer de parti
  person_id TEXT, party_id TEXT,
  start_date TEXT, end_date TEXT, source_url TEXT
);

CREATE TABLE claims (             -- une affirmation, dédoublonnée
  id TEXT PRIMARY KEY,
  text TEXT, person_id TEXT,      -- NULL tant que non attribuée
  claim_date TEXT, date_precision TEXT, date_is_fallback INTEGER,
  country TEXT, channel TEXT,     -- 'tv', 'x', 'presse', 'meeting'...
  attribution_status TEXT         -- 'auto_sure', 'to_review', 'validated', 'rejected'
);

CREATE TABLE reviews (            -- un fact-check ; plusieurs par claim possible
  id TEXT PRIMARY KEY,            -- hash(url)
  claim_id TEXT, source_id TEXT,
  url TEXT UNIQUE, title TEXT,
  rating_original TEXT,           -- libellé exact de la source
  rating_normalized TEXT,         -- échelle commune
  review_date TEXT, ingested_at TEXT, lang TEXT
);

CREATE TABLE rating_map (
  source_id TEXT, rating_original TEXT, rating_normalized TEXT,
  decided_by TEXT                 -- 'rule', 'llm_validated', 'human'
);

CREATE TABLE official_refs (      -- module B
  claim_id TEXT, provider TEXT, series_id TEXT,
  value TEXT, unit TEXT, period TEXT, url TEXT, status TEXT
);

CREATE TABLE runs (
  id INTEGER PRIMARY KEY, started_at TEXT, connector TEXT,
  fetched INTEGER, new_reviews INTEGER, errors TEXT
);
```

**Rattachement partisan à la date du fait** : le parti affiché pour une déclaration est celui de l'affiliation en vigueur à `claim_date`, pas le parti actuel. Un filtre « par parti » sur 2024 ne compte donc pas un transfuge de 2026.

## Échelle de verdicts

L'échelle commune compte cinq niveaux plus « non classable » ; la table `rating_map` fait la conversion, source par source.

| Niveau normalisé | Code | Exemples de libellés d'origine |
| --- | --- | --- |
| Vrai | `true` | True, Vrai, Correct |
| Plutôt vrai | `mostly_true` | Mostly True, Plutôt vrai |
| À moitié vrai | `half_true` | Half True, Imprécis, Nì |
| Plutôt faux | `mostly_false` | Mostly False, Trompeur, Exagéré |
| Faux | `false` | False, Faux, Pants on Fire, Inventé |
| Non classable | `unrated` | Manque de contexte, Satire, Montage, Invérifiable |

**Règles de conversion, dans l'ordre :**

1. Correspondance exacte (source + libellé, insensible à la casse et aux accents) dans `rating_map`.
2. Sinon, `ratingValue` numérique du ClaimReview rapporté à `bestRating` / `worstRating`, uniquement si la source est connue pour l'utiliser de façon cohérente.
3. Sinon, proposition par un modèle de langage, stockée avec `decided_by = 'llm_validated'` **seulement après validation humaine**. En attente : `unrated`.

L'interface affiche toujours le libellé d'origine à côté du niveau normalisé (ex. « Plutôt faux — *Trompeur* selon AFP Factuel »).

## Routine quotidienne

La routine tourne une fois par jour à 6 h (heure de Paris), collecte les nouveautés des 7 derniers jours sur chaque connecteur, et publie un export JSON consommé par l'app.

&#91;embedded content: pipeline quotidien · 3 connecteurs, 1 file de validation\]

Les trois connecteurs alimentent une normalisation commune ; seule une entrée sûre ou validée à la main rejoint l'export lu par l'app.

**Étapes** (une commande par étape, enchaînées par `run_daily.py`) :

1. **Collecte** — chaque connecteur récupère les vérifications publiées depuis sa dernière exécution réussie, avec 7 jours de recouvrement pour rattraper les retards de publication.
2. **Normalisation** — conversion vers le schéma commun ; les dates sont parsées en ISO 8601 et `date_precision` est renseigné.
3. **Dédoublonnage** — par URL d'abord (clé unique), puis par similarité d'affirmation (section Attribution).
4. **Attribution** — `claimant` → personne → parti à la date du fait.
5. **Conversion des verdicts** — via `rating_map`.
6. **File de validation** — tout ce qui est incertain passe en `to_review` et n'apparaît pas dans l'export public.
7. **Export** — `data/export/facts.json` (entrées validées uniquement) + `data/export/stats.json` (agrégats par personne, parti, pays, mois).
8. **Journal** — une ligne par connecteur dans `runs` ; alerte si un connecteur renvoie 0 résultat 3 jours de suite.

**Ordonnancement**

- Beta : lancement manuel depuis Claude Code (`python -m pipeline.run_daily`), puis une tâche planifiée quotidienne.
- Ensuite : GitHub Actions avec un `cron` quotidien, qui commite l'export dans le repo ou le pousse vers le stockage de l'app.

**Idempotence** : relancer la routine le même jour ne crée aucun doublon (clé `url` unique, upsert). Une erreur sur un connecteur n'arrête pas les autres.

## Attribution et dédoublonnage

L'attribution est le seul vrai risque juridique restant : une erreur fait dire à l'outil ce que le fact-checker n'a pas dit. Elle est donc stricte, et tout doute passe par la validation humaine.

**Attribution d'une vérification à une personne**

1. Référentiel fermé : la beta ne connaît que les personnes listées dans `persons` (point de départ : députés, sénateurs, eurodéputés français, membres du gouvernement, chefs de parti).
2. Correspondance du champ `claimant` avec `full_name` ou `aliases` → `auto_sure` seulement si la correspondance est exacte et unique.
3. Libellés vagues (« des internautes », « un post Facebook », « un élu RN ») → jamais attribués à une personne.
4. Correspondance partielle ou ambiguë (homonymes, nom seul) → `to_review`.
5. Le parti est déduit de `affiliations` à la date du fait, jamais saisi depuis l'article.

**Dédoublonnage**

- Niveau 1 — même URL : même `review`, upsert.
- Niveau 2 — même affirmation vérifiée par plusieurs médias : un seul `claim`, plusieurs `reviews` rattachées. Critères : même personne, dates de déclaration à ±3 jours, similarité de texte élevée (embeddings ou TF-IDF).
- Les compteurs comptent des `claims`, pas des `reviews`. Si deux sources divergent sur le verdict, la fiche affiche les deux et le compteur retient le verdict le plus fréquent ; en cas d'égalité, `unrated`.

## App web et beta

La beta est un artefact unique qui lit `facts.json` (100 à 300 entrées validées) ; la réflexion UI/UX se fait d'abord en maquettes Design, avant d'écrire l'artefact.

**Écrans**

| Écran | Contenu | Module |
| --- | --- | --- |
| Accueil | Compteurs par verdict sur la période choisie + dénominateur, dernières vérifications | A, C |
| Liste des faits | Liste filtrable, triée par date de déclaration décroissante ; chaque ligne = personne, parti, extrait de l'affirmation, verdict normalisé + libellé d'origine, source, deux dates, lien | A |
| Fiche personne | Répartition des verdicts, frise des vérifications dans le temps, partis successifs, liste des faits | A, C |
| Fiche parti | Agrégats par personne du parti, répartition des verdicts, mention de couverture | C |
| Méthodologie | Principes, sources, échelle, limites, contact pour contester une entrée | — |
| Mise en regard (V2) | Déclaration chiffrée à côté de la série officielle | B |

**Filtres** (combinables, reflétés dans l'URL pour partager une vue) :

- **Période** : 7 jours, 30 jours, 12 mois, année civile, plage personnalisée. Bascule « date de déclaration » / « date de vérification ».
- **Pays**, **parti**, **personne** (recherche), **verdict** (multi-sélection), **source**.

**Parcours beta, en deux temps**

1. Maquettes Design : accueil, liste des faits, fiche personne, en 2 ou 3 variantes. Sujets à trancher : comment rendre lisible le dénominateur, comment montrer un verdict sans effet « tableau d'honneur », place du libellé d'origine.
2. Artefact : une seule page HTML qui embarque l'export JSON, reprend la variante retenue, et fonctionne sur mobile.

**Ce que la beta ne fait pas** : pas de comptes, pas de commentaires d'utilisateurs, pas de classement des « pires » personnalités.

## Stack et arborescence

Python pour le pipeline, SQLite pour la beta, un export JSON statique pour l'app : rien à héberger côté serveur tant que la beta tourne.

| Couche | Beta | Après la beta |
| --- | --- | --- |
| Pipeline | Python 3.12, `httpx`, `extruct` (JSON-LD), `feedparser`, `rapidfuzz` | Idem + embeddings pour le dédoublonnage |
| Base | SQLite (`data/observatoire.db`) | Postgres (Supabase ou équivalent) |
| Ordonnancement | Lancement manuel puis tâche planifiée | GitHub Actions `cron` |
| Front | Artefact HTML unique + JSON embarqué | Next.js ou Astro, données statiques régénérées chaque jour |
| Tests | `pytest` avec pages HTML de fact-checkers en fixtures | Idem + test de non-régression sur `rating_map` |

```text
observatoire/
├── CLAUDE.md                 # principes + conventions (section dédiée)
├── README.md
├── pyproject.toml
├── pipeline/
│   ├── run_daily.py          # orchestre les 8 étapes
│   ├── schema.sql
│   ├── connectors/
│   │   ├── base.py           # interface commune : fetch() -> list[RawReview]
│   │   ├── jsonld_crawler.py
│   │   ├── google_factcheck.py
│   │   └── datacommons_feed.py
│   ├── normalize.py
│   ├── dedupe.py
│   ├── attribute.py
│   ├── ratings.py            # application de rating_map
│   └── export.py
├── data/
│   ├── seeds/                # persons.csv, parties.csv, affiliations.csv, rating_map.csv
│   ├── review_queue/         # entrées to_review, exportées pour validation
│   └── export/               # facts.json, stats.json
├── web/
│   └── beta/index.html       # l'artefact
└── tests/
    ├── fixtures/
    └── test_*.py
```

Secrets (clé API Google) dans `.env`, jamais commités ; `.env.example` versionné.

## Conformité

À cocher avant toute ouverture publique, même de la beta ; une consultation avec un avocat en droit de la presse et des données est recommandée avant le lancement.

**RGPD**

- [ ] Rattachement partisan limité aux affiliations publiques et sourcées (exception des données rendues manifestement publiques)
- [ ] Analyse d'impact (AIPD) rédigée
- [ ] Registre de traitement et mentions d'information sur la page Méthodologie
- [ ] Procédure de rectification et d'opposition, avec délai de réponse annoncé

**Diffamation et exactitude**

- [ ] Aucun verdict propre à l'outil ; libellé d'origine toujours visible
- [ ] Lien source sur chaque entrée
- [ ] Bouton « signaler une erreur » sur chaque entrée, retrait sous 48 h si l'attribution est contestée à raison
- [ ] Aucune attribution publiée sans statut `auto_sure` ou `validated`

**Licences et collecte**

- [ ] Conditions d'utilisation vérifiées et notées dans `sources.licence` pour chaque source
- [ ] Aucune source « recherche uniquement » dans l'export public
- [ ] robots.txt respecté, débit limité, user-agent identifiant le projet avec un contact
- [ ] Métadonnées seulement, pas de reprise du contenu des articles

**Neutralité**

- [ ] Méthodologie publique, identique pour tous les partis
- [ ] Pas de classement ni de mise en avant des « pires » personnalités

## Roadmap

&#91;embedded content: roadmap · 4 phases, 3 portes\]

On ne passe à la phase suivante qu'une fois la porte franchie ; aucune date n'est fixée tant que la beta n'a pas tourné quelques semaines.

## Démarrer dans Claude Code

Exporte ce document en Markdown, place-le dans le repo sous `docs/cadrage.md`, puis crée le `CLAUDE.md` ci-dessous ; Claude Code le relit à chaque session.

```markdown
# Observatoire de la parole politique

Spécification complète : docs/cadrage.md (à lire avant toute tâche).

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
- pytest
```

**Premiers prompts, dans l'ordre** (un par session, en vérifiant le résultat avant de passer au suivant) :

1. « Lis docs/cadrage.md. Initialise le repo selon l'arborescence décrite, crée schema.sql et les fichiers de seeds vides avec leurs en-têtes. Ne code aucun connecteur. »
2. « Code connectors/base.py et le connecteur jsonld\_crawler pour un seul site : AFP Factuel. Enregistre 3 pages en fixtures et écris les tests. Montre-moi 5 entrées normalisées. »
3. « Remplis rating\_map.csv avec les libellés trouvés et code ratings.py. Liste les libellés non convertis. »
4. « Remplis persons.csv, parties.csv et affiliations.csv pour les députés en exercice depuis l'open data de l'Assemblée nationale et Wikidata. Code attribute.py. »
5. « Ajoute les 4 autres sites français, puis google\_factcheck (clé dans .env) et datacommons\_feed. Code dedupe.py. »
6. « Code run\_daily.py et export.py. Lance la routine sur 90 jours d'historique et donne-moi les chiffres : collectées, attribuées, en file, exportées. »
7. « Génère web/beta/index.html à partir de la maquette retenue, avec facts.json embarqué et les filtres période, pays, parti, verdict. »

## Risques et questions ouvertes

| Risque | Effet | Parade |
| --- | --- | --- |
| Peu de verdicts positifs dans les sources françaises | Compteurs « vrai » quasi vides, lecture biaisée | Module C (dénominateur), sources à échelle complète, module B en V2 |
| Erreur d'attribution | Risque de diffamation | Référentiel fermé, file de validation, signalement + retrait sous 48 h |
| Changement de format d'un site source | Connecteur muet sans erreur visible | Alerte après 3 jours à 0 résultat, tests sur fixtures |
| Baisse du nombre de fact-checks publiés (financements des fact-checkers fragiles) | Moins de matière, compteurs qui stagnent | Diversifier les pays et les sources, afficher la couverture |
| Accusation de partialité | Attaque sur la crédibilité de l'outil | Méthodologie publique identique pour tous, pas de classement |
| `claim_date` absente chez certaines sources | Tri par période approximatif | Repli sur `review_date`, signalé dans l'interface |

**Questions à trancher pendant la beta**

- Validation humaine : combien d'entrées par jour en file, et qui valide ?
- Faut-il inclure les maires et élus locaux, ou rester au niveau national ?
- Thème pilote du module B : emploi ou finances publiques ?
- Nom définitif du projet (le titre de ce document est provisoire).
