# -*- coding: utf-8 -*-
"""Aplicação e restauração de filtros (subset string) em múltiplas camadas."""
import re

from qgis.core import NULL, QgsProject, QgsVectorLayer
from ..i18n import tr


def quote_ident(name):
    """Nome de campo entre aspas duplas, escapando aspas internas."""
    return '"' + str(name).replace('"', '""') + '"'


def _is_null(value):
    return value is None or value == NULL


def _literal(value, numeric):
    if numeric:
        try:
            num = float(value)
            return str(int(num)) if num.is_integer() else repr(num)
        except (TypeError, ValueError):
            pass  # cai para texto; o provider decide
    return "'" + str(value).replace("'", "''") + "'"


def build_expression(field_name, values, numeric=False):
    """Expressão para um ou mais valores. Retorna None se não houver valores."""
    nulls = any(_is_null(v) for v in values)
    vals = list(dict.fromkeys(v for v in values if not _is_null(v)))  # únicos, ordem preservada
    ident = quote_ident(field_name)
    parts = []
    if len(vals) == 1:
        parts.append("{} = {}".format(ident, _literal(vals[0], numeric)))
    elif vals:
        parts.append("{} IN ({})".format(ident, ", ".join(_literal(v, numeric) for v in vals)))
    if nulls:
        parts.append("{} IS NULL".format(ident))
    if not parts:
        return None
    return "(" + " OR ".join(parts) + ")"


def is_stale_field_filter(subset, field):
    """True se o subset só contém condições sobre o campo de relacionamento
    (resto de um filtro dinâmico anterior). Combinar com o novo daria sempre vazio."""
    if not subset:
        return False
    clause = (r'\(?\s*"' + re.escape(field).replace('\\ ', ' ') + r'"\s*(?:'
              r"=\s*'(?:[^']|'')*'|=\s*[-\d.]+|"
              r"IN\s*\((?:[^()']|'(?:[^']|'')*')*\)|IS\s+NULL)\s*\)?")
    rest = re.sub(clause, '', subset, flags=re.I)
    return re.fullmatch(r'[\s()]*(?:(?:AND|OR)[\s()]*)*', rest, flags=re.I) is not None


class FilterManager:
    """
    targets: {layer_id: nome_do_campo_de_relacionamento}
    Guarda o subsetString original de cada camada e o recompõe como
    (original) AND (filtro dinâmico). restore() devolve o estado original.
    """

    def __init__(self, targets):
        self.targets = dict(targets)
        self._originals = {}   # layer_id -> subsetString original
        self._applied = {}     # layer_id -> último subset aplicado (evita refiltrar)
        self.failed = set()    # camadas onde setSubsetString falhou
        self.notes = []        # avisos (ex.: filtro antigo descartado)

    def _layer(self, layer_id):
        lyr = QgsProject.instance().mapLayer(layer_id)
        return lyr if isinstance(lyr, QgsVectorLayer) else None

    def snapshot(self):
        for lid in self.targets:
            lyr = self._layer(lid)
            if lyr is not None and lid not in self._originals:
                orig = lyr.subsetString()
                if is_stale_field_filter(orig, self.targets[lid]):
                    self.notes.append(tr("'{}': old filter on '{}' discarded: {}").format(
                        lyr.name(), self.targets[lid], orig))
                    orig = ""
                self._originals[lid] = orig

    def validate(self):
        """Lista de mensagens de erro de configuração (campo ausente etc.)."""
        errors = []
        for lid, field in self.targets.items():
            lyr = self._layer(lid)
            if lyr is None:
                errors.append(tr("Layer not found in the project: {}").format(lid))
            elif lyr.fields().indexFromName(field) < 0:
                errors.append(tr("'{}': field '{}' does not exist.").format(lyr.name(), field))
        return errors

    def apply(self, values):
        """Aplica o filtro a todas as camadas. values vazio -> restaura."""
        if not values:
            self.restore()
            return
        self.failed.clear()
        for lid, field in self.targets.items():
            lyr = self._layer(lid)
            if lyr is None:
                continue
            idx = lyr.fields().indexFromName(field)
            if idx < 0:
                self.failed.add(lid)
                continue
            expr = build_expression(field, values, lyr.fields().at(idx).isNumeric())
            orig = self._originals.get(lid, "")
            subset = "({}) AND {}".format(orig, expr) if orig else expr
            if self._applied.get(lid) == subset:
                continue  # nada mudou
            if lyr.setSubsetString(subset):
                self._applied[lid] = subset
            else:
                self.failed.add(lid)  # camada em edição ou provider sem suporte

    def restore(self):
        for lid, orig in self._originals.items():
            lyr = self._layer(lid)
            if lyr is not None and lyr.subsetString() != orig:
                lyr.setSubsetString(orig)
        self._applied.clear()
