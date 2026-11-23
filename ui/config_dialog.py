# -*- coding: utf-8 -*-
"""Diálogo de configuração: referência, campo, árvore de destinos e cópia SHP."""
import os

from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                                 QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                                 QLabel, QLineEdit, QListWidget, QListWidgetItem,
                                 QMessageBox, QPushButton,
                                 QTreeWidget, QTreeWidgetItem, QVBoxLayout)
from qgis.core import QgsLayerTree, QgsProject, QgsVectorLayer
from ..compat import (BTN_CANCEL, BTN_OK, CHECKED, ITEM_CHECKABLE, ITEM_ENABLED,
                      ITEM_SELECTABLE, ITEM_TRISTATE, MATCH_FIXED, UNCHECKED)
from ..i18n import tr

_FLAGS_LAYER = ITEM_ENABLED | ITEM_CHECKABLE | ITEM_SELECTABLE
_FLAGS_GROUP = ITEM_ENABLED | ITEM_CHECKABLE | ITEM_TRISTATE


class ConfigDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Filter Focus — settings"))
        self.resize(680, 700)
        prj = QgsProject.instance()
        self._vec = {l.id(): l for l in prj.mapLayers().values() if isinstance(l, QgsVectorLayer)}
        self._items = {}            # layer_id -> (item, combo)
        self._path_edited = False

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.ref_combo = QComboBox()
        for lid, lyr in sorted(self._vec.items(), key=lambda kv: kv[1].name().lower()):
            self.ref_combo.addItem(lyr.name(), lid)
        active = iface.activeLayer()
        if active is not None and active.id() in self._vec:
            self.ref_combo.setCurrentIndex(self.ref_combo.findData(active.id()))
        self.field_combo = QComboBox()
        form.addRow(tr("Reference layer:"), self.ref_combo)
        form.addRow(tr("Relationship field:"), self.field_combo)
        root.addLayout(form)

        root.addWidget(QLabel(tr("Target layers (check them and choose each one's field):")))
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels([tr("Layer"), tr("Relationship field")])
        self.tree.setColumnWidth(0, 360)
        self._add_nodes(self.tree.invisibleRootItem(), prj.layerTreeRoot())
        self.tree.expandAll()
        root.addWidget(self.tree, 1)

        self.grp_copy = QGroupBox(tr("Create a copy of the reference (Shapefile) and filter it too"))
        self.grp_copy.setCheckable(True)
        self.grp_copy.setChecked(True)
        row = QHBoxLayout(self.grp_copy)
        self.path_edit = QLineEdit()
        self.path_edit.textEdited.connect(lambda *_: setattr(self, "_path_edited", True))
        btn = QPushButton("…")
        btn.clicked.connect(self._browse)
        row.addWidget(self.path_edit, 1)
        row.addWidget(btn)
        root.addWidget(self.grp_copy)

        grp = QGroupBox(tr("Fields shown in the panel (feature information)"))
        gl = QVBoxLayout(grp)
        self.fields_list = QListWidget()
        self.fields_list.setMaximumHeight(150)
        gl.addWidget(self.fields_list)
        btn_row = QHBoxLayout()
        b_all, b_none = QPushButton(tr("All")), QPushButton(tr("None"))
        b_all.clicked.connect(lambda: self._check_all_fields(True))
        b_none.clicked.connect(lambda: self._check_all_fields(False))
        btn_row.addWidget(b_all)
        btn_row.addWidget(b_none)
        btn_row.addStretch(1)
        gl.addLayout(btn_row)
        root.addWidget(grp)

        bb = QDialogButtonBox(BTN_OK | BTN_CANCEL)
        bb.accepted.connect(self._try_accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

        self.ref_combo.currentIndexChanged.connect(self._ref_changed)
        self.field_combo.currentIndexChanged.connect(self._update_defaults)
        self._ref_changed()

    # ---------- árvore ----------
    def _add_nodes(self, parent_item, node):
        for child in node.children():
            if QgsLayerTree.isGroup(child):
                it = QTreeWidgetItem(parent_item, [child.name(), ""])
                it.setFlags(_FLAGS_GROUP)
                it.setCheckState(0, UNCHECKED)
                self._add_nodes(it, child)
            elif QgsLayerTree.isLayer(child):
                lyr = child.layer()
                if not isinstance(lyr, QgsVectorLayer):
                    continue
                it = QTreeWidgetItem(parent_item, [lyr.name(), ""])
                it.setFlags(_FLAGS_LAYER)
                it.setCheckState(0, UNCHECKED)
                combo = QComboBox()
                combo.addItem("")
                combo.addItems(lyr.fields().names())
                self.tree.setItemWidget(it, 1, combo)
                self._items[lyr.id()] = (it, combo)

    def _ref_id(self):
        return self.ref_combo.currentData()

    def _ref_changed(self):
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        lyr = self._vec.get(self._ref_id())
        if lyr is not None:
            self.field_combo.addItems(lyr.fields().names())
            for guess in ("recibo", "cod_imovel"):
                i = self.field_combo.findText(guess, MATCH_FIXED)
                if i >= 0:
                    self.field_combo.setCurrentIndex(i)
                    break
            if not self._path_edited:
                src = lyr.source().split("|")[0]
                folder = os.path.dirname(src) if os.path.isfile(src) else os.path.expanduser("~")
                self.path_edit.setText(os.path.join(folder, lyr.name() + "_copy.shp"))
        self.field_combo.blockSignals(False)
        self._fill_panel_fields(lyr)
        self._update_defaults()

    def _fill_panel_fields(self, lyr):
        keep = {self.fields_list.item(i).text() for i in range(self.fields_list.count())
                if self.fields_list.item(i).checkState() == CHECKED}
        self.fields_list.clear()
        names = lyr.fields().names() if lyr is not None else []
        rel = self.field_combo.currentText()
        marked = (keep & set(names)) or ({rel} if rel else set())
        for n in names:
            it = QListWidgetItem(n)
            it.setFlags(ITEM_ENABLED | ITEM_CHECKABLE)
            it.setCheckState(CHECKED if n in marked else UNCHECKED)
            self.fields_list.addItem(it)

    def _check_all_fields(self, state):
        for i in range(self.fields_list.count()):
            self.fields_list.item(i).setCheckState(CHECKED if state else UNCHECKED)

    def _update_defaults(self):
        ref_id, field = self._ref_id(), self.field_combo.currentText()
        for lid, (it, combo) in self._items.items():
            lyr = self._vec[lid]
            font = QFont(it.font(0))
            if lid == ref_id:
                it.setCheckState(0, UNCHECKED)
                it.setFlags(ITEM_ENABLED)
                it.setText(0, lyr.name() + tr("  (reference)"))
                font.setBold(True)
                combo.setCurrentIndex(0)
                combo.setEnabled(False)
            else:
                it.setFlags(_FLAGS_LAYER)
                it.setText(0, lyr.name())
                font.setBold(False)
                combo.setEnabled(True)
                if combo.currentText() == "" and field:
                    names = {n.lower(): n for n in lyr.fields().names()}
                    match = names.get(field.lower())
                    if match:
                        combo.setCurrentText(match)
            it.setFont(0, font)

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("Reference copy"), self.path_edit.text(),
                                              "Shapefile (*.shp)")
        if path:
            self.path_edit.setText(path)
            self._path_edited = True

    # ---------- resultado ----------
    def config(self):
        ref_id = self._ref_id()
        targets = {}
        for lid, (it, combo) in self._items.items():
            if lid != ref_id and it.checkState(0) == CHECKED:
                targets[lid] = combo.currentText()
        return {
            "ref_id": ref_id,
            "ref_field": self.field_combo.currentText(),
            "targets": targets,
            "copy_path": self.path_edit.text().strip() if self.grp_copy.isChecked() else None,
            "panel_fields": [self.fields_list.item(i).text()
                             for i in range(self.fields_list.count())
                             if self.fields_list.item(i).checkState() == CHECKED],
        }

    def _try_accept(self):
        cfg = self.config()
        problems = []
        if not cfg["ref_id"] or not cfg["ref_field"]:
            problems.append(tr("Choose the reference layer and the relationship field."))
        if not cfg["targets"] and not cfg["copy_path"]:
            problems.append(tr("Check at least one target layer or enable the reference copy."))
        for lid, field in cfg["targets"].items():
            if not field:
                problems.append(tr("Set the relationship field for '{}'.").format(self._vec[lid].name()))
        if self.grp_copy.isChecked() and not cfg["copy_path"]:
            problems.append(tr("Enter the path of the Shapefile copy."))
        if problems:
            QMessageBox.warning(self, tr("Incomplete settings"), "\n".join(problems))
            return
        self.accept()
