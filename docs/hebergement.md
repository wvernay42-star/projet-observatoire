# Mise en ligne : Votona Observatoire

## Adresses

Votona est en production sur **votona.fr** (Vercel, domaine chez OVH). L'Observatoire vit sur un
sous-domaine de votona.fr :

| Étape | Adresse | Indexation |
|---|---|---|
| Préproduction (beta) | `preview.observatoire.votona.fr` | bloquée (`noindex`, robots.txt) |
| Production (plus tard) | `observatoire.votona.fr` | ouverte, après la liste de conformité du cadrage |

(Un sous-domaine de votona.fr s'écrit `observatoire.votona.fr` ; `votona.observatoire.fr`
supposerait de posséder `observatoire.fr`.)

## Ce que contient le dépôt

- `site/` : le site statique servi (page + logo + favicon + robots.txt), régénéré par
  `python -m pipeline.build_beta` à chaque routine quotidienne, puis commité sur `main`.
- `vercel.json` : sert `site/` sans étape de build, en-tête `X-Robots-Tag: noindex` pendant la beta.
- `.vercelignore` : seul `site/` part chez Vercel (le pipeline et les données brutes restent privés).

## À faire une fois (par le porteur du projet)

1. **Vercel** (même compte que Votona) : *Add New… → Project*, importer le dépôt GitHub
   `wvernay42-star/projet-observatoire`. Framework : *Other*. Laisser Build Command vide,
   Output Directory : `site`. Nom du projet : `votona-observatoire`.
2. **Domaine** : dans le projet Vercel, *Settings → Domains → Add* :
   `preview.observatoire.votona.fr`, rattaché à la branche `main`.
3. **DNS chez OVH** (zone votona.fr) : ajouter un enregistrement
   `CNAME  preview.observatoire  →  cname.vercel-dns.com.`
   (Vercel affiche la valeur exacte à recopier). Attendre la validation (quelques minutes à 1 h).
4. Facultatif : *Settings → Deployment Protection* pour protéger la préproduction par mot de passe
   ou par compte Vercel.

Ensuite, chaque push sur `main` (dont la routine de 6 h) redéploie automatiquement.

## Passage en production (plus tard)

1. Cocher la liste « Conformité » de `docs/cadrage.md` (RGPD, licences, avis d'avocat).
2. Retirer `noindex` : en-tête de `vercel.json`, balise `<meta name="robots">` et `robots.txt`
   générés par `pipeline/build_beta.py`.
3. Ajouter le domaine `observatoire.votona.fr` (CNAME `observatoire` → `cname.vercel-dns.com.`).
4. Ajouter les liens depuis votona.fr (fiches candidats, pages sujets) : travail dans le dépôt
   Votona, sur sa branche `draft` d'abord, comme le veut son CLAUDE.md.
