# -*- coding: utf-8 -*-
"""
Calcul d'altitude relative pour les polylignes
"""

from qgis.core import (QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeature,
                      QgsGeometry, QgsPointXY, QgsField, QgsFields,
                      QgsVectorDataProvider, QgsWkbTypes, QgsRasterDataProvider,
                      QgsProcessingException, QgsMessageLog, Qgis, QgsPoint,
                      QgsCoordinateReferenceSystem, QgsCoordinateTransform)
from qgis.PyQt.QtCore import QMetaType
import processing
import numpy as np


def replace_z(geom: QgsGeometry, new_z: np.ndarray) -> QgsGeometry:
    """
    Remplace les valeurs Z d'une géométrie par celles données dans new_z.
    Fonctionne pour LineStringZ et PolygonZ simples.
    
    Parameters
    ----------
    geom : QgsGeometry
        Géométrie d'entrée (doit avoir des Z).
    new_z : np.ndarray
        Tableau 1D avec les nouvelles altitudes (même nombre de sommets).
    
    Returns
    -------
    QgsGeometry
        Nouvelle géométrie avec Z remplacés.
    """
    g = geom.constGet()
    verts = list(g.vertices())

    if len(verts) != len(new_z):
        raise ValueError(f"Nombre de sommets ({len(verts)}) != taille de new_z ({len(new_z)})")

    # Reconstruire les points avec les nouveaux Z
    new_points = [QgsPoint(v.x(), v.y(), float(z)) for v, z in zip(verts, new_z)]

    if g.wkbType() in (QgsWkbTypes.LineStringZ, QgsWkbTypes.LineString25D):
        return QgsGeometry.fromPolyline(new_points)
    elif g.wkbType() in (QgsWkbTypes.PolygonZ, QgsWkbTypes.Polygon25D):
        return QgsGeometry.fromPolygonXY([new_points])
    else:
        raise NotImplementedError(f"replace_z non implémenté pour {g.wkbType()}")


class AltitudeCalculator:
    def __init__(self):
        pass

    def create_output_layer(self, source_layer, output_crs=None):
        """Créer une nouvelle couche de sortie"""
        # Créer une couche en mémoire
        geom_type = source_layer.geometryType()
        if geom_type == QgsWkbTypes.LineGeometry:
            geom_string = "LineStringZ"
        else:
            geom_string = "MultiLineStringZ"
            
        # Utiliser le CRS de sortie spécifié ou celui de la couche source
        if output_crs:
            crs = output_crs.authid()
        else:
            crs = source_layer.crs().authid()
        uri = f"{geom_string}?crs={crs}"
        
        output_layer = QgsVectorLayer(uri, 
                                    f"{source_layer.name()}_altitude_relative", 
                                    "memory")
        
        # Copier les champs existants et ajouter les nouveaux
        fields = source_layer.fields()
        new_fields = QgsFields()
        for field in fields:
            new_fields.append(field)
            
        # Champs pour les altitudes
        new_fields.append(QgsField("alt_sol", QMetaType.Type.Double))
        new_fields.append(QgsField("alt_relative", QMetaType.Type.Double))
        
        output_layer.dataProvider().addAttributes(new_fields)
        output_layer.updateFields()
        
        # Déterminer si une transformation de coordonnées est nécessaire
        needs_transform = output_crs and source_layer.crs() != output_crs
        transform = None
        if needs_transform:
            transform = QgsCoordinateTransform(
                source_layer.crs(), 
                output_crs, 
                QgsProject.instance()
            )
        
        # Copier les features
        features = []
        for feature in source_layer.getFeatures():
            new_feature = QgsFeature(output_layer.fields())
            
            # Copier et transformer la géométrie si nécessaire
            geom = feature.geometry()
            if transform:
                geom.transform(transform)
            new_feature.setGeometry(geom)
            
            # Copier les attributs existants
            for field in source_layer.fields():
                new_feature[field.name()] = feature[field.name()]
                
            features.append(new_feature)
            
        output_layer.dataProvider().addFeatures(features)
        return output_layer
    
    def add_altitude_fields(self, layer):
        """Ajouter les champs d'altitude à une couche existante"""
        provider = layer.dataProvider()
        
        # Vérifier si les champs existent déjà
        field_names = [field.name() for field in layer.fields()]
        
        new_fields = []
        if "alt_sol" not in field_names:
            new_fields.append(QgsField("alt_sol", QMetaType.Type.Double))
        if "alt_relative" not in field_names:
            new_fields.append(QgsField("alt_relative", QMetaType.Type.Double))
            
        if new_fields:
            provider.addAttributes(new_fields)
            layer.updateFields()

    def calculate_relative_altitudes(self, mnt_layer, polyline_layer, 
                                   altitude_field, use_z_coordinate, progress_callback=None):
        """Calculer les altitudes relatives pour chaque polyligne"""
        try:
            # Étape 1: Utiliser l'outil Draper pour obtenir les altitudes du terrain
            if progress_callback:
                progress_callback(0, 0)  # Mode indéterminé pendant le drapage
            
            drape_result = processing.run("native:setzfromraster", {
                'INPUT': polyline_layer,
                'RASTER': mnt_layer,
                'BAND': 1,
                'NODATA': 0,
                'SCALE': 1,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            })
            
            draped_layer = drape_result['OUTPUT']
            
            # Étape 2: Calculer les altitudes relatives
            if progress_callback:
                progress_callback(0, polyline_layer.featureCount())

            polyline_layer.startEditing()
            
            # Créer des dictionnaires pour mapper les features
            original_features = {f.id(): f for f in polyline_layer.getFeatures()}
            draped_features = {f.id(): f for f in draped_layer.getFeatures()}
            
            # Note: La transformation de coordonnées est déjà gérée lors de la création de la couche de sortie
            
            for i, original_feature in enumerate(polyline_layer.getFeatures()):
                if progress_callback:
                    progress_callback(i, None)
                
                fid = original_feature.id()
                if fid not in draped_features:
                    continue
                    
                draped_feature = draped_features[fid]
                
                # Récupérer les coordonnées
                orig_vertices = np.array([[v.x(), v.y(), v.z()] for v in original_feature.geometry().constGet().vertices()])
                drape_vertices = np.array([[v.x(), v.y(), v.z()] for v in draped_feature.geometry().constGet().vertices()])
                
                if orig_vertices.shape[0] != drape_vertices.shape[0]:
                    QgsMessageLog.logMessage(
                        f"Nombre de sommets différent pour feature {fid}", 
                        level=Qgis.Critical
                    )
                    continue
                
                # Calculer l'altitude relative : Z_absolu - Z_sol
                altitude_sol = np.mean(drape_vertices[:, 2])
                altitude_absolue = np.mean(orig_vertices[:, 2])
                altitude_relative = altitude_absolue - altitude_sol
                
                # Mettre à jour les champs
                polyline_layer.changeAttributeValue(
                    fid, 
                    polyline_layer.fields().indexFromName("alt_sol"), 
                    float(altitude_sol)
                )
                polyline_layer.changeAttributeValue(
                    fid, 
                    polyline_layer.fields().indexFromName("alt_relative"), 
                    float(altitude_relative)
                )
                
                # Mettre à jour la géométrie avec les Z relatifs
                new_z = orig_vertices[:, 2] - drape_vertices[:, 2]
                new_geom = replace_z(original_feature.geometry(), new_z)
                
                polyline_layer.changeGeometry(fid, new_geom)
            
            polyline_layer.commitChanges()
            
            if progress_callback:
                progress_callback(polyline_layer.featureCount(), None)
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Erreur lors du calcul: {str(e)}", 
                                   level=Qgis.Critical)
            return False

    def get_z_coordinate_from_geometry(self, geometry):
        """Extraire la coordonnée Z moyenne d'une géométrie polyligne"""
        try:
            if geometry.isEmpty():
                return None
                
            # Vérifier si la géométrie a des coordonnées Z
            if not QgsWkbTypes.hasZ(geometry.wkbType()):
                return None
                
            z_values = []
            
            # Parcourir tous les sommets de la géométrie
            vertices = geometry.vertices()
            while vertices.hasNext():
                vertex = vertices.next()
                if vertex.is3D() and not vertex.isEmpty():
                    z_values.append(vertex.z())
            
            # Retourner la moyenne des valeurs Z
            if z_values:
                return sum(z_values) / len(z_values)
            else:
                return None
                
        except Exception as e:
            QgsMessageLog.logMessage(f"Erreur extraction coordonnée Z: {str(e)}", 
                                   level=Qgis.Warning)
            return None