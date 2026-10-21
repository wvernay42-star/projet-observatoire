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
