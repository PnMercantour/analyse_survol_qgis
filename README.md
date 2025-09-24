# Plugin Analyse Survol pour QGIS

Plugin QGIS spécialisé dans l'analyse des trajectoires de vol et le calcul d'altitudes relatives par rapport au terrain.

## Fonctionnalités principales

- **Calcul d'altitude relative** : Détermine l'altitude de vol par rapport au sol
- **Visualisation colorée** : Affichage des segments avec dégradé selon l'altitude  
- **Détection automatique** : Identification des dépassements d'altitude minimale
- **Rapports visuels** : Génération de captures avec marqueurs et distances
- **Multi-projections** : Support de tous les systèmes de coordonnées QGIS

## Prérequis

- QGIS 3.40 ou version ultérieure
- Python 3.12+
- Données d'entrée :
  - Couche MNT (Modèle Numérique de Terrain) au format raster
  - Trajectoires de vol au format LineStringZ avec coordonnées d'altitude


## Installation avec un fichier zip

1. Allez dans `Extensions > Installer / Gérer les Extensions > Installer depuis un ZIP`
2. Cliquez sur `...` puis allez chercher le zip
3. Cliquez sur `Installer l'extension`

## Installation rapide

1. Copiez le dossier `analyse_survol` dans votre répertoire de plugins QGIS
2. Activez le plugin dans `Extensions > Gestionnaire d'extensions`
3. Les outils apparaissent dans la barre d'outils "AltitudeRelative"

## Documentation

### Pour les utilisateurs
**[Documentation Utilisateur](doc/DOCUMENTATION_UTILISATEUR.md)**
- Guide d'installation détaillé
- Tutoriels pas-à-pas
- Cas d'usage concrets

### Pour les développeurs  
**[Documentation Développeur](doc/DOCUMENTATION_DEVELOPPEUR.md)**
- Architecture du code
- API de référence
- Algorithmes implémentés
- Guide d'extension
- Tests et debugging

## Architecture technique

```
analyse_survol/
├── src/
│   ├── plugin.py              # Contrôleur principal
│   ├── core/
│   │   ├── calculator.py         # Calculs d'altitude
│   │   └── visualization/        # Visualisation et capture
│   └── gui/                   # Interfaces utilisateur
└── docs/                      # Documentation
```

### Problèmes courants
- **Pas de coordonnées Z** → Vérifiez que vos trajectoires sont en 3D
- **Erreurs de projection** → Le plugin transforme automatiquement vers Lambert 93

### Logs et debugging
Les messages détaillés sont disponibles dans :
`Vue > Panneaux > Journal des messages`

---

**🔗 Liens utiles**
- [Documentation Utilisateur complète](DOCUMENTATION_UTILISATEUR.md)
- [Documentation Développeur](DOCUMENTATION_DEVELOPPEUR.md)  
- [QGIS.org](https://qgis.org)

*Plugin Analyse Survol v1.0 - Développé pour QGIS 3.40+*