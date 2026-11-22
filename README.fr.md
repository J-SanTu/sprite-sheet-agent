# Sprite & Sprite Sheet Agent

**Concevez le mouvement avant de dessiner chaque image. Gardez une référence vérifiable pour chaque modification.**

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md) · [Deutsch](README.de.md) · [Español](README.es.md)

v0.2.0 · **design by santu**

Un processus de production et des outils hors ligne pour les assistants IA dotés de capacités visuelles. À partir des vues du personnage et des actions souhaitées, organisez les structures de pose, les images indépendantes, les GIF de revue et la planche finale Sprite Sheet PNG avec ses métadonnées JSON.

<p align="center"><img src="assets/readme/structure-sequence.png" width="100%" alt="Trois poses anonymes réellement rendues par les outils, avec articulations, accessoire et points de contact"></p>

*Sortie réelle de `scripts/build_demo.py`. Cet exemple technique anonyme ne constitue ni un personnage finalisé ni une animation approuvée.*

## De la pose à la livraison

<p align="center"><img src="assets/readme/workflow.svg" width="100%" alt="Concevoir les poses, examiner les images, exporter le PNG et le JSON"></p>

1. **Concevoir** — Confirmer le personnage, les actions et les accessoires. Définir appuis, occultations et contacts pour chaque direction, puis valider les limites des zones et les palettes.
2. **Examiner** — Après approbation des structures, générer les poses clés puis les images de transition indépendantes. Comparer références, RAW, candidats et images voisines.
3. **Exporter** — Après approbation humaine du groupe courant, produire le PNG et le JSON avec rectangles, pivots et durées. L'intégration au moteur reste une étape séparée.

| Fonction | Comportement |
| --- | --- |
| Versions actives | Seuls les groupes du manifest apparaissent. Les fichiers modifiés exigent de nouvelles empreintes ; les anciennes approbations deviennent obsolètes. |
| Revue comparative | Structure, RAW IA et candidat en trois colonnes, images voisines, taille commune, fonds et lecture image par image. |
| Protection des pixels | La méthode C restaure les régions immobiles aux mêmes coordonnées et produit des comparaisons et rapports de différences. |
| Suivi des requêtes | Références, budget et réponses sont enregistrés hors ligne. La reprise consulte la tâche existante et bloque les prises en charge répétées. |
| Atlas sans perte | Export PNG + JSON du groupe approuvé, avec vérification de la restitution exacte des pixels de chaque image. |

**L'hôte IA assure la conception, l'analyse visuelle et la génération ; l'utilisateur approuve.** Aucun service de génération, validation artistique automatique ou plugin de moteur n'est intégré.

## Démarrage rapide

Prérequis : **Python 3.10+, Pillow, macOS ou Linux**. Le verrouillage utilise `fcntl` ; l'exécution native sous Windows n'est pas prise en charge. Depuis la racine du paquet :

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install Pillow
python3 scripts/build_demo.py ../sprite-agent-demo
```

Ouvrez `../sprite-agent-demo/review/index.html` dans un navigateur. La démo contient des structures, des blocs colorés de test, un lecteur et l'export des avis. Ces blocs ne sont pas des personnages générés. Le dossier de sortie doit être vide ; choisissez un nouveau dossier à chaque essai. Aucun appel API n'est effectué.

## Utiliser avec un assistant IA

Installez le dossier entier sous le nom `sprite-sheet-agent`, avec `SKILL.md` à sa racine. Conservez les ressources et résultats dans un autre espace de travail.

- **Codex :** dossier de compétences configuré, par exemple `~/.codex/skills/sprite-sheet-agent/`. Rechargez puis invoquez `$sprite-sheet-agent`.
- **Claude Code :** `~/.claude/skills/sprite-sheet-agent/` ou le dossier du projet. Rechargez puis invoquez `/sprite-sheet-agent`.
- **Autres :** faites lire [AGENT.md](AGENT.md), [SKILL.md](SKILL.md) et les [règles de production](references/production-method.md).

Ces installations ne sont pas encore vérifiées en session réelle. Le README seul ne charge pas toutes les règles. L'hôte doit pouvoir lire et écrire des fichiers, examiner des images et accéder au générateur choisi.

Préparez les vues approuvées de face, de profil et de dos, les dimensions cibles et les actions. Ajoutez l'autre profil pour un personnage asymétrique et des références indépendantes pour les accessoires.

> Utilise sprite-sheet-agent dans mon espace de travail. Vérifie mes vues et planifie la marche dans quatre directions, l'assise et le lever. Présente d'abord les actions, les accessoires et les structures colorées. Attends mon approbation avant de générer les images du personnage. Mets à jour la page de revue par groupe et conserve les références, les RAW et les versions rejetées.

## Choisir A / B / C

| Méthode | Entrée du modèle | Traitement |
| --- | --- | --- |
| A | Image de référence + masque d'édition + consigne courte | Conserver le résultat et l'examiner. |
| B | Entrées A + JSON de la tâche actuelle | Conserver le résultat et l'examiner. |
| C | Identique à B | Restaurer les pixels avec un masque de protection distinct, puis vérifier raccords et mouvement. |

Si le fournisseur ne prend pas en charge les masques, documentez le mode dégradé. Le JSON exprime des contraintes, sans garantir leur exécution. C exige une région immobile, les mêmes dimensions et coordonnées. Ne figez pas l'ancienne position de la tête lors d'une assise, d'une rotation ou d'une course.

Pour une même source et un même résultat du modèle, C autorise au plus deux compositions. La seconde doit modifier la limite alpha effective. Il ne s'agit pas de deux générations supplémentaires. Le budget et le nombre d'appels sont confirmés séparément : trois appels totaux par image sont une suggestion, les limites déjà convenues restent prioritaires. Sans candidat valable, laissez l'image à corriger.

## Documentation et limites

[Guide anglais](docs/usage.en.md) · [Guide chinois](docs/usage.zh-CN.md) · [Modèles](templates/) · [Validation, en chinois](VALIDATION.md)

Des essais hors ligne sont consignés. Le chargement dans les hôtes, la qualité des services externes, la production complète de personnages et l'intégration aux moteurs restent à vérifier. Seul ce README est traduit en français ; les guides existent en anglais et chinois, les règles et l'interface de revue restent principalement en chinois.

Aucun détecteur automatique de couleurs n'est inclus. L'hôte échantillonne les zones approuvées et effectue l'analyse visuelle. Conservez les originaux et RAW ; distinguez contrôles techniques, auto-évaluation, approbation humaine et validation moteur. Les scripts dessinent les guides, mais ne doivent pas fabriquer le mouvement final par miroir, assemblage de membres ou interpolation automatique.

---

**design by santu**
