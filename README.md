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


## Installation

### Installation depuis le depot de plugins QGIS du Parc national du Mercantour (Recommandé)

- Si le dépôt QGIS du Parc national du Mercantour n'est pas configuré dans QGIS suivre [la procédure d'installation](https://pnmercantour.github.io/donnees/tutos/installation_plugin_via_depot/)
- Dans QGIS allez dans **Extensions** → **Installer/Gérer les extensions**, dans l'onglet **Toutes**, recherchez l'extension `Analyse Survol` puis cliquez sur **Installer**

### Installation depuis un fichier ZIP

1. Téléchargez le plugin au format ZIP
2. Dans QGIS, allez dans **Extensions** → **Installer/Gérer les extensions**
3. Cliquez sur **Installer depuis un ZIP**
4. Sélectionnez le fichier ZIP du plugin
5. Cliquez sur **Installer l'extension**

## Documentation

### Pour les utilisateurs
**[Documentation Utilisateur](https://pnmercantour.github.io/analyse_survol_qgis/DOCUMENTATION_UTILISATEUR/)**
- Guide d'installation détaillé
- Tutoriels pas-à-pas
- [Cas d'usage concrets avec données d'exemple](https://pnmercantour.github.io/analyse_survol_qgis/DOCUMENTATION_UTILISATEUR/#cas-dusage)

### Pour les développeurs  
**[Documentation Développeur](https://pnmercantour.github.io/analyse_survol_qgis/DOCUMENTATION_DEVELOPPEUR/)**
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
- [Documentation Utilisateur complète](https://pnmercantour.github.io/analyse_survol_qgis/DOCUMENTATION_UTILISATEUR/)
- [Documentation Développeur](https://pnmercantour.github.io/analyse_survol_qgis/DOCUMENTATION_DEVELOPPEUR/)  
- [QGIS.org](https://qgis.org)

*Plugin Analyse Survol v1.0 - Développé pour QGIS 3.40+*