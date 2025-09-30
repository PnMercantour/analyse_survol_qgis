# -*- coding: utf-8 -*-
"""
Widget de dialogue pour la détection des segments sous altitude minimale
"""

from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QDoubleSpinBox, QCheckBox, QLineEdit,
                                QFileDialog)
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel, QgsProject, QgsMapLayer, QgsWkbTypes
import os


class AltitudeCheckDialog(QDialog):
    """Dialogue pour la détection des segments sous altitude minimale"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Détecter segments sous altitude minimale")
        self.setFixedSize(450, 250)
        self.init_ui()
        
    def init_ui(self):
        """Initialise l'interface utilisateur"""
        layout = QVBoxLayout()
        
        # Sélection de la couche source
        layout.addWidget(QLabel("Sélectionnez la couche à analyser (elle doit contenir des segments relativement courts):"))
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.LineLayer)
        layout.addWidget(self.layer_combo)
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry:
                if "altitude_relative_segments" in layer.name():
                    self.layer_combo.setLayer(layer)
                    break
        
        # Configuration de l'altitude minimale
        min_alt_layout = QHBoxLayout()
        min_alt_layout.addWidget(QLabel("Altitude minimale (m):"))
        self.min_altitude_spin = QDoubleSpinBox()
        self.min_altitude_spin.setRange(0.0, 10000.0)
        self.min_altitude_spin.setValue(1000.0)  # Valeur par défaut 150m
        self.min_altitude_spin.setSingleStep(10.0)
        min_alt_layout.addWidget(self.min_altitude_spin)
        layout.addLayout(min_alt_layout)
        
        # Configuration du buffer pour les captures
        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(QLabel("Zone de capture (m):"))
        self.buffer_spin = QDoubleSpinBox()
        self.buffer_spin.setRange(50.0, 10000.0)
        self.buffer_spin.setValue(1000.0)  # 200m par défaut
        self.buffer_spin.setSingleStep(50.0)
        buffer_layout.addWidget(self.buffer_spin)
        layout.addLayout(buffer_layout)
        
        # Sélection du dossier de sortie
        layout.addWidget(QLabel("Dossier de sortie pour les captures:"))
        output_layout = QHBoxLayout()
        self.output_folder_edit = QLineEdit()
        # Valeur par défaut : dossier captures_altitude dans le projet ou home
        default_folder = os.path.join(
            QgsProject.instance().homePath() or os.path.expanduser("~"),
            "captures_altitude"
        )
        self.output_folder_edit.setText(default_folder)
        self.browse_button = QPushButton("Parcourir...")
        self.browse_button.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(self.output_folder_edit)
        output_layout.addWidget(self.browse_button)
        layout.addLayout(output_layout)
        
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
    
    def browse_output_folder(self):
        """Ouvre un dialogue pour sélectionner le dossier de sortie"""
        current_folder = self.output_folder_edit.text()
        if not current_folder or not os.path.exists(current_folder):
            current_folder = os.path.expanduser("~")
            
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de sortie pour les captures",
            current_folder
        )
        
        if folder:
            self.output_folder_edit.setText(folder)
    
    def get_output_folder(self):
        """Retourne le dossier de sortie sélectionné"""
        return self.output_folder_edit.text()