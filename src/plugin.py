# -*- coding: utf-8 -*-
"""
Plugin d'altitude relative pour QGIS
"""

import os
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QPushButton, QVBoxLayout, QTextEdit, QDialog, QDialogButtonBox, QScrollArea, QWidget
from qgis.PyQt.QtCore import QUrl
from qgis.core import QgsProject, QgsMessageLog, Qgis

from .gui.dialog import AltitudeRelativeDialog
from .gui.line_segment_dialog import LineSegmentDialog
from .gui.altitude_check_dialog import AltitudeCheckDialog
from .core.calculator import AltitudeCalculator
from .core.visualization.line_segment_visualizer import LineSegmentVisualizer
from .core.altitude_analyzer import AltitudeAnalyzer
import os


class AltitudeRelativePlugin:
    """Plugin principal"""
    
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.calculator = AltitudeCalculator()
        self.visualizer = LineSegmentVisualizer()
        self.altitude_analyzer = AltitudeAnalyzer(iface)
        
        # Initialiser les variables
        self.actions = []
        self.menu = "Analyse Survol"
        self.toolbar = self.iface.addToolBar("Analyse Survol")
        self.toolbar.setObjectName("Analyse Survol")

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        """Ajouter une action à la barre d'outils et au menu"""
        
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        
        if status_tip is not None:
            action.setStatusTip(status_tip)
            
        if whats_this is not None:
            action.setWhatsThis(whats_this)
            
        if add_to_toolbar:
            self.toolbar.addAction(action)
            
        if add_to_menu:
            self.iface.addPluginToVectorMenu(self.menu, action)
            
        self.actions.append(action)
        return action
        
    def initGui(self):
        """Créer l'interface graphique du plugin"""
        icon_path = os.path.join(self.plugin_dir, '../resources', 'icon.png')
        icon_path_visualizer = os.path.join(self.plugin_dir, '../resources', 'icon_visualize.png')
        icon_path_capture = os.path.join(self.plugin_dir, '../resources', 'icon_report.png')

        # Action pour le calcul d'altitude
        self.add_action(
            icon_path,
            text="Calculer altitude relative",
            callback=self.run_relative_altitude_computation,
            parent=self.iface.mainWindow()
        )
        
        # Action pour la visualisation des segments
        self.add_action(
            icon_path_visualizer,
            text="Visualiser segments colorés",
            callback=self.run_visualization,
            parent=self.iface.mainWindow()
        )
        
        # Action pour la détection des segments sous altitude minimale
        self.add_action(
            icon_path_capture,  # À remplacer par une nouvelle icône
            text="Détecter segments sous altitude min.",
            callback=self.run_altitude_check,
            parent=self.iface.mainWindow()
        )
        
    def unload(self):
        """Nettoyer lors du déchargement du plugin"""
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar
        

######################################################################################
####    Callback des actions -> Affiche les boites de dialogue de chaque sous module
######################################################################################

    def run_relative_altitude_computation(self):
        """Exécuter le calcul d'altitude relative"""
        dialog = AltitudeRelativeDialog(self.iface.mainWindow())
        
        # Vérifier qu'il y a des couches appropriées
        if dialog.mnt_combo.currentLayer() is None:
            self.iface.messageBar().pushMessage(
                "Erreur", "Aucune couche raster (MNT) disponible", 
                level=Qgis.Critical
            )
            return
            
        # Afficher le dialogue et traiter le résultat
        if dialog.exec_() == dialog.Accepted:
            self.process_altitude_calculation(dialog)
            
    def run_visualization(self):
        """Exécuter la visualisation des segments colorés"""
        dialog = LineSegmentDialog(self.iface.mainWindow())
        
        # Vérifier qu'il y a des couches appropriées
        if dialog.layer_combo.currentLayer() is None:
            self.iface.messageBar().pushMessage(
                "Erreur", "Aucune couche ligne disponible", 
                level=Qgis.Critical
            )
            return
            
        if dialog.exec_() == dialog.Accepted:
            self.process_visualization(dialog)

    def run_altitude_check(self):
        """Exécuter la détection des segments sous altitude minimale"""
        dialog = AltitudeCheckDialog(self.iface.mainWindow())
        
        if dialog.layer_combo.currentLayer() is None:
            self.iface.messageBar().pushMessage(
                "Erreur", "Aucune couche ligne disponible", level=Qgis.Critical)
            return
            
        if dialog.exec_() == dialog.Accepted:
            try:
                # Utiliser l'analyseur d'altitude dédié
                low_segments = self.altitude_analyzer.analyze_segments(
                    dialog.layer_combo.currentLayer(),
                    dialog.min_altitude_spin.value(),
                    dialog.buffer_spin.value(),
                    dialog.get_output_folder()
                )
                
                # Afficher les résultats
                message = self.altitude_analyzer.format_results_message(
                    low_segments, 
                    dialog.min_altitude_spin.value(), 
                    dialog.get_output_folder()
                )
                
                info_dialog = QDialog(self.iface.mainWindow())
                info_dialog.setWindowTitle("Analyse terminée")
                info_dialog.resize(400, 300)

                layout = QVBoxLayout()

                # Message scrollable
                text_edit = QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setText(message)
                layout.addWidget(text_edit)

                # Bouton "Ouvrir le dossier" pleine largeur
                open_folder_button = QPushButton("Ouvrir le dossier")
                open_folder_button.setMaximumWidth(16777215)  # Permet de s'étendre sur toute la largeur
                open_folder_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(dialog.get_output_folder())))
                layout.addWidget(open_folder_button)

                # Bouton OK pour fermer
                ok_button = QPushButton("OK")
                ok_button.clicked.connect(info_dialog.accept)
                layout.addWidget(ok_button)
                info_dialog.setLayout(layout)
                info_dialog.exec_()
            except Exception as e:
                self.iface.messageBar().pushMessage(
                    "Erreur", f"Erreur lors de la détection: {str(e)}", level=Qgis.Critical)
                QgsMessageLog.logMessage(f"Erreur détection segments: {str(e)}", level=Qgis.Critical)

######################################################################################
####    Fonction de traitement pour les sous-modules altitude relative et visualisation
######################################################################################
# Le calcul des altitudes illicites est géré dans altitude_analyzer.py 

    def process_altitude_calculation(self, dialog):
        """Traiter le calcul d'altitude relative"""
        try:
            # Récupérer les couches sélectionnées
            mnt_layer = dialog.mnt_combo.currentLayer()
            polyline_layer = dialog.polyline_combo.currentLayer()
            altitude_field = dialog.altitude_field_combo.currentData()
            use_z_coordinate = not altitude_field
            output_crs = dialog.crs_selector.crs()
            
            # Créer ou modifier la couche
            if dialog.create_new_layer_check.isChecked():
                output_layer = self.calculator.create_output_layer(polyline_layer, output_crs)
            else:
                output_layer = polyline_layer
                self.calculator.add_altitude_fields(output_layer)
            
            # Définir la fonction de callback pour la progression
            def update_progress(value, maximum=None):
                if maximum is not None:
                    dialog.progress_bar.setRange(0, maximum)
                dialog.progress_bar.setValue(value)
            
            # Afficher la barre de progression
            dialog.progress_bar.setVisible(True)
            
            # Calculer les altitudes relatives
            success = self.calculator.calculate_relative_altitudes(
                mnt_layer, output_layer, altitude_field, use_z_coordinate, update_progress
            )
            
            if success:
                # Ajouter la nouvelle couche au projet si nécessaire
                if dialog.create_new_layer_check.isChecked():
                    QgsProject.instance().addMapLayer(output_layer)
                    
                # Rafraîchir la couche
                output_layer.triggerRepaint()
                
                self.iface.messageBar().pushMessage(
                    "Succès", "Calcul d'altitude relative terminé", 
                    level=Qgis.Success
                )
            else:
                self.iface.messageBar().pushMessage(
                    "Erreur", "Le calcul a échoué", 
                    level=Qgis.Critical
                )
            
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Erreur", f"Erreur lors du calcul: {str(e)}", 
                level=Qgis.Critical
            )
            QgsMessageLog.logMessage(f"Erreur altitude relative: {str(e)}", 
                                   level=Qgis.Critical)
        finally:
            dialog.progress_bar.setVisible(False)

            
    def process_visualization(self, dialog):
        """Traiter la visualisation des segments"""
        try:
            source_layer = dialog.layer_combo.currentLayer()
            segment_length = dialog.length_spin.value()
            
            # Configurer le visualiseur
            self.visualizer.segment_length = segment_length
            self.visualizer.color_stops = dialog.get_color_stops()  # Utiliser les couleurs configurées
            
            # Créer la couche de segments
            output_layer = self.visualizer.create_segment_layer(source_layer)
            
            # Ajouter la couche au projet
            if dialog.create_new_layer_check.isChecked():
                QgsProject.instance().addMapLayer(output_layer)
                
            # Message de succès
            self.iface.messageBar().pushMessage(
                "Succès", "Segments créés avec succès", 
                level=Qgis.Success
            )
            
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Erreur", f"Erreur lors de la création des segments: {str(e)}", 
                level=Qgis.Critical
            )
            QgsMessageLog.logMessage(
                f"Erreur visualisation segments: {str(e)}", 
                level=Qgis.Critical
            )
    

