# -*- coding: utf-8 -*-
"""
Plugin d'altitude relative pour QGIS
"""

import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsMessageLog, Qgis, QgsGeometry, QgsPointXY

from .gui.dialog import AltitudeRelativeDialog
from .gui.line_segment_dialog import LineSegmentDialog
from .gui.altitude_check_dialog import AltitudeCheckDialog
from .core.calculator import AltitudeCalculator
from .core.visualization.line_segment_visualizer import LineSegmentVisualizer
from .core.visualization.map_capture import MapCapturer
import os


class AltitudeRelativePlugin:
    """Plugin principal"""
    
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.calculator = AltitudeCalculator()
        self.visualizer = LineSegmentVisualizer()
        
        # Initialiser les variables
        self.actions = []
        self.menu = "Altitude Relative"
        self.toolbar = self.iface.addToolBar("AltitudeRelative")
        self.toolbar.setObjectName("AltitudeRelative")
        
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
            callback=self.run,
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
        
    def run(self):
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
    
    def run_altitude_check(self):
        """Exécuter la détection des segments sous altitude minimale"""
        dialog = AltitudeCheckDialog(self.iface.mainWindow())
        
        # Vérifier qu'il y a des couches appropriées
        if dialog.layer_combo.currentLayer() is None:
            self.iface.messageBar().pushMessage(
                "Erreur", "Aucune couche ligne disponible", 
                level=Qgis.Critical
            )
            return
            
        if dialog.exec_() == dialog.Accepted:
            try:
                source_layer = dialog.layer_combo.currentLayer()
                min_altitude = dialog.min_altitude_spin.value()
                buffer_size = dialog.buffer_spin.value()
                
                # Utiliser le dossier de sortie sélectionné par l'utilisateur
                capture_folder = dialog.get_output_folder()
                
                capturer = MapCapturer(self.iface, capture_folder)
                low_segments = []
                                
                # Variables pour suivre les segments consécutifs
                current_group = []
                current_min_z = float('inf')
                current_merged_geom = None
                current_start_point = None
                current_end_point = None
                current_distance = 0.0
                group_count = 0
                
                # Chercher les segments avec une altitude Z trop basse
                for feature in source_layer.getFeatures():
                    geom = feature.geometry()
                    if geom.isEmpty():
                        continue
                        
                    vertices = list(geom.vertices())
                    if not vertices:
                        continue
                        
                    # Calculer l'altitude moyenne du segment
                    z_values = [v.z() for v in vertices if v.is3D()]
                    if not z_values:
                        continue
                        
                    z_avg = sum(z_values) / len(z_values)
                    
                    if z_avg < min_altitude:
                        # Vérifier si le segment est consécutif au groupe actuel
                        segment_start = QgsPointXY(vertices[0].x(), vertices[0].y())
                        is_consecutive = True
                        
                        if current_group and current_end_point:
                            # Vérifier si le début de ce segment correspond à la fin du précédent
                            # Tolérance de 0.001 mètre pour les erreurs d'arrondi
                            tolerance = 0.001
                            distance_to_previous_end = ((segment_start.x() - current_end_point.x()) ** 2 + 
                                                      (segment_start.y() - current_end_point.y()) ** 2) ** 0.5
                            is_consecutive = distance_to_previous_end <= tolerance
                        
                        # Si ce n'est pas consécutif, finaliser le groupe actuel
                        if not is_consecutive and current_group:
                            group_count += 1
                            distance_text = f"{current_distance:.0f}m"
                            captured_path = capturer.capture_segment_with_markers(
                                current_merged_geom,
                                current_start_point,
                                current_end_point,
                                distance_text,
                                buffer_size=buffer_size,
                                min_altitude=current_min_z,
                                filename=f"groupe_{group_count}_alt{current_min_z:.0f}m_{distance_text}.png"
                            )
                            if captured_path:
                                low_segments.append((len(current_group), current_min_z, captured_path, current_distance))
                            
                            # Réinitialiser pour le nouveau groupe
                            current_group = []
                            current_min_z = float('inf')
                            current_merged_geom = None
                            current_start_point = None
                            current_end_point = None
                            current_distance = 0.0
                        
                        # Ajouter ce segment au groupe actuel (nouveau ou existant)
                        if not current_group:
                            current_merged_geom = QgsGeometry(geom)
                            current_start_point = segment_start
                            current_distance = geom.length()
                        else:
                            current_merged_geom = current_merged_geom.combine(geom)
                            current_distance += geom.length()
                            
                        current_end_point = QgsPointXY(vertices[-1].x(), vertices[-1].y())
                        current_group.append(feature.id())
                        current_min_z = min(current_min_z, z_avg)
                    else:
                        # Si on a un groupe en cours, on l'exporte
                        if current_group:
                            group_count += 1
                            distance_text = f"{current_distance:.0f}m"
                            captured_path = capturer.capture_segment_with_markers(
                                current_merged_geom,
                                current_start_point,
                                current_end_point,
                                distance_text,
                                buffer_size=buffer_size,
                                min_altitude=current_min_z,
                                filename=f"groupe_{group_count}_alt{current_min_z:.0f}m_{distance_text}.png"
                            )
                            if captured_path:
                                low_segments.append((len(current_group), current_min_z, captured_path, current_distance))
                            
                            # Réinitialiser pour le prochain groupe
                            current_group = []
                            current_min_z = float('inf')
                            current_merged_geom = None
                            current_start_point = None
                            current_end_point = None
                            current_distance = 0.0
                
                # Ne pas oublier le dernier groupe
                if current_group:
                    group_count += 1
                    distance_text = f"{current_distance:.0f}m"
                    captured_path = capturer.capture_segment_with_markers(
                        current_merged_geom,
                        current_start_point,
                        current_end_point,
                        distance_text,
                        buffer_size=buffer_size,
                        min_altitude=current_min_z,
                        filename=f"groupe_{group_count}_alt{current_min_z:.0f}m_{distance_text}.png"
                    )
                    if captured_path:
                        low_segments.append((len(current_group), current_min_z, captured_path, current_distance))
                
                # Afficher un message avec le résultat
                if low_segments:
                    total_segments = sum(count for count, _, _, _ in low_segments)
                    total_distance = sum(distance for _, _, _, distance in low_segments)
                    msg = f"{total_segments} segments répartis en {len(low_segments)} groupe(s) "
                    msg += f"sous l'altitude minimale de {min_altitude}m.\n"
                    msg += f"Distance totale: {total_distance:.0f}m\n"
                    for count, alt, path, distance in low_segments:
                        msg += f"\n- Groupe de {count} segments à {alt:.0f}m ({distance:.0f}m)"
                    msg += f"\n\nCaptures avec marqueurs sauvegardées dans {capture_folder}"
                    level = Qgis.Success
                else:
                    msg = f"Aucun segment sous l'altitude minimale de {min_altitude}m."
                    level = Qgis.Success
                    
                self.iface.messageBar().pushMessage("Terminé", msg, level=level)
                
            except Exception as e:
                self.iface.messageBar().pushMessage(
                    "Erreur", f"Erreur lors de la détection: {str(e)}", 
                    level=Qgis.Critical
                )
                QgsMessageLog.logMessage(
                    f"Erreur détection segments: {str(e)}", 
                    level=Qgis.Critical
                )

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