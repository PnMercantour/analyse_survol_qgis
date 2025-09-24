# -*- coding: utf-8 -*-
"""
Module pour la capture d'images de la carte
"""

from cProfile import label
import os
from qgis.core import (QgsRectangle, QgsGeometry, QgsLayoutExporter,
                      QgsPrintLayout, QgsLayoutItemMap, QgsLayoutSize,
                      QgsUnitTypes, QgsLayoutPoint, QgsProject, QgsPointXY,
                      QgsLayoutItemLabel, QgsLayoutItemMarker, QgsMarkerSymbol,
                      QgsLayoutItemShape, QgsFillSymbol, QgsLayoutItemPage, QgsTextFormat)
from qgis.PyQt.QtCore import QSizeF, QPointF, QRectF as QRectangleF, Qt
from qgis.PyQt.QtGui import QFont, QColor


class MapCapturer:
    """Classe pour capturer des images de la carte"""
    
    def __init__(self, iface, output_folder):
        """
        Initialise le capturer de carte
        
        Args:
            iface: Interface QGIS
            output_folder: Dossier où sauvegarder les captures
        """
        self.iface = iface
        self.output_folder = output_folder
        self.map_canvas = iface.mapCanvas()
        
        # Créer le dossier de sortie s'il n'existe pas
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
    def capture_segment(self, segment_geom, buffer_size=100, filename=None):
        """
        Capture une image de la carte centrée sur un segment
        
        Args:
            segment_geom: Géométrie du segment (QgsGeometry)
            buffer_size: Taille du buffer autour du segment en mètres
            filename: Nom du fichier de sortie (optionnel)
            
        Returns:
            Le chemin du fichier image créé
        """
        # Obtenir l'emprise du segment avec un buffer
        bounds = segment_geom.boundingBox()
        bounds.grow(buffer_size)
        
        # Créer une mise en page
        project = QgsProject.instance()
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()


        
        # Configurer la carte
        map_item = QgsLayoutItemMap(layout)
        map_item.attemptSetSceneRect(QRectangleF(20, 20, 200, 200))
        map_item.setExtent(bounds)
        layout.addLayoutItem(map_item)
        
        map_item.setBackgroundColor(self.map_canvas.canvasColor())
        
        # Copier la configuration de la carte actuelle
        map_item.setLayers(self.map_canvas.layers())
        map_item.setMapRotation(self.map_canvas.rotation())
        
        # Générer un nom de fichier si non fourni
        if filename is None:
            bbox = bounds.center()
            filename = f"segment_{bbox.x():.5f}_{bbox.y():.5f}.png"
            
        output_path = os.path.join(self.output_folder, filename)
        
        # Exporter l'image
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToImage(output_path, 
                                      QgsLayoutExporter.ImageExportSettings())
        
        if result == QgsLayoutExporter.Success:
            return output_path
        else:
            return None
    
    def capture_segment_with_markers(self, segment_geom, start_point, end_point, 
                                   distance_text, buffer_size=200, min_altitude=float('inf'), filename=None):
        """
        Capture une image de la carte avec des marqueurs de début/fin et la distance
        
        Args:
            segment_geom: Géométrie du segment (QgsGeometry)
            start_point: Point de début du dépassement (QgsPointXY)
            end_point: Point de fin du dépassement (QgsPointXY)
            distance_text: Texte de la distance à afficher
            buffer_size: Taille du buffer autour du segment en mètres
            filename: Nom du fichier de sortie (optionnel)
            
        Returns:
            Le chemin du fichier image créé
        """
        # Obtenir l'emprise du segment avec un buffer
        bounds = segment_geom.boundingBox()
        bounds.grow(buffer_size)
        
        # Créer une mise en page avec espace pour le titre
        project = QgsProject.instance()
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()

        # ---- proportions de la carte ----
        map_width = bounds.width()
        map_height = bounds.height()
        aspect_ratio = map_width / map_height

        # dimension max en mm pour la carte
        max_dim = 180

        if aspect_ratio >= 1:
            map_width_mm = max_dim
            map_height_mm = max_dim / aspect_ratio
        else:
            map_height_mm = max_dim
            map_width_mm = max_dim * aspect_ratio

        # marges et titre
        margin_left = 10
        margin_right = 10
        margin_bottom = 10
        title_height = 25

        # taille page
        page_width_mm = margin_left + map_width_mm + margin_right
        page_height_mm = title_height + map_height_mm + margin_bottom

        page = layout.pageCollection().page(0)
        page.setPageSize(QgsLayoutSize(page_width_mm, page_height_mm))

        # ---- titre ----
        self._add_title_text(layout, f"DÉPASSEMENT D'ALTITUDE - Longueur: {distance_text} - altitude minimale: {min_altitude:.0f}m")

        # ---- carte ----
        map_item = QgsLayoutItemMap(layout)
        map_item.attemptSetSceneRect(
            QRectangleF(margin_left, title_height, map_width_mm, map_height_mm)
        )
        map_item.setExtent(bounds)
        layout.addLayoutItem(map_item)
        
        map_item.setBackgroundColor(self.map_canvas.canvasColor())
        
        # Copier la configuration de la carte actuelle
        map_item.setLayers(self.map_canvas.layers())
        map_item.setMapRotation(self.map_canvas.rotation())
        
        # Ajouter les marqueurs de début et fin directement sur la carte
        self._add_map_marker(layout, map_item, start_point, QColor(255, 0, 0))
        self._add_map_marker(layout, map_item, end_point, QColor(255, 0, 0))
                
        # Générer un nom de fichier si non fourni
        if filename is None:
            bbox = bounds.center()
            filename = f"segment_marked_{bbox.x():.5f}_{bbox.y():.5f}.png"
            
        output_path = os.path.join(self.output_folder, filename)
        
        # Exporter l'image
        exporter = QgsLayoutExporter(layout)
        result = exporter.exportToImage(output_path, 
                                      QgsLayoutExporter.ImageExportSettings())
        
        if result == QgsLayoutExporter.Success:
            return output_path
        else:
            return None
    
    def _add_map_marker(self, layout, map_item, point, color):
        """Ajoute un marqueur coloré sur la carte à la position donnée"""
        # Convertir le point géographique en coordonnées de layout
        extent = map_item.extent()
        map_rect = map_item.rect()
                
        # Position relative du point dans l'emprise (0-1)
        rel_x = (point.x() - extent.xMinimum()) / extent.width()
        rel_y = (extent.yMaximum() - point.y()) / extent.height()  # Y inversé
        
        # S'assurer que les marqueurs restent dans la carte (avec une marge)
        margin = 0.02  # 2% de marge
        rel_x = max(margin, min(1.0 - margin, rel_x))
        rel_y = max(margin, min(1.0 - margin, rel_y))
        
        # Convertir en coordonnées de layout
        layout_x = map_rect.x() + rel_x * map_rect.width() + 10
        layout_y = map_rect.y() + rel_y * map_rect.height() + 25
        
        # Créer le marqueur (cercle)
        marker = QgsLayoutItemShape(layout)
        marker.setShapeType(QgsLayoutItemShape.Ellipse)
        
        # Positionner le marqueur
        marker_size = 3  # mm (plus petit pour être moins intrusif)
        marker.attemptSetSceneRect(QRectangleF(
            layout_x - marker_size/2, 
            layout_y - marker_size/2,
            marker_size, 
            marker_size
        ))
        
        # Configurer l'apparence du marqueur avec contour noir
        symbol = QgsFillSymbol.createSimple({
            'color': color.name(), 
            'outline_color': 'black',
            'outline_width': '0.3'
        })
        marker.setSymbol(symbol)
        
        layout.addLayoutItem(marker)
    
    def _add_title_text(self, layout, title_text):
        """Ajoute le titre en haut de la page en rouge"""
        title_label = QgsLayoutItemLabel(layout)
        title_label.setText(title_text)

        page = layout.pageCollection().page(0)

        # récupérer la largeur et la hauteur en mm
        page_width_mm = page.pageSize().width()
        
        # Configurer la police
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        fmt = QgsTextFormat()

        fmt.setFont(font)

        # Définir couleur
        fmt.setColor(QColor("black"))

        # Appliquer le format au label
        title_label.setTextFormat(fmt)
        
        # Positionner en haut de la page
        title_label.attemptSetSceneRect(QRectangleF(0, 10, page_width_mm, 20))
        title_label.setHAlign(Qt.AlignCenter)
        
        layout.addLayoutItem(title_label)