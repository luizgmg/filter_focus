# -*- coding: utf-8 -*-
"""Centralização do canvas na(s) feição(ões) selecionada(s) da camada de referência."""
from qgis.core import (QgsCoordinateTransform, QgsFeatureRequest,
                       QgsProject, QgsRectangle)

BUFFER_FACTOR = 1.10        # folga de 10% ao redor da extensão
MIN_SIZE_METERS = 50.0      # lado mínimo para pontos/extensões nulas (SRC projetado)
MIN_SIZE_DEGREES = 0.0005   # idem, SRC geográfico (~55 m)


def selection_extent(layer):
    """Extensão combinada das feições selecionadas, no SRC da camada. None se vazia."""
    fids = layer.selectedFeatureIds()
    if not fids:
        return None
    req = QgsFeatureRequest().setFilterFids(fids)
    rect = QgsRectangle()
    rect.setMinimal()
    found = False
    for feat in layer.getFeatures(req):
        geom = feat.geometry()
        if geom is None or geom.isEmpty():
            continue
        rect.combineExtentWith(geom.boundingBox())
        found = True
    return rect if found else None


def _enforce_min_size(rect, geographic):
    min_size = MIN_SIZE_DEGREES if geographic else MIN_SIZE_METERS
    w, h = rect.width(), rect.height()
    if w < min_size or h < min_size:
        cx, cy = rect.center().x(), rect.center().y()
        half_w, half_h = max(w, min_size) / 2.0, max(h, min_size) / 2.0
        rect = QgsRectangle(cx - half_w, cy - half_h, cx + half_w, cy + half_h)
    return rect


def focus(canvas, layer):
    """Centraliza e ajusta o zoom do canvas na seleção da camada. Retorna True se agiu."""
    rect = selection_extent(layer)
    if rect is None:
        return False
    dest_crs = canvas.mapSettings().destinationCrs()
    if layer.crs() != dest_crs:
        tr = QgsCoordinateTransform(layer.crs(), dest_crs, QgsProject.instance().transformContext())
        rect = tr.transformBoundingBox(rect)
    rect = _enforce_min_size(rect, dest_crs.isGeographic())
    rect.scale(BUFFER_FACTOR)
    try:
        canvas.setExtent(rect, True)   # True: respeita a proporção da tela
    except TypeError:                  # QGIS antigo sem o parâmetro 'magnified'
        canvas.setExtent(rect)
    canvas.refresh()
    return True
