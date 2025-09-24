# Documentation Développeur - Plugin Analyse Survol

## Table des matières
1. [Architecture générale](#architecture-générale)
2. [Principes de fonctionnement](#principes-de-fonctionnement)
3. [Structure du code](#structure-du-code)
4. [Modules détaillés](#modules-détaillés)
5. [Algorithmes implémentés](#algorithmes-implémentés)
6. [Gestion des coordonnées](#gestion-des-coordonnées)
7. [Interface utilisateur](#interface-utilisateur)
8. [Extensibilité](#extensibilité)
9. [Tests et debugging](#tests-et-debugging)

## Architecture générale

### Vue d'ensemble
Le plugin Analyse Survol suit une architecture modulaire basée sur le pattern MVC (Model-View-Controller) adapté pour QGIS :

```
analyse_survol/
├── __init__.py                 # Point d'entrée du plugin
├── metadata.txt               # Métadonnées du plugin
├── src/
│   ├── plugin.py             # Contrôleur principal
│   ├── core/                 # Logique métier
│   │   ├── calculator.py     # Calculs d'altitude
│   │   └── visualization/    # Visualisation et capture
│   │       ├── line_segment_visualizer.py
│   │       └── map_capture.py
│   └── gui/                  # Interface utilisateur
│       ├── dialog.py         # Dialogue altitude relative
│       ├── line_segment_dialog.py
│       └── altitude_check_dialog.py
└── resources/                # Ressources (icônes, etc.)
```

### Dépendances
- **QGIS Core** : API QGIS pour la manipulation des données géospatiales
- **QGIS GUI** : Widgets d'interface utilisateur QGIS
- **PyQt5/6** : Interface graphique
- **NumPy** : Calculs numériques optimisés
- **Processing** : Framework de traitement QGIS

## Principes de fonctionnement

### 1. Gestion des systèmes de coordonnées
Le plugin utilise une approche de transformation systématique :
- **Entrée** : Données dans n'importe quel CRS
- **Traitement** : Transformation vers Lambert 93 (EPSG:2154)
- **Sortie** : CRS configurable par l'utilisateur

**Justification** : Lambert 93 est une projection conforme pour la France, permettant des calculs de distance précis en coordonnées planes.

### 2. Traitement des géométries 3D
Le plugin gère nativement les géométries 3D :
- **LineStringZ** : Lignes avec coordonnées Z
- **MultiLineStringZ** : Collections de lignes 3D
- **Préservation des Z** : Maintien des informations d'altitude

### 3. Segmentation adaptative
La visualisation utilise une segmentation basée sur la distance :
- **Longueur fixe** : Segments de longueur métrique constante
- **Interpolation** : Création de points intermédiaires si nécessaire
- **Préservation topologique** : Maintien de la continuité

## Structure du code

### Hiérarchie des classes

```python
# Plugin principal
AltitudeRelativePlugin
├── AltitudeCalculator          # Logique de calcul
├── LineSegmentVisualizer       # Visualisation colorée
└── MapCapturer                # Génération de captures

# Dialogues
AltitudeRelativeDialog          # Interface calcul d'altitude
LineSegmentDialog              # Interface visualisation
AltitudeCheckDialog           # Interface détection dépassements
```

### Flux de données

```
Données d'entrée (LineStringZ + MNT)
    ↓
Validation et transformation CRS
    ↓
Traitement par module spécialisé
    ↓
Génération de résultats
    ↓
Affichage et export
```

## Modules détaillés

### plugin.py - Contrôleur principal

**Responsabilités** :
- Initialisation et configuration du plugin
- Gestion des actions utilisateur
- Orchestration des modules métier
- Gestion des erreurs et messages

**Classes principales** :
```python
class AltitudeRelativePlugin:
    def __init__(self, iface)           # Initialisation
    def initGui(self)                   # Interface graphique
    def run(self)                       # Calcul d'altitude
    def run_visualization(self)         # Visualisation
    def run_altitude_check(self)        # Détection dépassements
```

**Méthodes clés** :
- `process_altitude_calculation()` : Orchestration du calcul d'altitude
- `process_visualization()` : Gestion de la visualisation colorée
- Gestion des groupes consécutifs avec vérification topologique

### core/calculator.py - Moteur de calcul

**Objectif** : Calculer les altitudes relatives par rapport au terrain.

**Algorithme principal** :
1. **Drapage** : Utilisation de l'outil QGIS `native:setzfromraster`
2. **Comparaison** : Différence entre altitude de vol et altitude sol
3. **Mise à jour** : Modification des coordonnées Z avec les valeurs relatives

**Classes et méthodes** :
```python
class AltitudeCalculator:
    def create_output_layer(source_layer, output_crs=None)
    def calculate_relative_altitudes(mnt_layer, polyline_layer, ...)
    def add_altitude_fields(layer)

def replace_z(geom: QgsGeometry, new_z: np.ndarray) -> QgsGeometry
```

**Gestion des transformations** :
```python
# Transformation automatique si CRS différent
if output_crs and source_layer.crs() != output_crs:
    transform = QgsCoordinateTransform(source_layer.crs(), output_crs, QgsProject.instance())
    geom.transform(transform)
```

### core/visualization/line_segment_visualizer.py

**Objectif** : Créer une visualisation colorée des segments selon l'altitude.

**Algorithme de segmentation** :
1. **Extraction des vertices** : Récupération des points 3D
2. **Segmentation fixe** : Découpage selon une longueur métrique
3. **Interpolation** : Création de points intermédiaires si nécessaire
4. **Attribution couleur** : Application du dégradé selon l'altitude moyenne

**Classes principales** :
```python
@dataclass
class ColorStop:
    altitude: float
    color: Tuple[int, int, int]

class LineSegmentVisualizer:
    def __init__(self, segment_length=5.0, color_stops=None)
    def create_segment_layer(source_layer, name=None)
    def _split_line_3d(geometry)
    def _interpolate_color(z)
```

**Algorithme de découpage** :
```python
# Segmentation à longueur fixe
while dist_acc + d >= self.segment_length:
    t = (self.segment_length - dist_acc) / d
    new_pt = QgsPoint(
        p_prev.x() + t * vec.x(),
        p_prev.y() + t * vec.y(),
        p_prev.z() + t * vec.z()
    )
    # Création du segment
```

### core/visualization/map_capture.py

**Objectif** : Générer des captures de carte avec annotations.

**Fonctionnalités** :
- Capture simple de segments
- Capture avec marqueurs de début/fin
- Annotations automatiques (distance, légende)
- Layout optimisé pour la lisibilité

**Architecture de capture** :
```python
class MapCapturer:
    def capture_segment(segment_geom, buffer_size, filename)
    def capture_segment_with_markers(segment_geom, start_point, end_point, distance_text, ...)
    def _add_map_marker(layout, map_item, point, color)
    def _add_title_text(layout, title_text)
    def _add_legend(layout)
```

**Gestion du layout** :
```
┌─────────────────────────────────────┐
│  DÉPASSEMENT D'ALTITUDE - Distance  │ ← Titre (15mm)
├─────────────────────────────────────┤
│                                     │
│         ● CARTE ●                   │ ← Carte (140mm)
│      (avec marqueurs)               │
└─────────────────────────────────────┘
```

### gui/ - Interfaces utilisateur

**Dialogues spécialisés** :
- `AltitudeRelativeDialog` : Configuration du calcul d'altitude
- `LineSegmentDialog` : Paramètres de visualisation
- `AltitudeCheckDialog` : Détection des dépassements

**Widgets QGIS utilisés** :
- `QgsMapLayerComboBox` : Sélection de couches
- `QgsProjectionSelectionWidget` : Choix du CRS
- `QgsColorRampButton` : Configuration des dégradés

## Algorithmes implémentés

### 1. Détection de segments consécutifs

**Problème** : Identifier les segments qui se touchent réellement.

**Solution** :
```python
# Calcul de distance entre fin du segment précédent et début du nouveau
distance_to_previous_end = ((segment_start.x() - current_end_point.x()) ** 2 + 
                          (segment_start.y() - current_end_point.y()) ** 2) ** 0.5
is_consecutive = distance_to_previous_end <= tolerance  # 0.001m
```

**Avantages** :
- Robuste aux erreurs d'arrondi
- Évite les faux regroupements
- Préserve la topologie

### 2. Interpolation de couleurs

**Algorithme** : Interpolation linéaire entre points de contrôle.

```python
def _interpolate_color(self, z: float) -> str:
    for i in range(len(self.color_stops) - 1):
        stop1, stop2 = self.color_stops[i], self.color_stops[i + 1]
        if stop1.altitude <= z <= stop2.altitude:
            t = (z - stop1.altitude) / (stop2.altitude - stop1.altitude)
            r = int(stop1.color[0] + t * (stop2.color[0] - stop1.color[0]))
            # Idem pour g et b
            return f"#{r:02x}{g:02x}{b:02x}"
```

### 3. Transformation de coordonnées

**Stratégie** : Transformation systématique vers Lambert 93 pour les calculs.

```python
# Détection du besoin de transformation
needs_transform = output_crs and source_layer.crs() != output_crs
if needs_transform:
    transform = QgsCoordinateTransform(source_layer.crs(), output_crs, QgsProject.instance())
    geom.transform(transform)
```

### 4. Positionnement des marqueurs

**Problème** : Positionner précisément des marqueurs sur une carte en layout.

**Solution** : Conversion manuelle des coordonnées géographiques vers coordonnées de layout.

```python
# Position relative dans l'emprise (0-1)
rel_x = (point.x() - extent.xMinimum()) / extent.width()
rel_y = (extent.yMaximum() - point.y()) / extent.height()  # Y inversé

# Conversion en coordonnées layout
layout_x = map_rect.x() + rel_x * map_rect.width()
layout_y = map_rect.y() + rel_y * map_rect.height()
```

## Gestion des coordonnées

### Systèmes supportés
- **Entrée** : Tout CRS supporté par QGIS
- **Processing** : Lambert 93 (EPSG:2154) pour la France
- **Sortie** : CRS configurable

### Transformations automatiques
```python
# Dans create_output_layer
if output_crs:
    crs = output_crs.authid()
else:
    crs = source_layer.crs().authid()

# Transformation des features
transform = QgsCoordinateTransform(source_layer.crs(), output_crs, QgsProject.instance())
geom.transform(transform)
```

### Précision et performances
- **Précision** : Utilisation de coordonnées planes pour éviter les déformations
- **Performance** : Transformation une seule fois par feature
- **Robustesse** : Gestion des erreurs de transformation

## Interface utilisateur

### Architecture des dialogues
Tous les dialogues héritent des patterns QGIS :
- `QDialog` comme classe de base
- Utilisation de layouts pour l'organisation
- Widgets QGIS spécialisés pour la cohérence

### Validation des entrées
```python
# Vérification des couches disponibles
if dialog.layer_combo.currentLayer() is None:
    self.iface.messageBar().pushMessage("Erreur", "Aucune couche disponible", level=Qgis.Critical)
    return
```

### Gestion des erreurs
- Messages utilisateur via `messageBar()`
- Logs détaillés via `QgsMessageLog`
- Try/catch systématique avec rollback

## Extensibilité

### Points d'extension

#### 1. Nouveaux algorithmes de visualisation
```python
# Dans LineSegmentVisualizer
def _interpolate_color_custom(self, z: float, algorithm: str) -> str:
    if algorithm == "logarithmic":
        # Implémentation logarithmique
    elif algorithm == "exponential":
        # Implémentation exponentielle
```

#### 2. Formats d'export supplémentaires
```python
# Dans MapCapturer
def export_to_pdf(self, layout, filename):
    # Export PDF avec mise en page complexe
    
def export_to_svg(self, layout, filename):
    # Export vectoriel pour édition
```

#### 3. Calculs d'altitude alternatifs
```python
# Dans AltitudeCalculator
def calculate_with_interpolation(self, method="bilinear"):
    # Interpolation avancée du MNT
    
def calculate_with_multiple_sources(self, mnt_layers):
    # Fusion de plusieurs sources d'altitude
```

### Architecture modulaire
Chaque module est indépendant et peut être étendu :
- **Interfaces claires** : APIs bien définies
- **Faible couplage** : Dépendances minimales
- **Séparation des responsabilités** : Un module = une fonction

## Tests et debugging

### Stratégies de test

#### 1. Tests unitaires (recommandés)
```python
import unittest
from qgis.core import QgsGeometry, QgsPoint

class TestLineSegmentVisualizer(unittest.TestCase):
    def test_split_line_3d(self):
        # Test de segmentation
        line = QgsGeometry.fromPolyline([
            QgsPoint(0, 0, 100),
            QgsPoint(10, 0, 200)
        ])
        visualizer = LineSegmentVisualizer(segment_length=5.0)
        segments = visualizer._split_line_3d(line)
        self.assertEqual(len(segments), 2)  # 2 segments de 5m
```

#### 2. Tests d'intégration
- Test avec vraies données QGIS
- Vérification des résultats visuels
- Performance sur gros datasets

### Debugging

#### Logging avancé
```python
# Dans chaque module
QgsMessageLog.logMessage(f"Processing {len(features)} features", 
                        "AnalyseSurvol", Qgis.Info)

# Debug détaillé
if DEBUG:
    QgsMessageLog.logMessage(f"Segment {i}: start={start}, end={end}, z={z_avg}", 
                            "AnalyseSurvol", Qgis.Info)
```

#### Gestion des erreurs
```python
try:
    # Opération risquée
    result = process_geometry(geom)
except Exception as e:
    QgsMessageLog.logMessage(f"Erreur géométrie {geom.wkbType()}: {str(e)}", 
                            "AnalyseSurvol", Qgis.Critical)
    return None
```

### Optimisations

#### Performance
- **Vectorisation NumPy** : Calculs sur arrays pour la vitesse
- **Cache des transformations** : Réutilisation des objets QgsCoordinateTransform
- **Traitement par batch** : Éviter les boucles sur les features

#### Mémoire
- **Streaming** : Traitement feature par feature pour gros datasets
- **Cleanup** : Suppression explicite des objets temporaires
- **Lazy loading** : Chargement à la demande des données

---

## API de référence

### Classes principales

#### AltitudeRelativePlugin
```python
class AltitudeRelativePlugin:
    """Classe principale du plugin"""
    
    def __init__(self, iface: QgisInterface)
    def initGui(self) -> None
    def unload(self) -> None
    def run(self) -> None
    def run_visualization(self) -> None
    def run_altitude_check(self) -> None
```

#### AltitudeCalculator
```python
class AltitudeCalculator:
    """Calculateur d'altitude relative"""
    
    def create_output_layer(self, source_layer: QgsVectorLayer, 
                          output_crs: QgsCoordinateReferenceSystem = None) -> QgsVectorLayer
    
    def calculate_relative_altitudes(self, mnt_layer: QgsRasterLayer, 
                                   polyline_layer: QgsVectorLayer,
                                   altitude_field: str,
                                   use_z_coordinate: bool,
                                   progress_callback: callable = None) -> bool
```

#### LineSegmentVisualizer
```python
class LineSegmentVisualizer:
    """Visualiseur de segments colorés"""
    
    def __init__(self, segment_length: float = 5.0, 
                 color_stops: List[ColorStop] = None)
    
    def create_segment_layer(self, source_layer: QgsVectorLayer, 
                           name: str = None) -> QgsVectorLayer
```

#### MapCapturer
```python
class MapCapturer:
    """Générateur de captures de carte"""
    
    def __init__(self, iface: QgisInterface, output_folder: str)
    
    def capture_segment_with_markers(self, segment_geom: QgsGeometry,
                                   start_point: QgsPointXY,
                                   end_point: QgsPointXY,
                                   distance_text: str,
                                   buffer_size: int = 200,
                                   filename: str = None) -> str
```

---
*Documentation développeur générée avec Claude Sonnet 4.*  
*Plugin Analyse Survol - Documentation développeur v1.0*  
*Mise à jour le 24 septembre 2025*