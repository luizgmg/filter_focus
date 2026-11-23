# -*- coding: utf-8 -*-
"""Tradução simples EN/PT-BR segundo o idioma configurado no QGIS (sem arquivos .qm)."""
from qgis.PyQt.QtCore import QSettings
from qgis.core import QgsApplication


def _language():
    try:
        loc = QgsApplication.locale()          # idioma efetivo do QGIS (ex.: "pt_BR")
    except Exception:                          # noqa: BLE001
        s = QSettings()
        loc = s.value("locale/userLocale", "en") if s.value("locale/overrideFlag", False, type=bool) else "en"
    return "pt" if str(loc).lower().startswith("pt") else "en"


LANG = _language()

_PT = {
    "Filters restored.": "Filtros restaurados.",
    "Fields longer than 10 characters were truncated in the Shapefile: {}":
        "Campos com mais de 10 caracteres foram truncados no Shapefile: {}",
    "The copy does not have the field '{}'.": "A cópia não tem o campo '{}'.",
    "Could not filter (layer in edit mode or unsupported source): ":
        "Não foi possível filtrar (camada em edição ou fonte sem suporte): ",
    "The file already exists and will not be overwritten: {}":
        "O arquivo já existe e não será sobrescrito: {}",
    "Could not create folder '{}': {}": "Não foi possível criar a pasta '{}': {}",
    "Export failed: {}": "Falha na exportação: {}",
    "The copy was written but could not be loaded: {}":
        "A cópia foi gravada, mas não pôde ser carregada: {}",
    "Copy created: {}": "Cópia criada: {}",
    "Layer not found in the project: {}": "Camada não encontrada no projeto: {}",
    "'{}': field '{}' does not exist.": "'{}': o campo '{}' não existe.",
    "'{}': old filter on '{}' discarded: {}": "'{}': filtro antigo em '{}' descartado: {}",
    "Filter Focus — settings": "Filter Focus — configuração",
    "Reference layer:": "Camada de referência:",
    "Relationship field:": "Campo de relacionamento:",
    "Target layers (check them and choose each one's field):":
        "Camadas de destino (marque e escolha o campo de cada uma):",
    "Layer": "Camada",
    "Relationship field": "Campo de relacionamento",
    "Create a copy of the reference (Shapefile) and filter it too":
        "Criar cópia da referência (Shapefile) e filtrá-la também",
    "Fields shown in the panel (feature information)":
        "Campos exibidos no painel (informações da feição)",
    "All": "Todos",
    "None": "Nenhum",
    "  (reference)": "  (referência)",
    "Reference copy": "Cópia da referência",
    "Choose the reference layer and the relationship field.":
        "Escolha a camada de referência e o campo de relacionamento.",
    "Check at least one target layer or enable the reference copy.":
        "Marque ao menos uma camada de destino ou ative a cópia da referência.",
    "Set the relationship field for '{}'.": "Defina o campo de relacionamento de '{}'.",
    "Enter the path of the Shapefile copy.": "Informe o caminho do Shapefile da cópia.",
    "Incomplete settings": "Configuração incompleta",
    "{} · relationship: {}": "{} · relacionamento: {}",
    "◀ Previous": "◀ Anterior",
    "Next ▶": "Próximo ▶",
    "Stop and restore filters": "Encerrar e restaurar filtros",
    "(empty)": "(vazio)",
    "{} selected": "{} selecionada(s)",
    " · {} total": " · {} no total",
    " (showing {})": " (exibindo {})",
    "Field": "Campo",
    "Value": "Valor",
}


def tr(text):
    return _PT.get(text, text) if LANG == "pt" else text
