# Liens entre Votona et Votona Observatoire

Deux outils distincts, une même famille : Votona (test et positions des candidats, votona.fr) et
l'Observatoire (vérifications des fact-checkers, observatoire.votona.fr). Règle commune : **les
vérifications n'entrent jamais dans le classement de Votona**, et l'Observatoire n'interprète
aucune position. Les liens orientent, ils ne mélangent pas les contenus.

## Observatoire → Votona (en place)

- Bandeau du haut : « Faire le test Votona ».
- Fiche personnalité d'un candidat 2027 et liste des candidats : « Ses positions sur Votona ».
- Chaque fait relié à un sujet du test : « Positions des candidats sur Votona »
  (votona.fr/sujets/<slug>/, sujet attribué par mots-clés, `data/seeds/themes.csv`).
- Page Sujets : familles de Votona, sujets sans aucune vérification (« angles morts ») avec lien
  vers la page sujet de Votona.

## Votona → Observatoire (prêt, désactivé)

Dépôt votona, branche `claude/liens-observatoire` (ni `draft` ni `main`) :
`scripts/generate-candidate-pages.js`, constante `OBSERVATOIRE_URL` (vide = aucun lien, pages
générées identiques au bit près).
- Fiche candidat `candidats/<id>/` : « Ses déclarations vérifiées par les rédactions de
  fact-checking : Votona Observatoire ↗ » → `observatoire.votona.fr/#candidat-<id Votona>`.
- Page sujet `sujets/<slug>/` : lien vers la famille du sujet → `#sujet-<famille>`.

Mise en service, quand observatoire.votona.fr répond : renseigner `OBSERVATOIRE_URL`, relancer le
générateur, pousser sur `draft` pour test, puis `main` sur demande explicite (règles du CLAUDE.md
de Votona). Aucune routine de Votona n'est à modifier : la veille quotidienne ne touche pas au
générateur, et l'Observatoire relit la liste des candidats de Votona sans jamais y écrire.

## Adresses stables de l'Observatoire (à ne pas casser)

`#candidat-<id Votona>`, `#sujet-<economie|social|securite|ecologie|europe|societe|defense>`,
`#personne-<QID>`, `#parti-<QID>`, `#faits`, `#sujets`, `/donnees/facts.json`,
`/donnees/facts.csv`, `/flux.xml`.
