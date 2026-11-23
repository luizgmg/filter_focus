# -*- coding: utf-8 -*-
"""Compatibilidade QGIS 3.x (Qt5) e QGIS 4.x (Qt6): enums escopados x não escopados."""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAbstractItemView, QComboBox, QCompleter, QDialogButtonBox
from qgis.core import Qgis, QgsFeatureRequest, QgsVectorFileWriter

try:                                   # Qt6: QAction fica em QtGui
    from qgis.PyQt.QtGui import QAction
except ImportError:                    # Qt5: QAction fica em QtWidgets
    from qgis.PyQt.QtWidgets import QAction


def _enum(owner, scope, name):
    """Acessa o enum no estilo escopado (Qt.CheckState.Checked) ou no antigo (Qt.Checked)."""
    scoped = getattr(owner, scope, None)
    if scoped is not None and hasattr(scoped, name):
        return getattr(scoped, name)
    return getattr(owner, name)


ITEM_ENABLED = _enum(Qt, "ItemFlag", "ItemIsEnabled")
ITEM_CHECKABLE = _enum(Qt, "ItemFlag", "ItemIsUserCheckable")
ITEM_SELECTABLE = _enum(Qt, "ItemFlag", "ItemIsSelectable")
ITEM_TRISTATE = _enum(Qt, "ItemFlag", "ItemIsAutoTristate")
CHECKED = _enum(Qt, "CheckState", "Checked")
UNCHECKED = _enum(Qt, "CheckState", "Unchecked")
MATCH_FIXED = _enum(Qt, "MatchFlag", "MatchFixedString")
MATCH_CONTAINS = _enum(Qt, "MatchFlag", "MatchContains")
ASC = _enum(Qt, "SortOrder", "AscendingOrder")
ISO_DATE = _enum(Qt, "DateFormat", "ISODate")
DOCK_RIGHT = _enum(Qt, "DockWidgetArea", "RightDockWidgetArea")

BTN_OK = _enum(QDialogButtonBox, "StandardButton", "Ok")
BTN_CANCEL = _enum(QDialogButtonBox, "StandardButton", "Cancel")
NO_EDIT = _enum(QAbstractItemView, "EditTrigger", "NoEditTriggers")
NO_INSERT = _enum(QComboBox, "InsertPolicy", "NoInsert")
POPUP = _enum(QCompleter, "CompletionMode", "PopupCompletion")

LEVEL_INFO = _enum(Qgis, "MessageLevel", "Info")
LEVEL_SUCCESS = _enum(Qgis, "MessageLevel", "Success")
LEVEL_WARNING = _enum(Qgis, "MessageLevel", "Warning")
LEVEL_CRITICAL = _enum(Qgis, "MessageLevel", "Critical")
FLAG_NO_GEOM = _enum(QgsFeatureRequest, "Flag", "NoGeometry")
WRITE_OK = _enum(QgsVectorFileWriter, "WriterError", "NoError")


def exec_dialog(dlg):
    """exec_() no PyQt5, exec() no PyQt6."""
    return dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
