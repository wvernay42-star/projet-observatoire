# Conformité - Votona Observatoire

Dossier de travail pour le porteur et, idéalement, un avocat en droit de la presse et des données.
Il reprend la liste « Conformité » de `docs/cadrage.md` (à cocher avant l'ouverture au
référencement), avec l'état réel du projet et les preuves. Ce n'est pas un avis juridique.

État au 28/10/2026. ✅ fait · ⏳ à faire ou à valider · ⚖️ à faire relire par un avocat.

## 1. Liste du cadrage

**RGPD**

| Point | État | Où / preuve |
|---|---|---|
| Rattachement partisan limité aux affiliations publiques et sourcées | ✅ | Wikidata (P102, dates), affiliations datées seulement ; sinon validation humaine (`data/seeds/affiliations_manual.csv`, source « validation manuelle ») ; jamais le parti indiqué par l'article |
| Analyse d'impact (AIPD) rédigée | ⏳ ⚖️ | Projet en section 3 ci-dessous, à relire |
| Registre de traitement et mentions d'information | ✅ ⚖️ | Registre en section 2 ; mentions : page « Vous êtes cité ? » (`/vous-etes-cite/`), Méthode, politique de confidentialité de votona.fr (section « Votona Observatoire ») |
| Procédure de rectification et d'opposition, délai annoncé | ✅ | `contact@votona.fr`, référence d'entrée sur chaque fait ; attribution erronée retirée sous 48 h ; autres demandes sous un mois |

**Diffamation et exactitude**

| Point | État | Où / preuve |
|---|---|---|
| Aucun verdict propre ; libellé d'origine toujours visible | ✅ | Export : `rating_original` + `rating_normalized` ; affichage « « libellé » selon Rédaction » sur chaque fait |
| Lien source sur chaque entrée | ✅ | « Lire sur … » sur chaque fait, flux RSS et CSV |
| « Signaler une erreur » sur chaque entrée, retrait sous 48 h | ✅ | App et pages fixes (référence de l'entrée + adresse de contact) |
| Aucune attribution publiée sans `auto_sure` ou `validated` | ✅ | `pipeline/export.py` (`PUBLISHED`) ; homonymes et noms partiels en validation humaine |

**Licences et collecte**

| Point | État | Où / preuve |
|---|---|---|
| Conditions d'utilisation notées dans `sources.licence` | ⏳ ⚖️ | Toutes les sources sont encore « à vérifier » (voir section 4) |
| Aucune source « recherche uniquement » dans l'export | ✅ | Sources : API Google Fact Check Tools, Data Commons (CC BY) ; Fact-Check Insights exclu |
| robots.txt, débit limité, user-agent identifiant avec contact | ✅ / ⏳ | Collecte par API (pas d'aspiration de pages) ; Wikidata : 1 requête / 2 s avec user-agent identifiant. **À décider** : le user-agent porte encore l'ancien nom (« g.nevert », Observatoire de la parole politique) ; proposition : `VotonaObservatoire/1.0 (+https://observatoire.votona.fr; contact@votona.fr)` |
| Métadonnées seulement | ✅ | Titre, verdict, dates, lien ; jamais le corps des articles |

**Neutralité**

| Point | État | Où / preuve |
|---|---|---|
| Méthodologie publique, identique pour tous | ✅ | Page `/methode/` |
| Pas de classement ni de « pires » personnalités | ✅ | Listes alphabétiques ; mention « aucun classement » sur les pages Personnalités |

## 2. Registre de traitement (article 30 du RGPD)

| Rubrique | Contenu |
|---|---|
| Traitement | Votona Observatoire : recensement des vérifications de déclarations politiques |
| Responsable | William Vernay, éditeur de Votona (à titre personnel) - contact@votona.fr |
| Finalité | Informer le public sur la vérification des propos politiques en réunissant les vérifications publiées par des rédactions de fact-checking |
| Base légale | Intérêt légitime d'information du public (art. 6.1.f), liberté d'expression et d'information ; affiliation partisane : données rendues manifestement publiques par la personne (art. 9.2.e) ⚖️ |
| Personnes concernées | Personnalités politiques (élus, membres du gouvernement, candidats, responsables de parti) dont une déclaration publique a été vérifiée |
| Données | Nom ; fonction publique ; parti à la date de la déclaration ; texte de la déclaration tel que formulé par la rédaction ; verdict et libellé d'origine ; dates ; lien vers l'article |
| Sources | Rédactions de fact-checking (API Google Fact Check Tools, flux ClaimReview Data Commons) ; Wikidata ; liste des candidats de Votona |
| Destinataires | Public (site, flux RSS, données ouvertes JSON/CSV) ; administrateur (back-office) |
| Sous-traitants | Vercel (hébergement, États-Unis), Supabase (base du back-office), GitHub (dépôt de code et de données), Anthropic (assistance à la maintenance) |
| Transferts hors UE | Vercel, GitHub (États-Unis) : clauses contractuelles types des prestataires ⚖️ |
| Durée | Tant que l'information reste utile au débat public ; entrée retirée sur demande fondée |
| Sécurité | Back-office réservé à l'email admin (RLS Supabase) ; clés hors du dépôt (identifiants d'environnement) ; aucune donnée de visiteur collectée par l'Observatoire |
| Droits | Accès, rectification, effacement, limitation, opposition : contact@votona.fr ; 48 h pour une attribution erronée, un mois sinon ; réclamation CNIL |

## 3. Analyse d'impact (projet d'AIPD)

**Pourquoi une AIPD** : traitement à grande échelle portant sur des opinions politiques (affiliation
partisane), donnée sensible, rendue accessible au public. ⚖️

**Risques et mesures**

| Risque pour les personnes | Gravité | Mesures en place |
|---|---|---|
| Attribution d'une déclaration à la mauvaise personne (homonyme) | Élevée | Référentiel fermé ; correspondance exacte unique sinon validation humaine ; retrait sous 48 h |
| Mauvais parti attribué | Moyenne | Parti à la date d'après des affiliations datées ; sinon pas de parti affiché ou validation humaine ; nom actuel affiché, nom à la date dans les données ouvertes |
| Lecture d'un « score de sincérité » | Élevée | Aucun classement ; mention « sur les déclarations vérifiées, pas sur l'ensemble des propos » à côté de chaque total ; verdict de la rédaction seulement |
| Verdict déformé | Élevée | Libellé d'origine toujours visible ; conversion vers l'échelle commune validée à la main ; « non classable » si la conversion n'est pas sûre |
| Diffusion durable d'une erreur (données ouvertes, flux) | Moyenne | Corrections reprises à chaque mise à jour quotidienne du site, des fichiers et du flux |
| Confusion avec le classement de Votona | Moyenne | Les vérifications n'entrent jamais dans le classement ; mention sur les deux sites |

**Risque résiduel** : jugé limité après mesures ; à confirmer par l'avocat. ⚖️

## 4. Licences des sources (à compléter)

La collecte passe par l'API Google Fact Check Tools, qui expose le balisage ClaimReview que les
rédactions publient elles-mêmes pour les moteurs de recherche, et par le flux ClaimReview de
Data Commons (licence CC BY). Seules des métadonnées sont reprises, avec lien vers l'article.
Reste à noter, pour chaque rédaction, ses conditions de réutilisation dans
`data/seeds/sources.csv` (colonne `licence`) :

| Rédaction | Conditions vérifiées | Note |
|---|---|---|
| AFP Factuel | ⏳ | |
| Les Décodeurs (Le Monde) | ⏳ | |
| Libération CheckNews | ⏳ | |
| franceinfo Vrai ou Fake | ⏳ | |
| Les Surligneurs | ⏳ | |
| TF1 Info - Les Vérificateurs | ⏳ | |
| 20 Minutes - Fake Off | ⏳ | |
| Poligraph | ⏳ | |

Piste : un courriel aux rédactions présentant l'Observatoire (métadonnées, lien, pas de verdict
propre) vaut aussi pour la relation avec elles. ⚖️

## 5. Avant d'ouvrir le référencement

1. Relire et publier les pages légales (votona.fr : mentions légales, confidentialité, À propos ;
   Observatoire : « Vous êtes cité ? »).
2. Faire relire ce dossier (sections 2 à 4) par un avocat, ou à défaut le valider en connaissance
   de cause.
3. Décider du user-agent.
4. Alors seulement : `INDEXABLE = True` (`pipeline/build_pages.py`), en-tête `noindex` limité à la
   préproduction (`vercel.json`), robots.txt ouvert avec le plan du site.
