# -*- coding: utf-8 -*-
"""Orquestra o ciclo de vida: configurar -> filtrar/centralizar a cada seleção -> restaurar."""
import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import Qgis, QgsProject

from .core.filter_manager import FilterManager
from .core.map_focus import focus
from .core.ref_copy import copy_field_name, export_reference
from .core.selection_watcher import SelectionWatcher
from .ui.config_dialog import ConfigDialog
from .ui.panel import NavPanel
from .i18n import tr

TITLE = "Filter Focus"


class FilterFocus:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.active = False
        self.ref = self.field = self.fm = self.watcher = self.panel = None
        self._warned = set()

    # ---------- QGIS ----------
    def initGui(self):
        self.action = QAction(QIcon(os.path.join(os.path.dirname(__file__), "icon.svg")), TITLE,
                              self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self._toggle)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&" + TITLE, self.action)

    def unload(self):
        self.stop()
        if self.action is not None:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&" + TITLE, self.action)
            self.action.deleteLater()
            self.action = None

    # ---------- fluxo ----------
    def _toggle(self, checked):
        if not checked:
            self.stop()
            return
        if self.active:
            return
        dlg = ConfigDialog(self.iface, self.iface.mainWindow())
        if dlg.exec_() and self.start(dlg.config()):
            return
        self.action.setChecked(False)

    def _msg(self, text, level=Qgis.Info, duration=6):
        self.iface.messageBar().pushMessage(TITLE, text, level=level, duration=duration)

    def start(self, cfg):
        prj = QgsProject.instance()
        ref = prj.mapLayer(cfg["ref_id"])
        targets = dict(cfg["targets"])

        if cfg["copy_path"]:
            copy, msg, long_names = export_reference(ref, cfg["copy_path"])
            if copy is None:
                self._msg(msg, Qgis.Critical, 10)
                return False
            cf = copy_field_name(cfg["ref_field"], copy)
            if cf is None:
                self._msg(tr("The copy does not have the field '{}'.").format(cfg["ref_field"]), Qgis.Critical, 10)
                return False
            targets[copy.id()] = cf
            self._msg(msg, Qgis.Success)
            if long_names:
                self._msg(tr("Fields longer than 10 characters were truncated in the Shapefile: {}").format(
                    ", ".join(long_names)), Qgis.Warning, 10)

        fm = FilterManager(targets)
        errors = fm.validate()
        if errors:
            QMessageBox.warning(self.iface.mainWindow(), TITLE, "\n".join(errors))
            return False
        fm.snapshot()
        for note in fm.notes:
            self._msg(note, Qgis.Warning, 10)

        self.ref, self.field, self.fm = ref, cfg["ref_field"], fm
        self._warned.clear()
        self.watcher = SelectionWatcher(ref)
        self.watcher.selectionSettled.connect(self._on_selection)
        self.watcher.start()
        prj.layerWillBeRemoved.connect(self._on_layer_removed)
        prj.cleared.connect(self.stop)
        self.active = True

        self.panel = NavPanel(ref, cfg["ref_field"], cfg["panel_fields"], self.iface.mainWindow())
        self.panel.stopRequested.connect(self.stop)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.panel)

        if ref.selectedFeatureCount():
            self._on_selection()
        return True

    def _on_selection(self):
        if not self.active or self.ref is None:
            return
        idx = self.ref.fields().indexFromName(self.field)
        values = [f[idx] for f in self.ref.getSelectedFeatures()]
        self.fm.apply(values)
        if values:
            focus(self.iface.mapCanvas(), self.ref)
        new_fail = self.fm.failed - self._warned
        if new_fail:
            names = [QgsProject.instance().mapLayer(l).name() for l in new_fail
                     if QgsProject.instance().mapLayer(l)]
            self._msg(tr("Could not filter (layer in edit mode or unsupported source): ")
                      + ", ".join(names), Qgis.Warning, 10)
            self._warned |= new_fail
        if self.panel is not None:
            self.panel.sync_from_selection()

    def _on_layer_removed(self, layer_id):
        if self.ref is not None and layer_id == self.ref.id():
            self.stop()

    def stop(self):
        if not self.active:
            return
        self.active = False
        prj = QgsProject.instance()
        for sig, slot in ((prj.layerWillBeRemoved, self._on_layer_removed), (prj.cleared, self.stop)):
            try:
                sig.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        if self.watcher is not None:
            self.watcher.stop()
            self.watcher.deleteLater()
            self.watcher = None
        if self.fm is not None:
            self.fm.restore()        # a cópia da referência NÃO é removida
            self.fm = None
        if self.panel is not None:
            self.panel.close()
            self.panel.deleteLater()
            self.panel = None
        self.ref = None
        if self.action is not None:
            self.action.setChecked(False)
        self._msg(tr("Filters restored."), Qgis.Info, 4)
