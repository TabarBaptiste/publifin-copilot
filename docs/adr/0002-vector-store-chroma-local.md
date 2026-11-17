# ADR 0002 — Chroma comme base vectorielle locale, Python 3.14

- **Statut** : accepté
- **Date** : 2026-11-17

## Contexte
La Phase 1 demande un RAG local, sans Azure et à 0 € ([ADR 0001](0001-budget-zero-euro.md)). Il faut une base vectorielle locale. Le plan propose Chroma ou pgvector. Le plan visait aussi la dernière version de Python (3.15).

## Décision
- **Chroma** en mode embarqué (`PersistentClient`, dossier `data/chroma/`, non versionné) : aucun serveur à installer, similarité cosinus.
- **Python 3.14** au lieu de 3.15. À la tentative d'installation sous 3.15, `chromadb` (≥ 1.0) était irrésoluble : sa dépendance `onnxruntime` ne publie pas encore de wheel pour 3.15 (uniquement jusqu'à 3.14), et l'installeur retombait sur une version de `chromadb` de 2023 incompatible.
- Remontée possible vers 3.15 quand `onnxruntime` publiera ses wheels.

## Alternatives écartées
- **pgvector** : cohérent avec la cible (PostgreSQL pour l'audit) mais demande d'installer et d'administrer PostgreSQL dès la Phase 1. Reporté ; l'index vectoriel sera de toute façon remplacé par Azure AI Search en Phase 2.
- **Rester en Python 3.15** avec un autre magasin vectoriel : complexité inutile pour un gain minime.

## Conséquences
- (+) Démarrage immédiat, aucune infrastructure.
- (−) La recherche hybride (mots-clés + vecteurs) n'existe pas nativement dans cette configuration ; elle sera étudiée avec Azure AI Search en Phase 2 et comparée en Phase 5.
- (−) Chroma local et Azure AI Search étant différents, le code de recherche devra rester derrière une petite interface.
