# -*- coding: utf-8 -*-
"""Observa selectionChanged da camada de referência, com debounce."""
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal


class SelectionWatcher(QObject):
    selectionSettled = pyqtSignal()

    def __init__(self, layer, delay_ms=50, parent=None):
        super().__init__(parent)
        self.layer = layer
        self._connected = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self.selectionSettled)

    def start(self):
        if self._connected:          # evita conexão duplicada
            return
        self.layer.selectionChanged.connect(self._on_changed)
        self._connected = True

    def stop(self):
        self._timer.stop()
        if not self._connected:
            return
        try:
            self.layer.selectionChanged.disconnect(self._on_changed)
        except (TypeError, RuntimeError):   # camada já destruída
            pass
        self._connected = False

    def _on_changed(self, *_):
        self._timer.start()
