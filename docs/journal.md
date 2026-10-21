# Journal de bord

Suivi de l'avancement, entrée par entrée (la plus récente en haut). Chaque session de travail
ajoute une entrée : ce qui a été fait, ce qui a été constaté, ce qui bloque, la suite.
Les décisions durables sont aussi consignées dans [decisions.md](decisions.md).

## État d'avancement (cadrage, « Premiers prompts »)

| # | Étape | État |
|---|---|---|
| 1 | Initialiser le repo, schema.sql, seeds vides | ✅ fait (20/10) |
| 2 | connectors/base.py + jsonld_crawler (AFP Factuel) | ⚠️ base.py fait ; crawler remis en question (voir 21/10) |
| 3 | rating_map.csv + ratings.py | ✅ fait (21/10) — 15 propositions à valider |
| 4 | persons / parties / affiliations + attribute.py | ⏳ à faire (sources accessibles) |
| 5 | Autres sites FR, google_factcheck, datacommons_feed, dedupe.py | 🟡 datacommons_feed fait ; google_factcheck attend une clé API |
| 6 | run_daily.py + export.py, routine sur 90 jours | ⏳ |
| 7 | web/beta/index.html (maquette A) | ⏳ |
| — | Page web de validation (maquette faite) | ⏳ |

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

**Étape 4** : voir le bilan ci-dessous (référentiel Wikidata + attribute.py).

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
