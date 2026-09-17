import logging
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill

log =logging.getLogger(__name__)


# EXPORTAR A EXCEL


def export_to_excel(df_conc_erp, df_conc_banco, df_partidas_pendientes,
                   df_depositos_sobrantes, df_fuzzy_matches, output_path):
    """
    Exporta todos los DataFrames a un archivo Excel con 6 pestañas y formato.
    Las filas con fuzzy_match se resaltan en amarillo.
    La pestaña Resumen incluye conteos e importes por categoría.

    Parámetros:
        df_conc_mayor          : mayor conciliado
        df_conc_banco          : banco conciliado
        df_partidas_pendientes : partidas sin match
        df_depositos_sobrantes : depósitos sin match
        df_fuzzy_matches       : detalle de matches fuzzy
        output_path            : ruta de salida del archivo Excel
    """
    log.info("Generando Resumen...")
    # Construir resumen
    total_mayor     = len(df_conc_erp)
    total_banco     = len(df_conc_banco)
    total_imp_mayor = df_conc_erp['Importe en moneda local'].sum()
    total_imp_banco = df_conc_banco['Importe'].sum()

    exactos_mayor_df = df_conc_erp[(df_conc_erp['Referencia_y'].notna()) & (df_conc_erp['fuzzy_match'] != True)]
    exactos_banco_df = df_conc_banco[(df_conc_banco['Clave_2'].notna())       & (df_conc_banco['fuzzy_match']  != True)]
    fuzzy_mayor_df   = df_conc_erp[df_conc_erp['fuzzy_match'] == True]
    fuzzy_banco_df   = df_conc_banco[df_conc_banco['fuzzy_match']  == True]

    exactos_mayor_cnt = len(exactos_mayor_df);  exactos_mayor_imp = exactos_mayor_df['Importe en moneda local'].sum()
    exactos_banco_cnt = len(exactos_banco_df);  exactos_banco_imp = exactos_banco_df['Importe'].sum()
    fuzzy_mayor_cnt   = len(fuzzy_mayor_df);    fuzzy_mayor_imp   = fuzzy_mayor_df['Importe en moneda local'].sum()
    fuzzy_banco_cnt   = len(fuzzy_banco_df);    fuzzy_banco_imp   = fuzzy_banco_df['Importe'].sum()
    pend_cnt          = len(df_partidas_pendientes); pend_imp      = df_partidas_pendientes['Importe en moneda local'].sum()
    sobr_cnt          = len(df_depositos_sobrantes); sobr_imp      = df_depositos_sobrantes['Importe'].sum()

    total_conc_mayor = exactos_mayor_cnt + fuzzy_mayor_cnt
    total_conc_banco = exactos_banco_cnt + fuzzy_banco_cnt
    total_imp_conc_mayor = exactos_mayor_imp + fuzzy_mayor_imp
    total_imp_conc_banco = exactos_banco_imp + fuzzy_banco_imp

    df_resumen = pd.DataFrame([
        {'Categoría': 'Total registros Mayor',           'Registros Mayor': total_mayor,        'Importe Mayor': total_imp_mayor,        'Registros Banco': '',                 'Importe Banco': ''},
        {'Categoría': 'Total registros Banco',           'Registros Mayor': '',                 'Importe Mayor': '',                     'Registros Banco': total_banco,        'Importe Banco': total_imp_banco},
        {'Categoría': '─────────────────',               'Registros Mayor': '',                 'Importe Mayor': '',                     'Registros Banco': '',                 'Importe Banco': ''},
        {'Categoría': 'Coincidencias exactas',           'Registros Mayor': exactos_mayor_cnt,  'Importe Mayor': exactos_mayor_imp,      'Registros Banco': exactos_banco_cnt,  'Importe Banco': exactos_banco_imp},
        {'Categoría': 'Coincidencias fuzzy',             'Registros Mayor': fuzzy_mayor_cnt,    'Importe Mayor': fuzzy_mayor_imp,        'Registros Banco': fuzzy_banco_cnt,    'Importe Banco': fuzzy_banco_imp},
        {'Categoría': 'Total conciliado',                'Registros Mayor': total_conc_mayor,   'Importe Mayor': total_imp_conc_mayor,   'Registros Banco': total_conc_banco,   'Importe Banco': total_imp_conc_banco},
        {'Categoría': '% Conciliado',                    'Registros Mayor': f'{total_conc_mayor/total_mayor:.1%}' if total_mayor else '0%', 'Importe Mayor': f'{total_imp_conc_mayor/total_imp_mayor:.1%}' if total_imp_mayor else '0%', 'Registros Banco': f'{total_conc_banco/total_banco:.1%}' if total_banco else '0%', 'Importe Banco': f'{total_imp_conc_banco/total_imp_banco:.1%}' if total_imp_banco else '0%'},
        {'Categoría': '─────────────────',               'Registros Mayor': '',                 'Importe Mayor': '',                     'Registros Banco': '',                 'Importe Banco': ''},
        {'Categoría': 'Partidas pendientes (sin match)', 'Registros Mayor': pend_cnt,           'Importe Mayor': pend_imp,               'Registros Banco': '',                 'Importe Banco': ''},
        {'Categoría': 'Depósitos sobrantes (sin match)', 'Registros Mayor': '',                 'Importe Mayor': '',                     'Registros Banco': sobr_cnt,           'Importe Banco': sobr_imp},
        {'Categoría': 'Diferencia (Pend - Sobr)',        'Registros Mayor': pend_cnt-sobr_cnt,  'Importe Mayor': round(pend_imp-sobr_imp, 2), 'Registros Banco': '',             'Importe Banco': ''},
    ])

    log.info("Escribiendo el Excel...")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_resumen.to_excel(writer,             sheet_name='Resumen',             index=False)
        df_conc_erp.to_excel(writer,          sheet_name='Mayor vs Banco',      index=False)
        df_conc_banco.to_excel(writer,          sheet_name='Banco vs Mayor',      index=False)
        df_partidas_pendientes.to_excel(writer, sheet_name='Partidas Pendientes', index=False)
        df_depositos_sobrantes.to_excel(writer, sheet_name='Depositos Sobrantes', index=False)
        df_fuzzy_matches.to_excel(writer,       sheet_name='Fuzzy Matches',       index=False)

        yellow = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
        green  = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
        orange = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')

        # Formato resumen
        ws_resumen = writer.sheets['Resumen']
        for cell in ws_resumen[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')

        color_map = {2: green, 3: green, 5: green, 6: yellow, 7: green,
                     8: green, 10: orange, 11: orange, 12: orange}
        for row_idx, row in enumerate(ws_resumen.iter_rows(min_row=2), start=2):
            for cell in row:
                cell.fill = color_map.get(row_idx, PatternFill())
                cell.alignment = Alignment(horizontal='center')

        for col, width in [('A', 38), ('B', 18), ('C', 18), ('D', 18), ('E', 18)]:
            ws_resumen.column_dimensions[col].width = width

        # Filas fuzzy en amarillo
        for sheet_name, df in [('Mayor vs Banco', df_conc_erp), ('Banco vs Mayor', df_conc_banco)]:
            ws = writer.sheets[sheet_name]
            if 'fuzzy_match' in df.columns:
                for row_idx, valor in enumerate(df['fuzzy_match'], start=2):
                    if valor == True:
                        for cell in ws[row_idx]:
                            cell.fill = yellow

    log.info("Archivo guardado en: %s",output_path.relative_to(Path.cwd()))
