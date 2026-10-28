# Décisions

## 2026-10-21

- **Maquette retenue : variante A « Jauge »** (codes PolitiFact, version sobre).
  Canevas : https://claude.ai/artifact/E3tCfPbN3JGAx9bwgVSJxo — sources des écrans dans `web/maquettes/`.
  - Typo : Source Serif 4 (titres, affirmations) + Inter (interface).
  - Bandeau bleu nuit `#1B3A5C`, fond blanc, texte `#1A1A1A`, gris secondaire `#5F6368`.
  - Échelle des verdicts (jamais rouge/vert) : Vrai `#1F5FA8` · Plutôt vrai `#9DC0E6` ·
    À moitié vrai `#CFC8BA` · Plutôt faux `#F2B57E` · Faux `#B4500A` ·
    Non classable = hachures grises, bordure pointillée.
  - Chaque verdict : jauge 5 crans + niveau normalisé + « libellé d'origine » selon la source.
- **Validation humaine** : page web interne (onglets Attributions / Verdicts), validée par le porteur du projet.
  Maquette : `web/maquettes/Validation.dc.html`.
- **Périmètre des personnes** : tout le monde à affiliation publique (députés, sénateurs, eurodéputés,
  gouvernement, chefs de parti, élus locaux inclus).
- **User-agent du robot** : `g.nevert/0.1 (…; +mailto:guillaume.nevert@outlook.com)` (voir `.env.example`).
- **Nom** : provisoire ; le repo `projet-observatoire` sera renommé avec le nom du site.

## Constats sur les données

- Flux Data Commons : seulement 89 fact-checks FR (2017–2020). Insuffisant seul : le crawler JSON-LD
  des sites français est indispensable (accès réseau à ouvrir dans l'environnement cloud).
- Les Surligneurs publient une phrase explicative au lieu d'un verdict court → « Non classable »
  sauf règle dédiée (leur `ratingValue` est à étudier).

## 2026-10-21 (après-midi)

- Capacité de validation humaine : environ 100 éléments par jour (porteur du projet).
- Module B (V2) : thème pilote **finances publiques**.
- Parti affiché = affiliation datée en vigueur à la date de la déclaration, dans la période
  d'existence du parti, sous le nom qu'il portait à cette date.

## 2026-10-21 (soir)

- Nom : **Votona Observatoire**, même famille que Votona (votona.fr).
- Périmètre affiché par défaut : candidats à la présidentielle 2027 (liste commune avec Votona),
  puis leurs partis, puis toute la vie politique ; la base complète est conservée.
- Les vérifications n'entrent jamais dans le classement de Votona.
- Hébergement : Vercel, préproduction `preview.observatoire.votona.fr` (noindex), production
  `observatoire.votona.fr` après la liste de conformité.

## 2026-10-22
- Un seul écran à filtres complets (Faits vérifiés) ; les autres vues entrent par une personne, un
  parti ou un sujet.
- Thème des faits : familles et sujets de Votona, par mots-clés relus à la main, affiché comme
  indicatif. Il sert de passerelle vers Votona et à montrer les angles morts, jamais à qualifier.
- Divergence entre rédactions signalée telle quelle, sans arbitrage.
- Données ouvertes (JSON, CSV, RSS) : métadonnées seulement, comme l'export.
- Deux environnements : `preprod` (préproduction) et `main` (production), noindex partout jusqu'à
  la liste de conformité. Fusion `preprod` → `main` sur demande explicite du porteur.
- Liens Votona → Observatoire préparés derrière une constante vide, activés quand le domaine
  de production répond.

## 2026-10-26
- Une seule identité : l'Observatoire reprend tel quel le bandeau, les boutons, le pied de page et
  les couleurs de familles de Votona ; seul le mot « OBSERVATOIRE » et l'échelle des verdicts
  (bleu → orange) le distinguent. Liens entre les deux sites dans le même onglet.
- Pages légales communes (celles de votona.fr) : à compléter pour mentionner l'Observatoire avant
  l'ouverture au référencement.

## 2026-10-28
- Back-office : onglet « Observatoire » de l'admin Votona (choix du porteur), données dans la
  base Supabase de Votona, réservées à l'email admin. La page Claude de validation devient un repli.
