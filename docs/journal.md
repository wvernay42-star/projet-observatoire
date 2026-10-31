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
| 5 | Autres sites FR, google_factcheck, datacommons_feed, dedupe.py | ✅ fait (21/10) |
| 6 | run_daily.py + export.py, routine sur 90 jours | ✅ fait — 122 entrées exportées sur 2 ans ; planifiée chaque jour à 6 h (22/10) |
| 7 | web/beta/index.html (maquette A) | ✅ en ligne (22/10) — 119 déclarations |
| — | Page web de validation | ✅ en ligne (22/10) — 147 éléments à traiter |
| — | Sujets (familles et sujets Votona), recoupement, angles morts, données ouvertes, RSS | ✅ fait (22/10) |
| — | Pages fixes par candidat, personnalité, parti, sujet + plan du site | ✅ en production (28/10) |
| — | Hébergement préprod (`preprod`) / prod (`main`) | ✅ en ligne (26/10) — projet Vercel `votona-observatoire` ; production indexable depuis le 28/10 |
| — | Liens Votona → Observatoire | ⏳ actifs sur `draft` (test, 26/10) ; `main` sur demande du porteur |

## 2026-10-31 — Routine quotidienne

- Candidats : synchronisation depuis https://votona.fr/ (pas de clone Votona) : 0 ajouté, 0 modifié,
  0 absent ; 2 à confirmer (Selma Labib, Antoine Mikolajczak).
- Décisions de l'admin (Supabase) : 1 décision appliquée, 0 note/attribution/parti modifié, 0 ignorée.
  rating_map.csv inchangé.
- Collecte : google_factcheck 23 récupérées, 3 nouvelles ; datacommons_feed 4 récupérées, 0 nouvelle.
- Base : 7 598 vérifications ; claims : auto_sure 454, validated 173, to_review 163, rejected 6 738.
- Export : 627 entrées (identique à la veille, aucune nouvelle déclaration exportée).
- Files déposées dans Supabase : attributions 163, partis 1, notes 0, sources 7.
- Part de verdicts positifs (toutes vérifications / attribuées) : TF1 Info 20 % / 35 % ; franceinfo
  Vrai ou Fake 29 % / 38 % ; AFP Factuel 0,4 % / 2,8 % ; Poligraph 21 % / 23 % ; Décodeurs 1,6 % / 4,2 % ;
  20 Minutes 11 % / 29 % ; CheckNews 0 % / sans attribution.
- Alerte : aucun résultat nouveau depuis 3 jours pour datacommons_feed (attendue, voir 30/10).
- Images de partage : rien à créer. Beta republiée (version 15 de l'artefact). 88 tests OK.

## 2026-10-30 (soir) — Portraits libres des candidats

- 30 des 38 candidats ont un portrait sous licence libre (Wikimedia Commons : Wikidata P18 et
  catégorie du candidat), le plus récent où un seul visage net occupe le cadre (détection OpenCV),
  validé par le porteur sur planche. Recadrage carré sur le visage, 192×192 WebP (≈ 6 Ko chacun) dans
  `web/beta/portraits/`, crédits (auteur, licence, lien, date) dans `data/seeds/portraits.json`.
  Les 8 autres (Guedj, Egger, Labib, Mikolajczak, Royal, Mathieu, Bouamrane, Markovic) : initiales.
- Pages fixes et application : pastilles de la liste des candidats, en-tête des fiches (84 px, ligne
  « Photo : auteur, licence, via Wikimedia Commons »), page `/credits-photos/` (pied de page, plan du
  site), images de partage des candidats avec le visage. Artefact : initiales (poids).
- Même jeu de photos et de crédits côté Votona (`assets/portraits/`, `data/portraits.json`, section
  « Crédits photos » de /a-propos/). 88 tests OK.

## 2026-10-30 (suite) — Ancienne page de validation retirée, images de partage

- Routine : étapes de repli sur l'ancienne page Claude de validation supprimées (lecture des
  décisions, dépôt des files) ; l'onglet « Observatoire » de l'admin Votona est le seul
  back-office. docs/validation.md et docs/decisions.md mis à jour.
- Images de partage 1200×630 sur le modèle de Votona (`scripts/og-images.js`, Node + Playwright) :
  une par candidat 2027 (couleur du candidat, initiales, parti, loupe) et une par famille de
  sujets (couleur et personnage de la famille), sans chiffre ni verdict. Rangées dans
  `web/beta/og/`, copiées par build_beta dans `site/assets/og/`, utilisées par les fiches
  (`og:image`, `twitter:image`) ; image générale sinon. La routine crée celles qui manquent
  (nouveau candidat) avant la régénération du site. 86 tests OK.

## 2026-10-30 — Couverture : diagnostic et attributions récupérées

- Diagnostic des rédactions manquantes : l'API Google Fact Check n'a plus rien du Monde depuis
  janvier 2021 ni de Libération depuis octobre 2023, rien des Surligneurs ni de Science Feedback.
  Leurs articles ne portent pas de balisage ClaimReview (Le Monde, Les Surligneurs) ou refusent
  les robots (Libération) : pas de verdict structuré à reprendre, donc pas de connecteur possible
  sans déduire un verdict du texte (interdit). Aucun autre éditeur français dans l'API ; le flux
  Data Commons n'ajoute que des sites belges et un ancien lot du Monde (alerte « rien de nouveau
  depuis 3 jours » normale). Piste restante : écrire aux rédactions (reprise du balisage).
- Attribution : « Le député LFI X », « L'ancien Premier ministre X » (nom complet en fin de
  libellé) et « X et Y » vont en validation (`to_review`) au lieu d'être rejetés comme libellés
  vagues. Estimation sur la base actuelle : 162 vérifications à valider (148 TF1 Info), dont
  15 concernant un candidat 2027. Jamais attribuées automatiquement. 85 tests OK.
- Hors périmètre volontaire : les personnalités sans fonction depuis 2017 (ex. Nicolas Sarkozy)
  restent hors référentiel.

## 2026-10-30 — Routine quotidienne

- Candidats : synchronisation avec votona.fr, 0 ajout, 0 modification, 0 absent ; 2 à confirmer (Selma Labib, Antoine Mikolajczak).
- Collecte : google_factcheck 23 récupérées / 3 nouvelles ; datacommons_feed 4 / 0. Aucune erreur de connecteur.
- Décisions appliquées : 0 (admin Votona : aucune ; ancienne page : aucune). rating_map.csv non modifié.
- Claims : auto_sure 454, validated 173, to_review 0, rejected 6 898. Exportées : 627 déclarations (data/export/facts.json), inchangé.
- Files de validation : 0 libellé, 0 attribution, 1 parti, 7 sources ; déposées sur Supabase (obs_queues, back-office admin Votona).
- Part de verdicts positifs (toutes entrées / attribuées) : TF1 Info 20 % / 35 % ; franceinfo Vrai ou Fake 29 % / 38 % ; AFP Factuel 0,4 % / 3 % ; Poligraph 21 % / 23 % ; Les Décodeurs 1,6 % / 4 % ; 20 Minutes Fakeoff 11 % / 29 % ; Libération CheckNews 0 % / —.
- Alertes : « aucun résultat nouveau depuis 3 jours : datacommons_feed ». Beta republiée (artefact version 14), site statique régénéré. 80 tests OK.

## 2026-10-29 — Routine quotidienne

- Candidats : synchronisation avec votona.fr, 0 ajout, 0 modification, 0 absent ; 2 à confirmer (Selma Labib, Antoine Mikolajczak).
- Collecte : google_factcheck 25 récupérées / 1 nouvelle ; datacommons_feed 4 / 0. Aucune erreur de connecteur.
- Décisions appliquées : 2 de l'admin Votona (1 parti, 0 libellé, 0 attribution), 0 ignorée ; ancienne page : aucune décision. rating_map.csv non modifié (affiliations_manual.csv : 1 ligne ajoutée, validation manuelle d'un parti).
- Claims : auto_sure 454, validated 173, to_review 0, rejected 6 895. Exportées : 627 déclarations (data/export/facts.json).
- Files de validation : 0 libellé, 0 attribution, 1 parti, 7 sources ; déposées sur Supabase (obs_queues, back-office admin Votona).
- Part de verdicts positifs (toutes entrées / attribuées) : TF1 Info 20 % / 35 % ; franceinfo Vrai ou Fake 29 % / 38 % ; AFP Factuel 0,4 % / 3 % ; Poligraph 21 % / 23 % ; Les Décodeurs 1,6 % / 4 % ; 20 Minutes Fakeoff 11 % / 29 % ; Libération CheckNews 0 % / —.
- Alertes : aucune. Beta republiée (artefact version 13), site statique régénéré. 80 tests OK.

## 2026-10-29 — Même ergonomie que les pages de votona.fr

- Composants de `generate-candidate-pages.js` repris à l'identique (`template.html`, `build_pages.py`) :
  en-tête illustré (`.vhero`, personnages de Votona copiés dans `web/beta/characters/`, pastilles de
  chiffres), fil d'Ariane « ‹ Tous les … / … › », titres de section à 20 px, espacements, boutons.
- Fiches personnes : en-tête `.cand-header` de Votona (avatar, parti, pastille du nombre de
  vérifications, accessoires des familles les plus vérifiées), bouton principal « Ses positions
  sur Votona », tuiles « Ses sujets vérifiés ».
- Listes : cartes candidats de votona.fr (carte entière cliquable), recherche sur les pages
  Candidats, Personnalités et Partis, légende des verdicts ; bouton « Et toi ? » vers le test sur
  la page Sujets ; en-tête coloré avec le personnage de la famille sur chaque page de sujet.
- Application (accueil, faits, et vues de l'artefact) alignée de la même façon. « 1er » pour le
  premier jour du mois. 80 tests OK. En préproduction.

## 2026-10-28 (nuit) — Encart sur les fiches Votona, mesure d'audience

- `site/donnees/votona.json` (`build_pages.votona_summary`) : par candidat, nombre de déclarations
  vérifiées, rédactions, date de la dernière vérification et adresse de la fiche ; par famille,
  nombre et adresse. Jamais de verdict (test). En-tête CORS sur `/donnees/`.
- Votona (sur `draft`) : encart « Ses déclarations vérifiées » en bas des fiches candidats qui en
  ont, avec la mention « hors classement » ; copie du résumé dans `data/observatoire.json`,
  rafraîchie par `pages.yml`. Liens des pages sujets vers `/sujets/<famille>/`.
- Vercel Web Analytics : balise ajoutée (pages fixes et application) ; à activer dans le projet
  Vercel `votona-observatoire`. 80 tests OK. En préproduction.

## 2026-10-28 (soir, suite) — En production, indexation ouverte

- Mise en production : Observatoire (`main` avancé sur `preprod`) et Votona (fusion `draft` → `main`).
- Indexation ouverte (`INDEXABLE = True`) : plus de balise noindex en production, `robots.txt`
  ouvert avec le plan du site. La préproduction reste en noindex (en-tête `vercel.json`).
- Conformité mise en veille (décision du porteur) jusqu'à un trafic important ; voir
  `docs/conformite.md`. 79 tests OK.
- Suite : déclarer le site dans Google Search Console et Bing Webmaster Tools.

## 2026-10-28 (soir) — Méthodes réunies : deux onglets communs aux deux sites

- `/methode/` de l'Observatoire et de votona.fr ouvrent sur les mêmes onglets « Le test Votona » |
  « L'Observatoire » ; chaque page reste sur son domaine. Même en-tête (mascotte, titre, chapeau),
  sommaire en pastilles, même largeur que la page de Votona ; ancres sur chaque section.
- Vue Méthode de l'application : mêmes onglets. 79 tests OK.
- En préproduction (preview.observatoire.votona.fr) et sur le `draft` de Votona ; mise en
  production à la demande.

## 2026-10-28 (après-midi) — Compte dans la barre, conformité, interrupteur d'indexation

- Barre du haut de l'Observatoire : icône « Mon compte » (vers le compte Votona), comme sur Votona.
- Conformité (étape 1) : `docs/conformite.md` (état de la liste du cadrage, registre de
  traitement, projet d'AIPD, licences des sources à compléter, user-agent à décider) ; page
  « Vous êtes cité ? » (`/vous-etes-cite/`, pied de page et Méthode) ; côté Votona (branche
  `draft`) : sections Observatoire dans les mentions légales, la confidentialité (personnalités
  citées : finalité, base légale, sources, droits, délais) et À propos. À relire par le porteur,
  idéalement avec un avocat.
- Indexation (étape 2) préparée : interrupteur `INDEXABLE` (encore `False`), noindex par en-tête
  limité aux domaines hors production, robots.txt et balises liés à l'interrupteur ; tests.
- En préproduction ; 224 liens internes vérifiés ; tests : 79.

## 2026-10-28 — En production : pages fixes, couleurs des candidats, nom actuel des partis

- À la demande du porteur, mise en production de la préproduction : pages par candidat,
  personnalité, parti et sujet, couleurs des candidats (Votona), noms de partis.
- Partis renommés : affichés partout sous leur **nom actuel** (Rassemblement national pour le
  FN, Renaissance pour EM/LREM), c'est la même organisation. Le nom à la date reste dans
  l'export (`name_at_date`, `short_name_at_date`) et dans les données ouvertes
  (`party_name_at_date`). Méthode mise à jour.
- Base locale reconstruite depuis data/store avant export (627 déclarations, comme la routine).
  Vérifié : aucune mention « FN » / « LREM » affichée, 223 liens internes, aucun cassé. Tests : 77.

## 2026-10-28 — Routine quotidienne (3e passage, après ajout de l'identifiant Supabase)

- **Supabase : accès fonctionnel.** `supabase_sync apply` : 0 décision de l'admin Votona à appliquer. `supabase_sync push` : déposé dans l'onglet « Observatoire » — 0 verdict, 0 attribution, 2 partis, 7 sources. Ancienne page : aucune décision en attente, non utilisée pour le dépôt.
- Candidats : synchronisation avec https://votona.fr/ (0 ajouté, 0 modifié, 0 absent) ; 2 à confirmer : Selma Labib, Antoine Mikolajczak.
- Collecte : google_factcheck 24 récupérées / 0 nouvelle ; datacommons_feed 4 / 0 nouvelle. Aucune erreur de connecteur.
- Base : 7 591 vérifications ; claims : auto_sure 454, validated 173, to_review 0, rejected 6 894.
- Exportées : 627 entrées (inchangé). rating_map.csv inchangé.
- Part de verdicts positifs (toutes vérifications) : TF1 Info 20,1 %, franceinfo 29,0 %, Poligraph 20,8 %, AFP Factuel 0,4 % (échelle partielle), Décodeurs 1,6 % (partielle), 20 Minutes 11,0 %, CheckNews 0 % (partielle).
- Alertes : aucune. 73 tests réussis. Beta republiée (artefact, version 12) ; site statique et flux régénérés.

## 2026-10-28 — Routine quotidienne (2e passage, lancement manuel)

- Candidats : synchronisation avec https://votona.fr/ (0 ajouté, 0 modifié, 0 absent) ; 2 à confirmer : Selma Labib, Antoine Mikolajczak.
- **Supabase : accès refusé** (`supabase_sync apply` et `push` : « identifiant API Supabase manquant dans l'environnement Observatoire »). Les files n'ont donc pas pu être déposées dans l'onglet « Observatoire » de l'admin Votona ; repli sur l'ancienne page.
- Décisions (ancienne page, 62 documents) : 61 appliquées (0 libellé, 1 attribution, 60 partis), 0 ignorée ; documents supprimés de la collection « decisions ». Aucune décision de l'admin Votona (Supabase inaccessible). rating_map.csv inchangé.
- Collecte : google_factcheck 24 récupérées / 0 nouvelle ; datacommons_feed 4 / 0 nouvelle. Aucune erreur de connecteur.
- Base : 7 591 vérifications ; claims : auto_sure 454, validated 173, to_review 0, rejected 6 894.
- Exportées : 627 entrées (626 la veille).
- Files de validation : 0 verdict, 0 attribution, 2 partis ; déposées sur l'ancienne page uniquement. Part de verdicts positifs (toutes vérifications) : TF1 Info 20,1 %, franceinfo 29,0 %, Poligraph 20,8 %, AFP Factuel 0,4 % (échelle partielle), Décodeurs 1,6 % (partielle), 20 Minutes 11,0 %, CheckNews 0 % (partielle).
- Alertes : aucune hors accès Supabase. 73 tests réussis.
- Beta republiée (artefact, version 11) ; site statique et flux régénérés.

## 2026-10-28 — Back-office dans l'admin Votona

- Décision du porteur : le back-office devient un onglet « Observatoire » de l'admin Votona,
  visible seulement connecté avec le compte admin.
- Supabase (projet Votona) : tables `obs_queues` et `obs_decisions`, RLS réservée à l'email
  admin (même règle que `relance_news_queue`). Aucune nouvelle alerte de sécurité.
- `pipeline/supabase_sync.py` (push / apply, tests) : les décisions s'appliquent sur les files
  vues par l'admin. Corrige au passage un défaut : l'ancienne application lisait des files
  locales non versionnées.
- Votona (branche `draft`) : onglet « Observatoire » (élément à traiter, choix, suite de la file,
  historique avec annulation, suivi des rédactions) ; écran renommé « Administration ».
  Testé dans le navigateur avec les vraies files (ordinateur et mobile). Production sur demande.
- Routine mise à jour : Supabase d'abord, ancienne page en repli tant que l'identifiant API
  « Supabase » n'est pas ajouté à l'environnement « Observatoire » (action du porteur).
- Incident clos : une fonction temporaire d'écriture créée pour charger les files a été refusée
  par la protection de la session, puis supprimée par le porteur (vérifié : 0 restante).

## 2026-10-28 — Routine quotidienne

- Candidats : synchronisation avec https://votona.fr/ (0 ajouté, 0 modifié, 0 absent) ; 2 à confirmer : Selma Labib, Antoine Mikolajczak.
- Collecte : google_factcheck 29 récupérées / 9 nouvelles ; datacommons_feed 4 / 0 nouvelle. Aucune erreur de connecteur.
- Décisions du tableau de validation : 354 documents rapatriés, 353 appliquées (22 libellés, 113 attributions, 218 partis), 0 ignorée, documents supprimés de la collection « decisions ». **rating_map.csv modifié : 22 lignes ajoutées** (AFP Factuel : Incomplet, Presque, A nuancer, Pas que, contexte manquant, Non prouvé, missing context, Attention, Erroné, X, Propos sortis de leur contexte, Simplification trompeuse, « Il n'y a pas d'interdiction de prendre l'avion pour les vaccinés », « Le Covid tue, les vaccins protègent du Covid » ; Les Décodeurs : C'est très exagéré, C'est contestable, C'est exagéré, C'est discutable, C'est compliqué, C'est plutôt vrai ; Poligraph : Contestable, C'est très exagéré). Décisions du porteur, reprises telles quelles.
- Base : 7 591 vérifications ; claims : auto_sure 454, validated 172, to_review 1, rejected 6 894.
- Exportées : 626 entrées (data/export/facts.json ; 522 la veille), dont 229 de candidats 2027.
- Files de validation : 0 verdict, 1 attribution, 61 partis ; files déposées sur la page. Part de verdicts positifs (toutes vérifications) : TF1 Info 20,1 %, franceinfo 29,0 %, Poligraph 20,8 %, AFP Factuel 0,4 % (échelle partielle), Décodeurs 1,6 % (partielle), 20 Minutes 11,0 %, CheckNews 0 % (échelle partielle).
- Alertes : aucune. 70 tests réussis.
- Beta republiée (artefact, version 10) ; site statique et flux régénérés.
- Préproduction non mise à jour : changements en attente sur preprod.

## 2026-10-27 — Routine quotidienne

- Candidats : synchronisation avec https://votona.fr/ (0 ajouté, 0 modifié, 0 absent) ; 2 à confirmer : Selma Labib, Antoine Mikolajczak.
- Collecte : google_factcheck 25 récupérées / 0 nouvelle ; datacommons_feed 4 / 0 nouvelle. Aucune erreur de connecteur.
- Décisions du tableau de validation : aucune à rapatrier (0 appliquée, 0 ignorée). rating_map.csv inchangé.
- Base : 2 135 vérifications ; claims : auto_sure 122, validated 67, to_review 0, rejected 1 916.
- Exportées : 189 entrées (data/export/facts.json), inchangé depuis la veille.
- Files de validation : 0 verdict, 0 attribution, 51 partis ; 6 sources suivies (part de verdicts positifs, toutes vérifications : TF1 Info 15,3 %, franceinfo 23,1 %, Poligraph 17,4 %, AFP Factuel 0 % (échelle partielle), 20 Minutes 4,5 %, Décodeurs 0 % sur 4).
- Alertes : aucune. 70 tests réussis.
- Beta republiée (artefact, version 8) ; site statique et flux régénérés.

## 2026-10-27 — Historique 2017-2024 : 189 → 522 déclarations publiées

- Rattrapage `run_daily --connector google_factcheck --days 3587` (depuis le 1er janvier 2017) :
  7 562 vérifications récupérées, 5 463 nouvelles (dont Les Décodeurs 2017-2021 et CheckNews
  2020-2023, absents jusqu'ici). Base : 7 582 vérifications ; claims auto_sure 455, validated 67,
  to_review 113, rejected 6 883 (surtout des rumeurs virales, jamais publiées).
- Export : **522 déclarations** (189 avant), dont 208 de **20 candidats 2027** sur 38
  (Le Pen 35, Mélenchon 25, Bardella 25, Philippot 17, Attal 16, Dupont-Aignan 16, Zemmour 13…).
- Files de validation : la file des libellés ne montre plus que ceux qui touchent une
  déclaration attribuée (23 au lieu de 484 ; ceux des rumeurs ne changent rien à ce qui est
  publié). Attributions et partis : candidats 2027 en tête (21 et 63 éléments), puis du plus
  récent au plus ancien. Files déposées sur la page de validation. rating_map.csv non modifié.
## 2026-10-27 — Une vraie page par candidat, personnalité, parti et sujet

- `pipeline/build_pages.py` (lancé par `build_beta`, donc par la routine) : pages HTML fixes
  `/candidats/<id Votona>/` (38, mêmes identifiants que votona.fr), `/personnalites/<nom>/`,
  `/partis/<sigle>/`, `/sujets/<famille>/`, pages d'index, `/methode/`, `sitemap.xml` ; titre,
  description, adresse canonique, image de partage (`web/beta/og.jpg`), fil d'Ariane (données
  structurées BreadcrumbList). Lisibles sans JavaScript ; feuille de style extraite du gabarit
  (`site/assets/observatoire.css`), donc même rendu que l'app. « Signaler une erreur » sans script.
- 136 pages, 113 au plan du site (candidat sans vérification : page publiée, hors plan, comme
  sur Votona). Toujours `noindex` (constante `INDEXABLE`) jusqu'au feu vert conformité.
- L'app (site) envoie vers ces pages (personne, parti, sujet, Méthode) ; les anciennes adresses
  `#personne-…`, `#candidat-lepen` (liens de votona.fr) redirigent. Dans l'artefact, tout reste
  dans l'app. Adresses des homonymes stables (ordre nom puis identifiant).
- Vérifié dans le navigateur : 138 liens internes, aucun cassé ; pas de débordement sur mobile.
  Tests : 73 passent. Poussé sur `preprod` seulement.

## 2026-10-26 (fin de journée) — Même largeur que Votona, violet foncé dans le bandeau

- Largeurs : l'Observatoire comptait les marges en plus de la largeur (contenu 880 px au lieu
  de 800, bandeau 1 260 au lieu de 1 180). Corrigé (`box-sizing: border-box`) : mesures
  identiques à Votona à 1 440 px (bandeau 1 180, contenu 800).
- Bandeau : violet foncé #7C3AED (`--masthead-accent`) pour « PRÉSIDENTIELLE 2027 » /
  « OBSERVATOIRE », le trait du bas et les survols, y compris en mode sombre, sur les deux sites
  (Votona : index.html et pages générées). Étiquette « BÊTA » lisible en mode sombre.

## 2026-10-26 (après-midi) — Une seule identité Votona / Observatoire, lien dans la barre de Votona

- **Votona** (en production à la demande du porteur) : lien « Observatoire » dans la barre du haut
  de l'app (écrans d'accueil, tableau de bord, compte ; pas pendant le questionnaire) et de toutes
  les pages générées ; icône seule sous 480 px. Liens vers l'Observatoire dans le même onglet.
- **Observatoire** aligné sur Votona : bandeau `header.topbar` identique (même largeur 1180 px,
  marges, lavande y compris en mode sombre, mascotte, « Votona » + « OBSERVATOIRE » en Plex Mono),
  lien « Le test 2027 » symétrique, icône « ? » pour la Méthode (comme la FAQ de Votona), onglets
  sous le bandeau ; boutons `.btn-accent` / `.btn-ghost` de Votona ; pied de page `.gfoot`
  (pages légales et réseaux de Votona) ; couleurs et accessoires des 7 familles (`web/beta/props/`,
  copiés de Votona) sur les tuiles et pages sujets ; appel « Faire le test » sur l'accueil.
- Ergonomie : cartes de l'accueil plus courtes (détail dans Faits vérifiés), chiffres clés en deux
  colonnes et onglets courts sur mobile, « OBSERVATOIRE » toujours visible ; corrigé un conflit de
  classe CSS (`.tag`) qui donnait un fond à l'étiquette du logo.

## 2026-10-26 — Mise en ligne, routine réparée, liens Votona sur draft

- **Routine** : le porteur a ajouté le dépôt (écriture) à la routine Observatoire et `votona.fr`
  aux domaines autorisés de l'environnement « Observatoire ». Test lancé à 10h16 : réussi (voir
  entrée suivante) ; accès à votona.fr vérifié (38 candidats lus). La routine Votona n'est pas
  modifiée : deux boucles, deux environnements, deux dépôts.
- **Hébergement** : projet Vercel `votona-observatoire` (équipe Votona) ; `observatoire.votona.fr`
  (production, `main`) et `preview.observatoire.votona.fr` (branche `preprod`) vérifiés, CNAME
  chez OVH ; déploiements prêts. Protection Vercel « Standard » : les domaines personnalisés,
  préproduction comprise, restent publics (mais en noindex).
- **Liens Votona → Observatoire** : `OBSERVATOIRE_URL` renseignée et pages régénérées sur la
  branche `draft` de Votona (38 candidats, 37 sujets, inchangés). Passage sur `main` (votona.fr)
  uniquement à la demande du porteur.

## 2026-10-26 — Routine quotidienne

- **Candidats** : synchronisation non faite (votona.fr inaccessible depuis la routine : proxy 403 ; pas de clone votona). Liste inchangée.
- **Collecte** : google_factcheck 38 récupérées / 16 nouvelles ; datacommons_feed 4 / 0. Aucune erreur de connecteur.
- **Décisions du tableau** : aucune (0 appliquée, 0 ignorée). rating_map.csv non modifié.
- **Claims** : auto_sure 122, validated 67, rejected 1 916, to_review 0. Base : 2 135 vérifications.
- **Export** : 189 déclarations (188 à la dernière entrée), fichiers data/export/ régénérés. Pas d'alerte d'export.
- **Files de validation** : verdicts 0, attributions 0, partis 51, sources 6 (déposées dans le tableau).
- **Part de verdicts positifs (vrai + plutôt vrai)** : TF1 Info 15,3 % (875) ; franceinfo Vrai ou Fake 23,1 % (121) ; Poligraph 17,4 % (46) ; AFP Factuel 0 % (780) ; 20 Minutes Fake Off 4,5 % (309) ; Les Décodeurs 0 % (4).
- **Beta** : régénérée (189 déclarations) et republiée (artefact version 5). Tests : 70 passent.

## 2026-10-22 — Onglets sans redondance, sujets, recoupement, données ouvertes, préprod/prod

**Demande du porteur** : contenu des onglets redondant ; enrichir pour se démarquer de Poligraph ;
relier Votona et l'Observatoire sans les confondre ; hébergement préprod + prod.

- **Architecture de la beta** : Accueil (chiffres clés, couverture des candidats 2027, dernières
  vérifications, tuiles par sujet, ce qui distingue l'Observatoire ; plus de barre de filtres) ;
  **Faits vérifiés**, seul écran à filtres complets (+ sujet, + « vérifié par plusieurs
  rédactions ») ; Personnalités (onglets Candidats 2027 / Toutes, recherche) ; Partis (partis des
  candidats d'abord, répartition en barre) ; **Sujets** (nouveau) ; Méthode. Les fiches personne,
  parti et sujet n'ont plus de filtres : un lien « Filtrer ces faits » ouvre Faits vérifiés
  pré-filtré. « Faire le test Votona » dans le bandeau.
- **Sujets** : `data/seeds/themes.csv` (37 sujets de Votona + 7 familles, mots-clés à la main),
  `pipeline/themes.py` ; l'export ajoute `theme` et `votona_topics` à chaque fait (indicatif,
  jamais un jugement). 137/188 faits ont une famille, 73 un sujet de Votona.
  **Angles morts** : 17 des 37 sujets de Votona sans aucune vérification pour les candidats 2027
  et leurs partis.
- **Recoupement** : badge « Vérifié par N rédactions » (28 faits), « Verdicts divergents » quand
  les rédactions ne placent pas la déclaration au même niveau ; aucun arbitrage.
- **Données ouvertes** (site seulement) : `site/donnees/facts.json`, `facts.csv` (une ligne par
  vérification), flux RSS `site/flux.xml` (50 dernières).
- **Liens Votona** : voir [liens-votona.md](liens-votona.md). Routes entrantes `#candidat-<id>` et
  `#sujet-<famille>`. Côté Votona, branche `claude/liens-observatoire` (constante
  `OBSERVATOIRE_URL` vide : pages générées inchangées, vérifié).
- **Hébergement** : `preprod` → preview.observatoire.votona.fr, `main` → observatoire.votona.fr,
  tous deux en noindex jusqu'au feu vert conformité ([hebergement.md](hebergement.md)). La routine
  commite les données sur `main` et avance `preprod` seulement en avance rapide.
- Tests : 70 passent. rating_map.csv non modifié.

**Suite** : le porteur configure Vercel (deux domaines) et le DNS OVH, et ajoute le dépôt à la
routine ; Science Feedback comme source ; module B finances publiques.

## 2026-10-21 (soir) — Votona Observatoire : liste commune, charte, vue 2027, site

**Décisions du porteur** : nom **Votona Observatoire** ; mise en avant des candidats 2027 et de
leurs partis ; site sur un sous-domaine de votona.fr, d'abord en préproduction.

- Analyse du dépôt `wvernay42-star/votona` (lecture seule) : site statique Vercel, `draft` →
  votona.vercel.app, `main` → votona.fr ; charte : fond crème #fbfaf7, encre #191d2b, violet
  #7C3AED, bandeau #F6F2FE souligné de violet, Baloo 2 / Work Sans / IBM Plex Mono, largeur 880 px,
  mascotte ourson, charte de neutralité des intitulés.
- **Liste commune** `data/seeds/candidates_2027.csv` : 38 candidats de Votona (5 retirés), 36 reliés
  à Wikidata (Labib et Mikolajczak « à confirmer » ; Mathieu et Markovic sans fiche Wikidata),
  23 reliés à un parti du référentiel. Les candidats absents des fonctions suivies (Arthaud,
  Kazib, Branco, Polony…) rejoignent le référentiel d'attribution.
- **Beta** : charte Votona appliquée ; vue « Candidats 2027 » (38 fiches, ordre alphabétique du
  nom, « aucune vérification publiée à ce jour » affiché tel quel, lien vers les positions sur
  Votona) ; sélecteur de périmètre Candidats 2027 / Leurs partis / Toute la vie politique
  (défaut : candidats) ; badge et lien Votona sur les fiches ; méthodologie : les vérifications
  n'entrent jamais dans le classement de Votona. Contact : contact@votona.fr.
- 188 déclarations, dont 65 de 15 candidats.
- **Synchronisation** `pipeline/sync_candidates.py` : Votona est la source de la liste (ajouts,
  retraits) ; jamais de suppression ; la routine du matin la lance (dépôt Votona en lecture seule).
- **Site** : `site/` + `vercel.json` (noindex) + `.vercelignore`, procédure dans `docs/hebergement.md`
  (préproduction `preview.observatoire.votona.fr`, puis `observatoire.votona.fr`).

## 2026-10-21 (fin d'après-midi) — couverture de l'API Google au-delà des 8 rédactions

Recherche par nom de 360 personnalités (gouvernement, présidents, chefs de parti + personnes
déjà exportées), toutes rédactions, langue fr, 2 ans : 337 vérifications uniques, dont ~90 % déjà
couvertes par nos sources (TF1 Info 166, franceinfo 47, AFP 48, Poligraph 35, 20 Minutes 7).
Non suivies : DE FACTO (20, observatoire collectif qui reprend des vérifications de ses membres,
dont l'AFP → risque de doublons), dpa-factchecking (9, surtout réseaux sociaux), Science Feedback (2,
dont une déclaration de Jordan Bardella), RTBF (2, Belgique). Le Monde, Libération et Les Surligneurs
ne déclarent pas leurs vérifications à Google.
Pistes : ajouter Science Feedback ; un balayage hebdomadaire par nom pour repérer les nouvelles
rédactions (rapport, jamais d'ajout automatique) ; DE FACTO seulement avec dédoublonnage par URL d'origine.

## 2026-10-21 (après-midi) — validations appliquées, partis datés, suivi des sources

**Validations du porteur** : 144 décisions appliquées (12 libellés, 75 attributions, 57 partis
dont 6 « sans étiquette »), aucune ignorée. rating_map.csv : 12 lignes ajoutées (decided_by = human) :
« En partie vrai » TF1 Info et Poligraph → à moitié vrai ; « En partie vrai » 20 Minutes → plutôt vrai ;
« C'est plus compliqué » franceinfo et Poligraph → à moitié vrai ; « Infondé » AFP → faux ;
« Partiellement faux », « Vidéo manipulée », « Photo manipulée » AFP et « FAUSSE LÉGENDE » Décodeurs
→ plutôt faux ; « Image générée par IA » et « 1 » AFP → non classable.
→ 186 déclarations exportées (80 personnalités) : vrai 23, plutôt vrai 31, à moitié vrai 42,
plutôt faux 47, faux 38, non classable 5.

**Partis selon la date** (demande du porteur) :
- Contrôle d'existence : une affiliation (Wikidata ou manuelle) n'est jamais retenue avant la
  création du parti ni après sa dissolution (parties.csv : colonnes inception / dissolved).
  Cas trouvé : 2 validations « UMP » pour Laurent Wauquiez en 2024-2025 (UMP dissoute en 2015) →
  écartées, de retour en file. Le tableau ne propose plus que des partis existant à la date.
- Noms à la date : `party_names.csv` (noms officiels datés, Wikidata P1448) et
  `party_names_manual.csv` (sigles FN, EM, LREM complétés à la main) : FN avant le 1/06/2018,
  En marche ! → LREM (8/05/2017) → Renaissance (22/09/2022).
- `python -m pipeline.referential --parties-only` met à jour cet historique sans tout reconstruire.

**Corrections** : « sans étiquette » validé ne revient plus en file ; l'alerte « connecteur muet »
compte des jours (3) et non des exécutions.

**Module A, suivi des sources** (onglet du tableau de validation) — part de vrai/plutôt vrai sur
les déclarations de personnalités : TF1 Info 35 % (104), franceinfo 30 % (60), Poligraph 21 % (28),
AFP 0 % (23). 20 Minutes : aucune déclaration de personnalité.

**Décisions du porteur** : capacité de validation ≈ 100 éléments par jour ; thème pilote du
module B (V2) : finances publiques.

## 2026-10-22 (suite 3) — beta publique en ligne

- Page de la beta : https://claude.ai/artifact/19UnNBtaqC927nk4tZR419 (privée tant qu'elle
  n'est pas partagée depuis le menu Partager). Gabarit `web/beta/template.html` (maquette A),
  page générée `web/beta/index.html` par `python -m pipeline.build_beta` (export embarqué).
- Écrans : accueil (compteurs + dénominateur + mention de périmètre), faits vérifiés, personnalités
  (ordre alphabétique, aucun classement), partis, fiche personne (frise), fiche parti,
  méthodologie (principes, sources, échelle, limites, contestation sous 48 h).
- Filtres : période (7 j, 30 j, 12 mois, année, personnalisée), date de déclaration / de
  vérification, pays, parti, personne, source, verdicts. Liens partageables seulement par vue
  (#faits, #personne-Q…, #parti-Q…) : les filtres ne passent pas dans l'adresse (limite des artefacts).
- « Signaler une erreur » : affiche l'adresse de contact et la référence de l'entrée, avec copie.
- Dédoublonnage : fenêtre élargie à ±10 jours quand une date est une date de repli
  (cas Le Pen logement social : 3 vérifications regroupées, Panot « Octobre rose » : 2).
  119 déclarations exportées.
- La routine du matin régénère et republie la beta (étape ajoutée à la tâche planifiée).

## 2026-10-22 (suite 2) — routine quotidienne planifiée

- Tâche planifiée « Routine quotidienne Observatoire » (id `trig_012mCuwXsnbSw8LrjxuAjyhN`),
  chaque jour à 5 h 59 (heure de Paris), première exécution le 22/10/2026.
- Chaque exécution démarre une nouvelle session cloud qui : rattache et clone le repo,
  applique les décisions du tableau de validation, lance `run_daily`, redépose les files,
  lance les tests, ajoute une entrée « Routine quotidienne » à ce journal, commite et pousse.
- Aucun connecteur claude.ai n'est nécessaire (API Google via le secret réseau de
  l'environnement, base de la page via les outils d'artefact).

## 2026-10-22 (suite) — tableau de validation en ligne

- Page privée : https://claude.ai/artifact/At6BYDaT6SbwLv5P2LuSLU (option A retenue).
  Base partagée : `queues` (déposées par Claude) et `decisions` (écrites par la page,
  réservées aux éditeurs — vérifié : un simple lecteur ne peut pas écrire).
- `pipeline/validation_sync.py` : `seed` (prépare les files) et `apply` (écrit les décisions
  dans rating_map.csv, attributions.csv, affiliations_manual.csv ; idempotent).
- Les partis validés à la main sont prioritaires sur Wikidata à la date validée seulement.
- Files déposées : 12 libellés, 75 attributions, 60 partis. Procédure : docs/validation.md.

## 2026-10-22 — plus de déclarations exactes : historique 2 ans + Poligraph

**Demande du porteur** : recueillir davantage de déclarations vérifiées « vraies » (sans jamais
modifier un verdict). Recherche par nom de 30 personnalités sur 2 ans dans l'API Google :
TF1 Info (26 vrai/plutôt vrai sur 99) et franceinfo (13 sur 35) vérifient beaucoup de
déclarations exactes ; l'AFP quasiment jamais ; Poligraph (non suivi jusque-là) publie toute l'échelle.

**Décisions** : Poligraph ajouté (`poligraph_fr`, full_scale = 1, licence à vérifier) avec les
règles du cadrage dans `rating_map.csv` (signalé : 16 lignes ajoutées pour cette source) ;
historique de collecte porté à 2 ans (`--days 730`).

**Résultat** : 2 116 vérifications ; 122 déclarations exportées (51 personnalités) ;
verdicts : plutôt faux 35, faux 27, plutôt vrai 15, vrai 12, non classable 33 (surtout
« En partie vrai » ×80 et « C'est plus compliqué » ×37 en attente) ; file : 75 attributions,
60 partis, 12 libellés.

**À garder en tête** : les fact-checkers choisissent ce qu'ils vérifient (souvent les propos
douteux) ; même avec ces sources, la répartition ne mesure pas la sincérité globale d'une
personne. D'où la mention obligatoire du module C.

## 2026-10-21 (nuit, suite) — dédoublonnage, routine quotidienne, export

**Question du porteur : « trop peu de vrais »**. Les verdicts ne sont pas modifiables (règle 1).
Analyse : l'écart vient des rumeurs virales (AFP, 20 Minutes : 180 faux / 4 vrais sur 211),
qui ne sont rattachées à personne et ne seront jamais affichées. Sur les 31 déclarations de
personnalités : 6 vrai/plutôt vrai, 14 faux/plutôt faux, 11 intermédiaires en attente de
validation (« En partie vrai », « C'est plus compliqué »). Leviers légitimes : valider ces
libellés, ajouter des sources à échelle complète (module A), afficher le dénominateur (module C).

**Code** :
- `normalize.py` : dates à leur précision, horodatages UTC ramenés au jour de Paris
  (« 2026-10-12T22:00:00Z » = 13 octobre), repli sur la date de vérification.
- `dedupe.py` : même personne, ±3 jours, similarité ≥ 80, ou ≥ 55 avec les mêmes chiffres
  (cas Le Pen 13/09, « 70 % éligibles / 11 % » formulé différemment par franceinfo et TF1 Info).
  Verdict d'un claim = le plus fréquent ; égalité → non classable.
- `run_daily.py` : collecte depuis le dernier succès − 7 jours, upsert par URL, claims recalculés
  à chaque fois (idempotent), validations manuelles appliquées
  (`data/validations/attributions.csv`, `data/seeds/affiliations_manual.csv`, `rating_map.csv`),
  files de validation dans `data/review_queue/*.json`, alerte après 3 exécutions sans nouveauté.
- `export.py` : `data/export/facts.json` + `stats.json` (par personne, parti, pays, mois).

**Exécution réelle** (`python -m pipeline.run_daily --days 90`) :
- 246 vérifications (Google 242, Data Commons 4), 2ᵉ exécution : 0 nouvelle (idempotence OK).
- Claims : 24 exportés (`auto_sure`), 6 attributions à valider, 215 écartés.
- Verdicts exportés : non classable 9 (en attente de libellé), plutôt faux 7, faux 4, vrai 2,
  plutôt vrai 2. Parti sûr pour 15 entrées sur 24.
- File de validation : 6 attributions, 9 partis, 7 libellés.

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
