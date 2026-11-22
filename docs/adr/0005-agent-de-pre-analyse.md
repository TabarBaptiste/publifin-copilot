# ADR 0005 — Agent de pré-analyse : workflow LangGraph avec validation humaine

- **Statut** : accepté
- **Date** : 2026-11-18

## Contexte
Le cas d'usage 2 doit produire une note de pré-analyse d'une demande de financement à partir de données publiques et du corpus, puis **attendre la validation d'un humain** avant d'enregistrer quoi que ce soit, en laissant une trace complète. Le modèle local (4 milliards de paramètres, CPU) est lent (10 à 40 s par appel) et peu fiable pour choisir seul des outils.

## Décision
- **LangGraph** : état typé, un nœud par étape, *interrupt* avant l'enregistrement, checkpoints dans **PostgreSQL** (une analyse en attente survit à un redémarrage).
- **Chemin fixe, modèle sur deux étapes seulement.** Les outils sont appelés par du code, jamais choisis par le modèle :
  1. `extract_request` (modèle, sortie JSON validée) ;
  2. `find_commune` (API Géo), `get_finances` (données OFGL), `compute_indicators` (calcul) ;
  3. `search_rules` (questions fixes posées au corpus, seuil de pertinence du RAG) ;
  4. `draft_note` (modèle, un paragraphe de 2-3 phrases) ;
  5. `human_review` (*interrupt*), `record_decision`, `save_note`.
- **Les chiffres viennent du code.** La note est assemblée par `build_note` : situation financière, alertes et sources sont calculées. Le modèle n'écrit que le paragraphe d'appréciation, qui doit citer des extraits valides ; sans citation valide, il est remplacé par un texte neutre. Les montants (« 2 M€ ») sont lus par une expression régulière : le modèle les convertissait mal (observé : `null`).
- **Droits minimaux** : les outils sont en lecture seule avec des schémas d'entrée stricts (`extra="forbid"`, motifs sur les codes). Une seule écriture existe (`save_note`), atteignable uniquement après `record_decision` avec l'action `approve` ou `edit`, et protégée une seconde fois dans le nœud.
- **Audit append-only** : table `audit_events` avec un déclencheur qui refuse `UPDATE` et `DELETE`. Chaque appel (entrée, sortie, durée, statut) et chaque décision (nom du relecteur, action, commentaire) y figure.
- **Limites** : 25 étapes de graphe maximum (`recursion_limit`), budget de 12 000 tokens estimés et 600 s par analyse ; dépassement = analyse arrêtée sans écriture.
- **Interface** : l'API lance l'analyse en arrière-plan ; le front interroge `GET /analyses/{id}` toutes les 1,5 s pour afficher la chronologie, puis l'écran de validation.

## Alternatives écartées
- **Agent « ReAct » choisissant ses outils** : imprévisible avec un petit modèle, plus long, plus difficile à borner et à auditer. Un chemin fixe donne le même résultat ici.
- **Tout faire écrire au modèle** : il inventait des seuils (observé : « neuf années » appliqué à une commune alors que le seuil est de 12 ans) ; d'où les seuils fournis explicitement et les chiffres calculés.
- **Flux temps réel (SSE)** : plus complexe que l'interrogation périodique pour un gain nul à cette échelle.

## Conséquences
- (+) Comportement prévisible, borné, vérifié par 22 tests du graphe, des outils et de l'API (dont des tests contre un vrai PostgreSQL).
- (+) Le relecteur voit exactement ce qui a été fait, étape par étape, et peut corriger la note.
- (−) Le texte du paragraphe d'appréciation peut rester maladroit ou ambigu (observé : « le taux de 7,2 % dépasse le seuil d'alerte de 7 % »). C'est précisément ce que la validation humaine couvre ; à mesurer en Phase 5.
- Mise à jour (2026-11-22) : erreur confirmée en préparant la démo (« 23,2 % dépasse le seuil d'alerte de 7 % » pour une commune saine). Correction : le code énonce lui-même chaque comparaison avec son seuil (« AU-DESSUS du seuil d'alerte de 7 % (pas d'alerte) ») et le modèle la reprend sans la refaire ; 8 essais sur 8 corrects ensuite, banc d'injection inchangé (7/9).
- (−) Le relecteur saisit son nom à la main : pas d'authentification tant qu'Entra ID n'est pas branché (Phase 6). Le nom enregistré n'est donc pas une preuve d'identité.
- (−) Les indicateurs reposent sur le **budget principal** des communes (OFGL), pas sur les budgets annexes, et sur la dernière année publiée.
- Variante Semantic Kernel : non faite (étape facultative du plan).
