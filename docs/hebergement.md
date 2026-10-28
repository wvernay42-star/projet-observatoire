# Mise en ligne : Votona Observatoire

## Deux environnements, comme Votona

| Branche | Adresse | Rôle | Indexation |
|---|---|---|---|
| `preprod` | `preview.observatoire.votona.fr` | test des changements de code et de présentation | bloquée |
| `main` | `observatoire.votona.fr` | production | bloquée jusqu'au feu vert (voir plus bas) |

- Tout changement de code ou de page part sur `preprod` (directement, ou depuis une branche
  `claude/...`). On ne fusionne `preprod` → `main` qu'à la demande explicite du porteur
  (« pousse en production »), comme pour Votona.
- La routine quotidienne de 6 h ne touche que les données : elle commite sur `main` (base,
  export, site régénéré), puis avance `preprod` sur `main` **seulement** si `preprod` ne contient
  aucun changement en attente (avance rapide). Sinon `preprod` garde les données de la veille
  jusqu'à la prochaine fusion.
- Votona reste séparé : `draft` → votona.vercel.app, `main` → votona.fr. Les deux projets Vercel et
  les deux dépôts sont indépendants ; ils ne partagent que le domaine votona.fr (zone DNS OVH).

(Un sous-domaine de votona.fr s'écrit `observatoire.votona.fr` ; `votona.observatoire.fr`
supposerait de posséder `observatoire.fr`.)

## Ce que contient le dépôt

- `site/` : le site statique servi (page, logo, favicon, robots.txt, données ouvertes
  `donnees/facts.json` et `donnees/facts.csv`, flux RSS `flux.xml`), régénéré par
  `python -m pipeline.build_beta`.
- `vercel.json` : sert `site/` sans étape de build, en-tête `X-Robots-Tag: noindex` partout.
- `.vercelignore` : seul `site/` part chez Vercel (le pipeline et les données brutes restent privés).

## À faire une fois (par le porteur du projet)

1. **Vercel** (même compte que Votona) : *Add New… → Project*, importer le dépôt GitHub
   `wvernay42-star/projet-observatoire`. Framework : *Other*. Laisser Build Command vide,
   Output Directory : `site`. Nom du projet : `votona-observatoire`.
   *Settings → Git → Production Branch* : `main`.
2. **Domaines** (*Settings → Domains → Add*) :
   - `observatoire.votona.fr` → production (branche `main`) ;
   - `preview.observatoire.votona.fr` → *Preview*, branche `preprod` (« Git Branch » dans la
     fenêtre d'ajout).
3. **DNS chez OVH** (zone votona.fr), deux enregistrements :
   `CNAME  observatoire  →  cname.vercel-dns.com.` et
   `CNAME  preview.observatoire  →  cname.vercel-dns.com.`
   (Vercel affiche la valeur exacte à recopier). Attendre la validation (quelques minutes à 1 h).
4. Conseillé : *Settings → Deployment Protection* → protéger les déploiements *Preview*
   (préproduction réservée au porteur et aux testeurs).

Chaque push redéploie automatiquement la branche concernée.

## Ouvrir l'indexation de la production (plus tard, sur feu vert)

Tout est prêt derrière un seul interrupteur, `INDEXABLE` dans `pipeline/build_pages.py` :
- `vercel.json` met l'en-tête `X-Robots-Tag: noindex` sur tout domaine autre que
  `observatoire.votona.fr` (préproduction et adresses *.vercel.app restent toujours fermées) ;
- avec `INDEXABLE = False`, la production est fermée par la balise `<meta name="robots">` de chaque
  page et par `robots.txt` (Disallow) ; avec `True`, les balises disparaissent et `robots.txt`
  ouvre le site et déclare `sitemap.xml`.
Ne passer à `True` qu'après la section 5 de `docs/conformite.md`, puis déclarer le site dans
Google Search Console et Bing Webmaster Tools.
