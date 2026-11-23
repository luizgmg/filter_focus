# -*- coding: utf-8 -*-
"""Exportação da cópia da camada de referência (Shapefile) sem sobrescrever."""
import os

from qgis.core import QgsProject, QgsVectorFileWriter, QgsVectorLayer
from ..compat import WRITE_OK
from ..i18n import tr

_SHP_PARTS = (".shp", ".shx", ".dbf", ".prj", ".cpg")


def normalize_path(path):
    path = os.path.normpath(path.strip())
    return path if path.lower().endswith(".shp") else path + ".shp"


def _write(layer, path, opts):
    """Grava a camada usando a API disponível (V3 >= 3.20, V2 >= 3.10, legada antes)."""
    ctx = QgsProject.instance().transformContext()
    w = QgsVectorFileWriter
    if hasattr(w, "writeAsVectorFormatV3"):
        res = w.writeAsVectorFormatV3(layer, path, ctx, opts)
    elif hasattr(w, "writeAsVectorFormatV2"):
        res = w.writeAsVectorFormatV2(layer, path, ctx, opts)
    else:
        res = w.writeAsVectorFormat(layer, path, "UTF-8", layer.crs(), "ESRI Shapefile")
    return res[0], res[1]


def export_reference(layer, path):
    """Retorna (camada_copia | None, mensagem, campos_com_nome_longo)."""
    path = normalize_path(path)
    base = os.path.splitext(path)[0]
    existing = [base + ext for ext in _SHP_PARTS if os.path.exists(base + ext)]
    if existing:
        return None, tr("The file already exists and will not be overwritten: {}").format(path), []
    folder = os.path.dirname(path)
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError as exc:
        return None, tr("Could not create folder '{}': {}").format(folder, exc), []

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName = "ESRI Shapefile"
    opts.fileEncoding = "UTF-8"
    err, errmsg = _write(layer, path, opts)
    if err != WRITE_OK:
        return None, tr("Export failed: {}").format(errmsg), []

    copy = QgsVectorLayer(path, os.path.basename(base), "ogr")
    if not copy.isValid():
        return None, tr("The copy was written but could not be loaded: {}").format(path), []

    # adiciona ao projeto logo abaixo da referência (mesmo grupo)
    prj = QgsProject.instance()
    prj.addMapLayer(copy, False)
    node = prj.layerTreeRoot().findLayer(layer.id())
    if node is not None and node.parent() is not None:
        parent = node.parent()
        parent.insertLayer(parent.children().index(node) + 1, copy)
    else:
        prj.layerTreeRoot().addLayer(copy)

    long_names = [f.name() for f in layer.fields() if len(f.name()) > 10]
    return copy, tr("Copy created: {}").format(path), long_names


def copy_field_name(ref_field, copy_layer):
    """Nome do campo de relacionamento na cópia (SHP trunca em 10 caracteres)."""
    names = copy_layer.fields().names()
    for cand in (ref_field, ref_field[:10]):
        if cand in names:
            return cand
    low = {n.lower(): n for n in names}
    return low.get(ref_field.lower()) or low.get(ref_field[:10].lower())
