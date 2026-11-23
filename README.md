# Filter Focus (QGIS plugin)

Filter multiple layers by the selected feature of a reference layer and zoom to it.

## What it does
1. Pick a **reference layer** and a **relationship field**.
2. Pick the **target layers** (tree like the Layers panel; each layer has its own matching field).
3. Select one or more features in the reference layer. The plugin, in a single step:
   - applies a subset filter to every target layer (`"field" = 'value'`, or `IN (...)` for multiple selection);
   - centers the map on the selection with an automatic zoom.
4. Use the **Filter Focus panel** to step through features (Previous/Next, searchable list, in the same order as the attribute table sort) and to view the attributes you chose.
5. Stop the plugin (toolbar button or panel button) to restore the original filters.

## Notes
- Existing layer filters are preserved (`(original) AND (dynamic)`) and restored on exit. A leftover filter that only constrains the relationship field is discarded, since combining it would always return nothing.
- The reference layer itself is never filtered. Optionally, a local **Shapefile copy** of it is created, added to the project and filtered like the other targets (field names are truncated to 10 characters by the format).
- The interface follows the QGIS language setting (English and Brazilian Portuguese).
- Layers in edit mode or from providers without subset support cannot be filtered; the plugin warns which ones.

## Compatibility
QGIS 3.0 through 4.x (Qt5 and Qt6).

## Install
Plugins > Manage and Install Plugins > search for "Filter Focus", or copy the `filter_focus` folder into your QGIS profile `python/plugins` directory.

## Português
Filtra várias camadas pela(s) feição(ões) selecionada(s) em uma camada de referência e dá zoom nela. Escolha a referência, o campo de relacionamento e as camadas de destino; ao selecionar feições na referência, os filtros são aplicados e o mapa é centralizado. O painel do plugin permite navegar (Anterior/Próximo) e exibir os campos escolhidos. Ao encerrar, os filtros originais são restaurados. A interface segue o idioma configurado no QGIS (inglês ou português).

## License
GPL-2.0. See `LICENSE`.
