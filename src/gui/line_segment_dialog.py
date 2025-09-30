# -*- coding: utf-8 -*-
"""
Widget de dialogue pour la visualisation des segments
"""

from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QDoubleSpinBox, QCheckBox)
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapLayerComboBox, QgsColorRampButton
from qgis.core import QgsMapLayerProxyModel, QgsGradientColorRamp, QgsGradientStop, QgsProject, QgsMapLayer, QgsWkbTypes, QgsMessageLog, Qgis


class LineSegmentDialog(QDialog):
    """Dialogue pour la configuration de la visualisation des segments"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visualisation des segments")
        self.setFixedSize(400, 200)
        self.init_ui()
        
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Sélection de la couche source
        layout.addWidget(QLabel("Sélectionnez la couche à segmenter:"))
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        # --- sélectionner par défaut la couche qui a le champ "altitude_relative" ---
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry:
                if "altitude_relative" in layer.name():
                    self.layer_combo.setLayer(layer)
                    break
        layout.addWidget(self.layer_combo)

        
        # Configuration de la longueur des segments
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Longueur des segments (m):"))
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0.1, 100.0)
        self.length_spin.setValue(5.0)
        self.length_spin.setSingleStep(0.5)
        length_layout.addWidget(self.length_spin)
        layout.addLayout(length_layout)
        
        # Option pour créer une nouvelle couche
        self.create_new_layer_check = QCheckBox("Créer une nouvelle couche")
        self.create_new_layer_check.setChecked(True)
        layout.addWidget(self.create_new_layer_check)
        
        # Sélecteur de dégradé de couleurs
        layout.addWidget(QLabel("Configuration du dégradé de couleurs:"))
        
        color_layout = QHBoxLayout()
        self.color_ramp_button = QgsColorRampButton()
        
        # Créer le dégradé par défaut
        stops = [
            QgsGradientStop(0.0, QColor(255, 0, 0)),      # rouge à 0m
            QgsGradientStop(0.5, QColor(255, 165, 0)),   # orange à 500m
            QgsGradientStop(0.8, QColor(255, 255, 0)),   # jaune à 800m
            QgsGradientStop(1.0, QColor(0, 128, 0))      # vert à 1000m
        ]
        ramp = QgsGradientColorRamp(stops=stops)
        self.color_ramp_button.setColorRamp(ramp)
        
        color_layout.addWidget(self.color_ramp_button)
        layout.addLayout(color_layout)
        
        # Boutons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Annuler")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connexions
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
    def get_color_stops(self):
        """Retourne la liste des points de couleur configurés"""
        from ..core.visualization.line_segment_visualizer import ColorStop
        
        ramp = self.color_ramp_button.colorRamp()
        if not ramp:
            return []
            
        stops = []
        for stop in ramp.stops():
            # Convertir la position relative (0-1) en altitude (0-1000m)
            altitude = stop.offset * 1000
            color = stop.color
            stops.append(ColorStop(altitude, (color.red(), color.green(), color.blue())))
            
        return sorted(stops, key=lambda x: x.altitude)