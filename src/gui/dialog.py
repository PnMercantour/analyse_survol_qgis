# -*- coding: utf-8 -*-
"""
Interface utilisateur du plugin d'altitude relative
"""

from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QComboBox, QProgressBar, QCheckBox)
from qgis.gui import QgsMapLayerComboBox, QgsProjectionSelectionWidget
from qgis.core import QgsMapLayerProxyModel, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import QVariant


class AltitudeRelativeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calcul d'altitude relative")
        self.setFixedSize(400, 350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Sélection du MNT
        layout.addWidget(QLabel("Sélectionnez le MNT (couche raster):"))
        self.mnt_combo = QgsMapLayerComboBox()
        self.mnt_combo.setFilters(QgsMapLayerProxyModel.RasterLayer)
        layout.addWidget(self.mnt_combo)
        
        # Sélection de la couche polyligne
        layout.addWidget(QLabel("Sélectionnez la couche polyligne:"))
        self.polyline_combo = QgsMapLayerComboBox()
        self.polyline_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        layout.addWidget(self.polyline_combo)
        
        # Champ altitude absolue
        layout.addWidget(QLabel("Champ contenant l'altitude absolue (optionnel):"))
        self.altitude_field_combo = QComboBox()
        self.altitude_field_combo.addItem("(Utiliser coordonnée Z de la géométrie)", "")
        layout.addWidget(self.altitude_field_combo)
        
        # Option pour créer une nouvelle couche
        self.create_new_layer_check = QCheckBox("Créer une nouvelle couche")
        self.create_new_layer_check.setChecked(True)
        layout.addWidget(self.create_new_layer_check)
        
        # Sélection de la projection de sortie
        layout.addWidget(QLabel("Projection de sortie:"))
        self.crs_selector = QgsProjectionSelectionWidget()
        # Définir Lambert 93 par défaut
        lambert93 = QgsCoordinateReferenceSystem("EPSG:2154")
        self.crs_selector.setCrs(lambert93)
        layout.addWidget(self.crs_selector)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
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
        self.polyline_combo.layerChanged.connect(self.update_altitude_fields)
        
        # Initialiser les champs
        self.update_altitude_fields()
    
    def update_altitude_fields(self):
        """Met à jour la liste des champs disponibles pour l'altitude"""
        self.altitude_field_combo.clear()
        
        # Option par défaut pour utiliser la coordonnée Z
        self.altitude_field_combo.addItem("(Utiliser coordonnée Z de la géométrie)", "")
        
        layer = self.polyline_combo.currentLayer()
        if layer:
            fields = layer.fields()
            for field in fields:
                if field.type() in [QVariant.Double, QVariant.Int]:
                    self.altitude_field_combo.addItem(field.name(), field.name())