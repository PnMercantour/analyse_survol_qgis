# -*- coding: utf-8 -*-
"""
Module de visualisation des segments de ligne avec colormap
"""

import math
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

from qgis.core import (QgsGeometry, QgsFeature, QgsPoint, QgsVectorLayer,
                      QgsField, QgsSimpleLineSymbolLayer, QgsSymbol,
                      QgsRendererCategory, QgsCategorizedSymbolRenderer)
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor


@dataclass
class ColorStop:
    """Point de contrôle pour le dégradé de couleur"""
    altitude: float
    color: Tuple[int, int, int]


class LineSegmentVisualizer:
    """Classe pour la visualisation des segments de ligne avec colormap"""

    DEFAULT_COLOR_STOPS = [
        ColorStop(0, (255, 0, 0)),      # rouge
        ColorStop(500, (255, 165, 0)),   # orange
        ColorStop(800, (255, 255, 0)),   # jaune
        ColorStop(1000, (0, 128, 0))     # vert
    ]

    def __init__(self, segment_length: float = 5.0, color_stops: List[ColorStop] = None):
        """
        Initialise le visualiseur de segments
        
        Args:
            segment_length: Longueur des segments en mètres
            color_stops: Points de contrôle pour le dégradé de couleur
        """
        self.segment_length = segment_length
        self.color_stops = color_stops or self.DEFAULT_COLOR_STOPS

    def create_segment_layer(self, source_layer: QgsVectorLayer, name: str = None) -> QgsVectorLayer:
        """
        Crée une nouvelle couche de segments colorés
        
        Args:
            source_layer: Couche source contenant les lignes à segmenter
            name: Nom de la nouvelle couche (optionnel)
            
        Returns:
            Nouvelle couche vectorielle avec les segments
        """
        # Créer la couche 
        # Utiliser MultiLineStringZ pour supporter à la fois les lignes simples et multiples avec Z
        name = name or f"{source_layer.name()}_segments_{self.segment_length}m"
        vl = QgsVectorLayer(
            f"MultiLineStringZ?crs={source_layer.crs().authid()}",
            name,
            "memory"
        )
        
        # Ajouter les champs
        provider = vl.dataProvider()
        provider.addAttributes([
            QgsField("z_avg", QMetaType.Double),
            QgsField("length", QMetaType.Double),
            QgsField("color", QMetaType.QString)
        ])
        vl.updateFields()

        # Traiter toutes les entités
        features = []
        for feature in source_layer.getFeatures():
            features.extend(self._process_feature(feature))
            
        # Ajouter les entités
        provider.addFeatures(features)
        vl.updateExtents()
        
        # Appliquer la symbologie
        self._apply_symbology(vl)
        
        return vl

    def _process_feature(self, feature: QgsFeature) -> List[QgsFeature]:
        """Traite une entité et retourne les segments résultants"""
        geom = feature.geometry()
        segments = []
        
        # Traiter les géométries Multi vs Simple en récupérant les points en 3D
        if geom.isMultipart():
            multi_geom = geom.constGet()
            for i in range(multi_geom.numGeometries()):
                part = multi_geom.geometryN(i)
                line_z = []
                for j in range(part.numPoints()):
                    pt = part.pointN(j)
                    line_z.append(QgsPoint(pt.x(), pt.y(), pt.z()))
                g = QgsGeometry.fromPolyline(line_z)
                segments.extend(self._create_segments(g))
        else:
            single_geom = geom.constGet()
            line_z = []
            for i in range(single_geom.numPoints()):
                pt = single_geom.pointN(i)
                line_z.append(QgsPoint(pt.x(), pt.y(), pt.z()))
            g = QgsGeometry.fromPolyline(line_z)
            segments.extend(self._create_segments(g))
            
        return segments

    def _create_segments(self, geometry: QgsGeometry) -> List[QgsFeature]:
        """Crée les segments à partir d'une géométrie"""
        segments = []
        for seg_pts, avg_z, length, color in self._split_line_3d(geometry):
            feat = QgsFeature()
            feat.setGeometry(QgsGeometry.fromPolyline(seg_pts))
            feat.setAttributes([avg_z, length, color])
            segments.append(feat)
        return segments

    def _split_line_3d(self, geometry: QgsGeometry) -> List[Tuple[List[QgsPoint], float, float, str]]:
        """Découpe une ligne 3D en segments de longueur fixe"""
        vertices = list(geometry.vertices())
        segments = []
        
        if len(vertices) < 2:
            return segments

        current_points = [vertices[0]]
        dist_acc = 0
        
        for i in range(1, len(vertices)):
            p_prev, p_curr = vertices[i-1], vertices[i]
            d = self._distance_3d(p_prev, p_curr)
            vec = QgsPoint(
                p_curr.x() - p_prev.x(),
                p_curr.y() - p_prev.y(),
                p_curr.z() - p_prev.z()
            )
            
            # Créer des segments de longueur fixe
            while dist_acc + d >= self.segment_length:
                t = (self.segment_length - dist_acc) / d
                new_pt = QgsPoint(
                    p_prev.x() + t * vec.x(),
                    p_prev.y() + t * vec.y(),
                    p_prev.z() + t * vec.z()
                )
                
                current_points.append(new_pt)
                avg_z = sum(v.z() for v in current_points) / len(current_points)
                length = sum(self._distance_3d(current_points[j], current_points[j+1])
                           for j in range(len(current_points)-1))
                           
                color = self._interpolate_color(avg_z)
                segments.append((current_points.copy(), avg_z, length, color))
                
                current_points = [new_pt]
                p_prev = new_pt
                d = self._distance_3d(p_prev, p_curr)
                vec = QgsPoint(
                    p_curr.x() - p_prev.x(),
                    p_curr.y() - p_prev.y(),
                    p_curr.z() - p_prev.z()
                )
                dist_acc = 0
                
            current_points.append(p_curr)
            dist_acc += d

        # Traiter le dernier segment
        if len(current_points) > 1:
            avg_z = sum(v.z() for v in current_points) / len(current_points)
            length = sum(self._distance_3d(current_points[j], current_points[j+1])
                        for j in range(len(current_points)-1))
            color = self._interpolate_color(avg_z)
            segments.append((current_points, avg_z, length, color))
            
        return segments

    def _distance_3d(self, p1: QgsPoint, p2: QgsPoint) -> float:
        """Calcule la distance 3D entre deux points"""
        return math.sqrt(
            (p2.x() - p1.x()) ** 2 +
            (p2.y() - p1.y()) ** 2 +
            (p2.z() - p1.z()) ** 2
        )

    def _interpolate_color(self, z: float) -> str:
        """
        Interpole la couleur en fonction de l'altitude
        
        Args:
            z: Altitude en mètres
            
        Returns:
            Code couleur au format hexadécimal (#RRGGBB)
        """
        if z >= self.color_stops[-1].altitude:
            r, g, b = self.color_stops[-1].color
            return f"#{r:02x}{g:02x}{b:02x}"

        for i in range(len(self.color_stops) - 1):
            stop1, stop2 = self.color_stops[i], self.color_stops[i + 1]
            
            if stop1.altitude <= z <= stop2.altitude:
                t = (z - stop1.altitude) / (stop2.altitude - stop1.altitude)
                r = int(stop1.color[0] + t * (stop2.color[0] - stop1.color[0]))
                g = int(stop1.color[1] + t * (stop2.color[1] - stop1.color[1]))
                b = int(stop1.color[2] + t * (stop2.color[2] - stop1.color[2]))
                return f"#{r:02x}{g:02x}{b:02x}"

        # Par défaut, retourner la première couleur
        r, g, b = self.color_stops[0].color
        return f"#{r:02x}{g:02x}{b:02x}"

    def _apply_symbology(self, layer: QgsVectorLayer) -> None:
        """Applique la symbologie catégorisée par couleur"""
        categories = []
        
        # Créer une catégorie pour chaque couleur unique
        unique_colors = set()
        for feature in layer.getFeatures():
            color = feature["color"]
            if color not in unique_colors:
                unique_colors.add(color)
                sym = QgsSymbol.defaultSymbol(layer.geometryType())
                sym.setColor(QColor(color))
                # Épaissir le trait à 1.25
                sym.setWidth(1.25)
                cat = QgsRendererCategory(color, sym, color)
                categories.append(cat)

        # Appliquer le rendu
        renderer = QgsCategorizedSymbolRenderer("color", categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()