# -*- coding: utf-8 -*-
"""
Plugin d'altitude relative pour QGIS
"""

def classFactory(iface):
    """Charge le plugin AltitudeRelative"""
    from .src.plugin import AltitudeRelativePlugin
    return AltitudeRelativePlugin(iface)