# ADR 0006 — Découpage en morceaux de 1 200 caractères et 4 extraits

- **Statut** : accepté
- **Date** : 2026-11-22

## Contexte
Le RAG découpait les PDF en morceaux de 2 400 caractères (chevauchement de 300) et envoyait 2 extraits au modèle (choix de la Phase 1, mesuré sur 17 questions). L'évaluation de la Phase 5 (49 questions, dont reformulations et pièges ; voir [`docs/evaluation.md`](../evaluation.md)) a comparé ce réglage à deux variantes, avec un budget de contexte constant (~1 200 tokens par question).

## Décision
- **Morceaux de 1 200 caractères, chevauchement de 150, 4 extraits** par question (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`).
- Modèle de génération inchangé : `qwen3:4b-instruct`.
- Seuil de pertinence `max_distance = 0,43` inchangé : aucun seuil unique ne sépare proprement questions à réponse et pièges ; on ne le retouchera qu'avec la recherche hybride (Azure AI Search).

## Résultats qui fondent la décision
| Réglage | Bonnes réponses (règle) | Pièges refusés | Reformulations | Latence médiane |
| --- | --- | --- | --- | --- |
| 2 400/300, 2 extraits | 23/38 | 11/11 | 6/10 | 19,1 s |
| **1 200/150, 4 extraits** | **30/38** | 11/11 | **8/10** | 19,7 à 20,8 s |
| `gemma3:4b`, 2 extraits | 21/38 | 9/11 | 5/10 | 15,4 s |

La mesure a été refaite après application par défaut et ré-ingestion de l'index principal : résultats identiques.

## Alternatives écartées
- **`gemma3:4b`** : plus rapide, mais moins de bonnes réponses et 2 pièges non refusés.
- **Garder 2 400 caractères** : plus de questions où le bon passage n'est pas retrouvé, surtout pour les reformulations.

## Conséquences
- (+) +7 bonnes réponses sur 38, sans coût supplémentaire (même volume de tokens) ni hausse notable de latence.
- (−) Une information peut être séparée de son contexte (observé : `rgpd-03`, montant d'amende séparé des articles concernés ; `ofgl-02`, chiffre dans un autre morceau de la même page). Le modèle refuse alors, sans inventer.
- (−) La taille du morceau et le nombre d'extraits ont changé ensemble : leurs effets ne sont pas isolés.
- Changer ces valeurs impose de ré-ingérer le corpus (~6 min en local, 1 760 morceaux).
