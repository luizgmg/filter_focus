# -*- coding: utf-8 -*-
"""Painel próprio (sempre aberto): navegação + informações dos campos escolhidos."""
from qgis.PyQt.QtCore import QTimer, pyqtSignal
from qgis.PyQt.QtWidgets import (QComboBox, QHBoxLayout,
                                 QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                                 QVBoxLayout, QWidget)
from qgis.core import NULL, QgsFeatureRequest
from qgis.gui import QgsDockWidget
from ..compat import (ASC, FLAG_NO_GEOM, ISO_DATE, MATCH_CONTAINS, NO_EDIT,
                      NO_INSERT, POPUP)
from ..i18n import tr

MAX_ROWS = 200   # limite de linhas no modo de várias feições


def _fmt(val):
    if val is None or val == NULL:
        return ""
    if hasattr(val, "toString"):          # QDate / QDateTime / QTime
        return val.toString(ISO_DATE)
    return str(val)


class NavPanel(QgsDockWidget):
    stopRequested = pyqtSignal()

    def __init__(self, layer, field, show_fields, parent=None):
        super().__init__("Filter Focus", parent)
        self.setObjectName("FilterFocusPanel")
        self.layer, self.field = layer, field
        names = layer.fields().names()
        self.show_fields = [f for f in show_fields if f in names]
        self._fid_to_index = {}

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.addWidget(QLabel(tr("{} · relationship: {}").format(layer.name(), field)))

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setInsertPolicy(NO_INSERT)
        self.combo.completer().setFilterMode(MATCH_CONTAINS)
        self.combo.completer().setCompletionMode(POPUP)
        self.combo.activated.connect(self._select)
        lay.addWidget(self.combo)

        row = QHBoxLayout()
        self.btn_prev = QPushButton(tr("◀ Previous"))
        self.btn_next = QPushButton(tr("Next ▶"))
        self.btn_prev.clicked.connect(lambda: self._step(-1))
        self.btn_next.clicked.connect(lambda: self._step(1))
        row.addWidget(self.btn_prev)
        row.addWidget(self.btn_next)
        lay.addLayout(row)

        self.lbl = QLabel("")
        lay.addWidget(self.lbl)

        self.info = QTableWidget()
        self.info.setEditTriggers(NO_EDIT)
        self.info.setAlternatingRowColors(True)
        lay.addWidget(self.info, 1)

        btn_stop = QPushButton(tr("Stop and restore filters"))
        btn_stop.clicked.connect(self.stopRequested)
        lay.addWidget(btn_stop)
        self.setWidget(body)

        self._sort_key = None
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(150)
        self._reload_timer.timeout.connect(self._on_table_config_changed)
        try:   # a ordenação da tabela de atributos é gravada na configuração da camada
            self.layer.attributeTableConfigChanged.connect(self._reload_timer.start)
        except (AttributeError, TypeError):
            pass

        self.reload()
        self.sync_from_selection()

    def dispose(self):
        self._reload_timer.stop()
        try:
            self.layer.attributeTableConfigChanged.disconnect(self._reload_timer.start)
        except (AttributeError, TypeError, RuntimeError):
            pass

    def _on_table_config_changed(self):
        cfg = self.layer.attributeTableConfig()
        if (cfg.sortExpression(), cfg.sortOrder()) == self._sort_key:
            return                      # mudou outra coisa (largura de coluna etc.)
        self.reload()
        self.sync_from_selection()

    # ---------- lista de valores ----------
    def reload(self):
        """Carrega os valores na MESMA ordem da tabela de atributos da camada."""
        cfg = self.layer.attributeTableConfig()
        expr, order = cfg.sortExpression(), cfg.sortOrder()
        self._sort_key = (expr, order)
        items = self._load_items(expr, order == ASC) if expr else self._load_items(None, True)
        self.combo.blockSignals(True)
        self.combo.clear()
        self._fid_to_index = {}
        for i, (text, fid) in enumerate(items):
            self.combo.addItem(text, fid)
            self._fid_to_index[fid] = i
        self.combo.setCurrentIndex(-1)
        self.combo.blockSignals(False)

    def _load_items(self, sort_expr, ascending):
        req = QgsFeatureRequest().setFlags(FLAG_NO_GEOM)
        if sort_expr:
            req.setOrderBy(QgsFeatureRequest.OrderBy(
                [QgsFeatureRequest.OrderByClause(sort_expr, ascending)]))
        else:   # sem ordenação na tabela: ordem natural da fonte, como a tabela mostra
            req.setSubsetOfAttributes([self.field], self.layer.fields())
        items = []
        for feat in self.layer.getFeatures(req):
            val = feat[self.field]
            items.append((tr("(empty)") if val is None or val == NULL else str(val), feat.id()))
        if not items and sort_expr:     # expressão inválida: cai para a ordem natural
            return self._load_items(None, True)
        return items

    def _select(self, index):
        if index < 0:
            return
        self.layer.selectByIds([self.combo.itemData(index)])   # dispara selectionChanged

    def _step(self, delta):
        n = self.combo.count()
        if n == 0:
            return
        cur = self.combo.currentIndex()
        idx = (0 if delta > 0 else n - 1) if cur < 0 else max(0, min(n - 1, cur + delta))
        self.combo.setCurrentIndex(idx)
        self._select(idx)

    # ---------- sincronização com a seleção ----------
    def sync_from_selection(self):
        """Atualiza combo, rótulo e informações quando a seleção muda (por qualquer meio)."""
        ids = list(self.layer.selectedFeatureIds())
        self.combo.blockSignals(True)
        if len(ids) == 1 and ids[0] in self._fid_to_index:
            self.combo.setCurrentIndex(self._fid_to_index[ids[0]])
        else:
            self.combo.setCurrentIndex(-1)
        self.combo.blockSignals(False)
        total, pos = self.combo.count(), self.combo.currentIndex() + 1
        self.lbl.setText(tr("{} selected").format(len(ids)) +
                         (" · {}/{}".format(pos, total) if pos else tr(" · {} total").format(total)))
        self._update_info(ids)

    def _update_info(self, ids):
        self.info.clear()
        fields = self.show_fields
        if not fields or not ids:
            self.info.setRowCount(0)
            self.info.setColumnCount(0)
            return
        req = QgsFeatureRequest().setFilterFids(ids[:MAX_ROWS]).setFlags(FLAG_NO_GEOM)
        feats = list(self.layer.getFeatures(req))
        labels = [self.layer.attributeDisplayName(self.layer.fields().indexFromName(f))
                  for f in fields]
        if len(feats) == 1:                       # uma feição: campo | valor
            self.info.setColumnCount(2)
            self.info.setHorizontalHeaderLabels([tr("Field"), tr("Value")])
            self.info.setRowCount(len(fields))
            for r, f in enumerate(fields):
                self.info.setItem(r, 0, QTableWidgetItem(labels[r]))
                self.info.setItem(r, 1, QTableWidgetItem(_fmt(feats[0][f])))
            self.info.verticalHeader().setVisible(False)
        else:                                     # várias: uma linha por feição
            self.info.setColumnCount(len(fields))
            self.info.setHorizontalHeaderLabels(labels)
            self.info.setRowCount(len(feats))
            for r, feat in enumerate(feats):
                for c, f in enumerate(fields):
                    self.info.setItem(r, c, QTableWidgetItem(_fmt(feat[f])))
            self.info.verticalHeader().setVisible(True)
            if len(ids) > MAX_ROWS:
                self.lbl.setText(self.lbl.text() + tr(" (showing {})").format(MAX_ROWS))
        self.info.resizeColumnsToContents()
        self.info.horizontalHeader().setStretchLastSection(True)
