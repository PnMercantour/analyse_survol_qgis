# -*- coding: utf-8 -*-
"""
Analyseur d'altitude pour la détection de segments sous altitude minimale
"""

from qgis.core import QgsGeometry, QgsPointXY, QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import QProgressDialog, QApplication
from qgis.PyQt.QtCore import Qt

from .visualization.map_capture import MapCapturer


class AltitudeAnalyzer:
    """Classe dédiée à l'analyse des segments d'altitude"""
    
    def __init__(self, iface):
        self.iface = iface
        self.group_count = 0
    
    def analyze_segments(self, source_layer, min_altitude, buffer_size, capture_folder):
        """
        Analyse les segments et génère les captures pour ceux sous l'altitude minimale
        
        Args:
            source_layer: Couche source à analyser
            min_altitude: Altitude minimale de référence
            buffer_size: Taille du buffer pour les captures
            capture_folder: Dossier de destination des captures
            
        Returns:
            list: Liste des segments détectés (count, min_z, captured_path, distance)
        """
        capturer = MapCapturer(self.iface, capture_folder)
        low_segments = []
        self.group_count = 0
        
        # État du groupe courant
        group_state = self._init_group_state()
        

        progress = QProgressDialog("Traitement en cours...", "Annuler", 0, 100, self.iface.mainWindow())
        progress.setWindowTitle("Progression")
        progress.setWindowModality(Qt.WindowModal)  # Bloque l'accès à QGIS pendant le traitement
        progress.show()
        total = source_layer.featureCount()

        for i, feature in enumerate(source_layer.getFeatures()):
            z_avg = self._get_feature_altitude(feature)
            if z_avg is None:
                continue
                
            if z_avg < min_altitude:
                self._process_low_altitude_segment(
                    feature, z_avg, group_state, capturer, buffer_size, low_segments
                )
            else:
                self._finalize_current_group(group_state, capturer, buffer_size, low_segments)
            progress.setValue( int((i/total) * 100) )
            QApplication.processEvents()  # Permet à QGIS de rester réactif
            if progress.wasCanceled():
                break
        progress.close()
        # Finaliser le dernier groupe si nécessaire
        self._finalize_current_group(group_state, capturer, buffer_size, low_segments)
        return low_segments
    
    def _init_group_state(self):
        """Initialise l'état d'un nouveau groupe"""
        return {
            'features': [],
            'min_z': float('inf'),
            'merged_geom': None,
            'start_point': None,
            'end_point': None,
            'distance': 0.0
        }
    
    def _get_feature_altitude(self, feature):
        """
        Calcule l'altitude moyenne d'une feature
        
        Args:
            feature: Feature à analyser
            
        Returns:
            float or None: Altitude moyenne ou None si pas de données Z
        """
        geom = feature.geometry()
        if geom.isEmpty():
            return None
            
        vertices = list(geom.vertices())
        if not vertices:
            return None
            
        z_values = [v.z() for v in vertices if v.is3D()]
        return sum(z_values) / len(z_values) if z_values else None
    
    def _process_low_altitude_segment(self, feature, z_avg, group_state, capturer, buffer_size, low_segments):
        """
        Traite un segment sous l'altitude minimale
        
        Args:
            feature: Feature du segment
            z_avg: Altitude moyenne du segment
            group_state: État du groupe courant
            capturer: Instance de MapCapturer
            buffer_size: Taille du buffer
            low_segments: Liste des segments détectés
        """
        geom = feature.geometry()
        vertices = list(geom.vertices())
        segment_start = QgsPointXY(vertices[0].x(), vertices[0].y())
        
        # Vérifier la continuité avec le groupe précédent
        if not self._is_consecutive_segment(segment_start, group_state['end_point']):
            self._finalize_current_group(group_state, capturer, buffer_size, low_segments)
        
        # Ajouter au groupe actuel
        if not group_state['features']:
            group_state.update({
                'merged_geom': QgsGeometry(geom),
                'start_point': segment_start,
                'distance': geom.length()
            })
        else:
            group_state['merged_geom'] = group_state['merged_geom'].combine(geom)
            group_state['distance'] += geom.length()
            
        group_state.update({
            'end_point': QgsPointXY(vertices[-1].x(), vertices[-1].y()),
            'min_z': min(group_state['min_z'], z_avg)
        })
        group_state['features'].append(feature.id())
    
    def _is_consecutive_segment(self, segment_start, previous_end, tolerance=0.001):
        """
        Vérifie si un segment est consécutif au précédent
        
        Args:
            segment_start: Point de début du segment courant
            previous_end: Point de fin du segment précédent
            tolerance: Tolérance pour la distance (défaut: 0.001)
            
        Returns:
            bool: True si les segments sont consécutifs
        """
        if not previous_end:
            return True
            
        distance = ((segment_start.x() - previous_end.x()) ** 2 + 
                   (segment_start.y() - previous_end.y()) ** 2) ** 0.5
        return distance <= tolerance
    
    def _finalize_current_group(self, group_state, capturer, buffer_size, low_segments):
        """
        Finalise et sauvegarde le groupe courant
        
        Args:
            group_state: État du groupe à finaliser
            capturer: Instance de MapCapturer
            buffer_size: Taille du buffer
            low_segments: Liste des segments détectés
        """
        if not group_state['features']:
            return
            
        self.group_count += 1
        distance_text = f"{group_state['distance']:.0f}m"
        filename = f"groupe_{self.group_count}_alt{group_state['min_z']:.0f}m_{distance_text}.png"
        
        try:
            captured_path = capturer.capture_segment_with_markers(
                group_state['merged_geom'], 
                group_state['start_point'], 
                group_state['end_point'],
                distance_text, 
                buffer_size=buffer_size, 
                min_altitude=group_state['min_z'], 
                filename=filename
            )
            
            if captured_path:
                low_segments.append((
                    len(group_state['features']), 
                    group_state['min_z'], 
                    captured_path, 
                    group_state['distance']
                ))
                
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Erreur capture groupe {self.group_count}: {str(e)}", 
                level=Qgis.Warning
            )
        
        # Réinitialiser l'état du groupe
        group_state.update(self._init_group_state())
    
    def format_results_message(self, low_segments, min_altitude, capture_folder):
        """
        Formate le message de résultats
        
        Args:
            low_segments: Liste des segments détectés
            min_altitude: Altitude minimale utilisée
            capture_folder: Dossier des captures
            
        Returns:
            str: Message formaté
        """
        if low_segments:
            total_segments = sum(count for count, _, _, _ in low_segments)
            total_distance = sum(distance for _, _, _, distance in low_segments)
            
            msg = (f"{total_segments} segments répartis en {len(low_segments)} groupe(s) "
                  f"sous l'altitude minimale de {min_altitude}m.\n"
                  f"Distance totale: {total_distance:.0f}m\n")
            
            for i, (count, alt, _, distance) in enumerate(low_segments, 1):
                msg += f"\n- Groupe {i}: {count} segments à {alt:.0f}m ({distance:.0f}m)"
                
            msg += f"\n\nCaptures sauvegardées dans {capture_folder}"
        else:
            msg = f"Aucun segment sous l'altitude minimale de {min_altitude}m."
            
        return msg