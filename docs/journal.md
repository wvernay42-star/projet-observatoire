# Journal de bord

Suivi de l'avancement, entrée par entrée (la plus récente en haut). Chaque session de travail
ajoute une entrée : ce qui a été fait, ce qui a été constaté, ce qui bloque, la suite.
Les décisions durables sont aussi consignées dans [decisions.md](decisions.md).

## État d'avancement (cadrage, « Premiers prompts »)

| # | Étape | État |
|---|---|---|
| 1 | Initialiser le repo, schema.sql, seeds vides | ✅ fait (20/10) |
| 2 | connectors/base.py + jsonld_crawler (AFP Factuel) | ✅ base.py ; crawler abandonné au profit de google_factcheck (21/10) |
| 3 | rating_map.csv + ratings.py | ✅ fait (21/10) — 15 propositions à valider |
| 4 | persons / parties / affiliations + attribute.py | ✅ fait (21/10) — 67 724 personnes, partis à valider pour beaucoup |
| 5 | Autres sites FR, google_factcheck, datacommons_feed, dedupe.py | 🟡 google_factcheck + datacommons_feed faits ; dedupe.py à faire |
| 6 | run_daily.py + export.py, routine sur 90 jours | ⏳ |
| 7 | web/beta/index.html (maquette A) | ⏳ |
| — | Page web de validation (maquette faite) | ⏳ |

## 2026-10-21 (nuit) — connecteur google_factcheck, premières données récentes

**Décision** : TF1 Info (Les Vérificateurs) et 20 Minutes (Fake Off) ajoutés aux sources ;
toutes les sources passent par `google_factcheck` (sources.csv, colonne `connector`).
`full_scale = 1` pour TF1 Info, franceinfo et 20 Minutes (verdicts positifs observés).

**rating_map.csv modifié** : ajout, pour les 7 sources, des libellés donnés en exemple dans le
tableau « Échelle de verdicts » du cadrage (Vrai, Correct, Plutôt vrai, À moitié vrai, Imprécis,
Plutôt faux, Trompeur, Exagéré, Faux, Inventé, Manque de contexte, Satire, Montage, Invérifiable)
→ 112 règles. « TROMPEUR » (Décodeurs) retiré des propositions puisque couvert par le cadrage.
Nouvelles propositions à valider : « En partie vrai » (TF1), « C'est plus compliqué » (franceinfo),
« Image générée par IA », « Photo manipulée », « Vidéo manipulée », « Infondé » (AFP).

**Collecte réelle sur 90 jours** (`python -m pipeline.connectors.google_factcheck --days 90`) :
- 242 vérifications : AFP 96, TF1 Info 97, 20 Minutes 41, franceinfo 8.
- Verdicts : faux 150, plutôt faux 44, vrai 6, plutôt vrai 4, non classable 38
  (dont 37 en attente de validation de libellé). Le déséquilibre vers « faux » prévu au
  cadrage se confirme.
- Attribution : 25 `auto_sure`, 6 `to_review` (nom + fonction, ex. « Julien Odoul, député RN »),
  211 écartées (166 libellés vagues : « Sources multiples », « X », publications de réseaux
  sociaux… ; 33 hors référentiel, surtout des comptes étrangers ; 12 sans claimant).
- 31 déclarations de personnalités au total : Le Pen, Mélenchon, Retailleau, Bardella,
  Tondelier, Panot, Macron, Glucksmann, Knafo, Bergé, Lecornu, Hollande, Philippot…
- 76 vérifications sur 242 n'ont pas de date de déclaration → repli sur la date de vérification.
- AFP et 20 Minutes vérifient surtout des contenus viraux ; TF1 Info et franceinfo
  apportent l'essentiel des déclarations de personnalités.

**Autres éditeurs vus dans l'API** (non suivis) : Poligraph (poligraph.fr), DE FACTO
(defacto-observatoire.fr).

## 2026-10-21 (soir) — clé Google, référentiel des personnalités

**Clé API Google** : configurée en « Network secret » (en-tête `X-goog-api-key` injecté
automatiquement vers `factchecktools.googleapis.com`) ; fonctionne. Accès `www.franceinfo.fr` ouvert.

**Ce que remonte l'API Google Fact Check** (filtre par site éditeur) :

| Éditeur | 90 jours | 365 jours | Plus récente |
|---|---|---|---|
| factuel.afp.com | 93 | ≥ 200 | 20/10/2026 |
| tf1info.fr (Les Vérificateurs) | 97 | ≥ 200 | 19/10/2026 |
| 20minutes.fr (Fake Off) | 41 | 191 | 20/10/2026 |
| franceinfo.fr | 8 | 24 | 17/10/2026 |
| lemonde.fr, liberation.fr, lessurligneurs.eu | 0 | 0 | — |

→ Proposition : ajouter TF1 Info et 20 Minutes aux sources suivies (à valider).

**Étape 4 — référentiel** (`python -m pipeline.referential`, ~25 min, source Wikidata) :
- 67 724 personnes : députés (15e–17e législatures, 1 628), sénateurs (691), eurodéputés
  français (202), gouvernement (127), présidents de la République (2), dirigeants de parti (195),
  maires depuis 2014 (65 595). 269 partis, 3 915 affiliations.
- Dates d'affiliation gardées à leur précision réelle (Wikidata note souvent « 2015-01-01 »
  pour « 2015 ») : jamais de 1er janvier inventé.
- Seulement ~19 % des affiliations ont une date de début ; beaucoup de personnes n'ont aucune
  affiliation connue (maires surtout).

**Étape 4 — attribution** (`python -m pipeline.attribute`) sur les 89 vérifications FR du flux :
- 24 attribuées `auto_sure` (15 personnalités, toutes correctes), 65 écartées (internautes,
  médias, sites, personnes hors référentiel : Jean-Pierre Pernault, Ursula von der Leyen…).
- Parti à la date du fait : sûr pour 7 personnes sur 15 (Le Pen, Bardella, Bay → RN ;
  Ciotti → LR ; Macron → RE ; Asselineau → UPR ; Monot → DLF).
- Règle ajoutée : une affiliation **sans aucune date** n'est jamais utilisée automatiquement
  (cas Jacques Maire : Wikidata ne connaît que le PS, sans date, alors qu'il était LREM en 2020).
  Ces cas (8 personnes) passent en validation avec les partis candidats.

**Limites connues** :
- Noms de parti : Wikidata donne le nom actuel (« Renaissance » pour LREM en 2020,
  « Rassemblement national » pour le FN en 2017). À traiter : nom en vigueur à la date (P1448 daté).
- Les affiliations validées à la main devront être stockées à part
  (ex. `data/seeds/affiliations_manual.csv`) pour survivre à une reconstruction du référentiel.
- Grand nombre d'homonymes chez les maires (1 900+ noms partagés) : ils passeront en validation.

**Prochaines étapes proposées** : connecteur `google_factcheck` (AFP, TF1 Info, 20 Minutes,
franceinfo), puis `dedupe.py`, puis tableau de validation.

## 2026-10-21 (suite) — accès réseau ouvert, test des sources

**Accès** : Le Monde, Libération, Les Surligneurs, Assemblée nationale, Sénat, Wikidata, ParlGov : OK.
- `www.francetvinfo.fr` redirige désormais vers `www.franceinfo.fr` : domaine à ajouter à
  l'environnement (sources.csv mis à jour).
- `api.insee.fr` : toujours inaccessible (utile seulement en V2, module B).
- **AFP Factuel** : refusé par le site lui-même (protection Akamai, 403 même avec un
  navigateur standard). Pas de contournement.
- **Libération CheckNews** : flux RSS accessible, mais les articles renvoient 403 (anti-robot).

**robots.txt** : notre robot est autorisé sur Le Monde (Décodeurs), Libération et Les Surligneurs.

**Constat majeur** : sur 20 articles récents des Décodeurs et 6 des Surligneurs, **aucun ne
contient de balisage ClaimReview**. Le connecteur `jsonld_crawler` prévu au cadrage ne
collecterait rien sur ces sites. Les fact-checkers déclarent plutôt leurs vérifications
directement à Google (outil Fact Check Markup), ce qui les rend visibles via l'API
Google Fact Check Tools sans balisage dans la page.

**Conséquence proposée** : faire de `google_factcheck` la source principale de la beta
(clé API à créer), garder `datacommons_feed` en complément, et ne coder `jsonld_crawler`
que pour un site qui balise effectivement ses pages. À trancher par le porteur du projet.

## 2026-10-21 — maquettes, repo GitHub, conversion des verdicts

- Repo GitHub `wvernay42-star/projet-observatoire` créé et alimenté.
- Maquettes (3 variantes + tableau de validation) : variante **A « Jauge »** retenue.
- User-agent du robot : `g.nevert/0.1 (…; +mailto:guillaume.nevert@outlook.com)`.
- Étape 3 : `rating_map.csv` limité aux libellés sans ambiguïté (Vrai / C'est vrai / Faux /
  C'est faux, pour les 5 sources) ; 15 propositions de conversion dans
  `data/review_queue/rating_proposals.csv`, en attente de validation. Règle numérique
  désactivée (notes ratingValue incohérentes chez Les Décodeurs).
- Sur les 89 vérifications FR du flux : 57 converties, 32 en attente.

## 2026-10-20 — démarrage

- Environnement cloud : Python 3.12 (uv), dépendances, hook de démarrage de session.
- Étape 1 faite. Connecteur `datacommons_feed` codé et testé.
- Constat : le flux Data Commons ne contient que 89 fact-checks FR, tous de 2017 à 2020.
