import logging
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from src.project_config import (
    COLS_FUZZY_BANK,
    COLS_FUZZY_ERP,
    COLS_FUZZY_REQUERIDAS,
    COLS_REQUERIDAS_BANCO,
    COLS_REQUERIDAS_ERP,
)

log =logging.getLogger(__name__)

def load_erp_report (filepath :Path)-> pd.DataFrame :

    try :
        log.info("Cargando reporte del erp:%s",filepath.relative_to(Path.cwd()))
        df_erp= pd.read_excel(filepath)
        log.info("Numero total de registros cargados:%d",len(df_erp))
        return df_erp

    except FileNotFoundError as e :
        log.error("No se encontro archivo especificado:%s",e.filename)
        raise
    except PermissionError as e :
        log.error("El archivo erp esta abierto bloqueado:%s", e)
        raise
    except ValueError as e :
        log.error("Error en el formato o estructura del excel :%s",e)
        raise



def load_bank_report(filepath: Path)-> pd.DataFrame:

    try :
        log.info("Cargando Reporte bancario:%s",filepath.relative_to(Path.cwd()))
        with pd.ExcelFile(filepath) as xls :
            df_bank= pd.concat(
                [pd.read_excel(xls,sheet) for sheet in xls.sheet_names],
                ignore_index = True)
        log.info("NUmero total de registros del banco :%d",len (df_bank))
        return df_bank

    except FileNotFoundError as e :
        log.error("No se encontro archivo especificado en :%s", e.filename)
        raise
    except PermissionError as e :
        log.error ("El archivo bancario esta abierto o bloqueado :$%s",e)
        raise
    except ValueError as e :
        log.error("Error en el formato o escritura del archvivo :%s",e)
        raise




def exact_match_reconciliation (df_erp: pd.DataFrame , df_bank : pd.DataFrame)-> tuple :

    #Validacion de columnas requeridas para el cruce
    if cols_faltantes_erp := (set(COLS_REQUERIDAS_ERP)- set(df_erp.columns)):
        log.error("Columnas faltantes en reporte erp :%s", cols_faltantes_erp)
        raise KeyError(f"Faltan clumnas requerids en el ERP :{cols_faltantes_erp}")

    if cols_faltantes_bank := (set(COLS_REQUERIDAS_BANCO)- set(df_bank.columns)):
        log.error("Columna faltantes en reporte bancario :%s",cols_faltantes_bank)
        raise KeyError(f"f Faltan columnas requeridas en el reporte bancario: {cols_faltantes_bank}")

    df_erp['Importe en moneda local'] = df_erp['Importe en moneda local'].abs()

    log.info("Conciliando ERP...")
    df_conc_erp = pd.merge(
        df_erp,
        df_bank[COLS_REQUERIDAS_BANCO],
        left_on=['Ref_transaccion', 'Importe en moneda local'],
        right_on=['Referencia', 'Importe'],
        how='left'
    ).rename(columns={
        'Cuenta bancaria': 'Cuenta acreditada',
        'Fecha valor'    : 'Fecha de acreditacion',
        'Importe'        : 'Importe acreditado'
    })

    log.info("Conciliando Banco...")
    df_conc_banco = pd.merge(
        df_bank,
        df_erp[COLS_REQUERIDAS_ERP],
        left_on=['Referencia', 'Importe'],
        right_on=['Ref_transaccion', 'Importe en moneda local'],
        how='left'
    )

    return df_conc_erp,df_conc_banco


def get_pending_records(df_conc_erp: pd.DataFrame, df_conc_banco: pd.DataFrame)-> tuple:
    """
    Filtra los registros sin match en ambos DataFrames.
    Se puede llamar después del cruce exacto y después del fuzzy

    Parámetros:
        df_conc_erp : DataFrame del mayor conciliado
        df_conc_banco : DataFrame del banco conciliado

    Retorna:
        df_partidas_pendientes : registros del mayor sin match
        df_depositos_sobrantes : registros del banco sin match
    """
    df_partidas_pendientes = df_conc_erp[df_conc_erp['Cuenta acreditada'].isna()].copy()
    df_depositos_sobrantes = df_conc_banco[df_conc_banco['Clave_2'].isna()].copy()

    log.info("[Pendientes] Partidas sin match: %d", len(df_partidas_pendientes))
    log.info("Depositos sobrantes :%d",len(df_depositos_sobrantes))

    return df_partidas_pendientes, df_depositos_sobrantes


def fuzzy_match_reconciliation(df_partidas_pendientes: pd.DataFrame,
    df_depositos_sobrantes: pd.DataFrame,
    umbral: int = 80,) -> pd.DataFrame:
    """Capa 2: Fuzzy matching sobre registros sin match previo.

    Filtra por importe exacto y aplica similitud de texto sobre la referencia.
    """
    # 1. Guard Clauses (Validación de precondiciones)
    if faltantes_bank := (set(COLS_FUZZY_BANK) - set(df_depositos_sobrantes.columns)):
        log.error("Columnas faltantes en depósitos sobrantes: %s", faltantes_bank)
        raise KeyError(f"Faltan columnas en df_depositos_sobrantes: {faltantes_bank}")

    if faltantes_erp := (set(COLS_FUZZY_ERP) - set(df_partidas_pendientes.columns)):
        log.error("Columnas faltantes en partidas pendientes: %s", faltantes_erp)
        raise KeyError(f"Faltan columnas en df_partidas_pendientes: {faltantes_erp}")

    # Retorno rápido si no hay pendientes que cruzar
    if df_partidas_pendientes.empty or df_depositos_sobrantes.empty:
        log.info("[Capa 2] Sin datos para evaluar fuzzy matching.")
        return pd.DataFrame()

    # 2. Preparación de columnas temporales de texto
    df_dep = df_depositos_sobrantes.assign(
        _ref_str=df_depositos_sobrantes["Referencia"].astype(str)
    )
    df_pen = df_partidas_pendientes.assign(
        _ref_str=df_partidas_pendientes["Ref_transaccion"].astype(str)
    )

    # 3. Función de búsqueda interna
    def _buscar_match(row: pd.Series) -> dict | None:
        candidatos = df_pen[df_pen["Importe en moneda local"] == row["Importe"]]
        if candidatos.empty:
            return None

        ref_deposito: str = str(row["_ref_str"])
        refs_pendientes: list[str] = candidatos["_ref_str"].astype(str).tolist()

        match = process.extractOne(
            ref_deposito,
            refs_pendientes,
            scorer=fuzz.partial_ratio
        )
        if not match or match[1] < umbral:
            return None

        mask: pd.Series = candidatos["_ref_str"] == match[0]
        pendiente: pd.Series = candidatos.loc[mask].iloc[0]

        # Retornar diccionario ignorando columnas auxiliares internas (que inician con '_')
        return {
            **{f"deposito_{c}": row[c] for c in df_depositos_sobrantes.columns},
            **{
                f"pendiente_{c}": pendiente[c]
                for c in df_partidas_pendientes.columns
                if c not in ["Referencia_x", "Importe en moneda local"]
            },
            "fuzzy_score_referencia": match[1],
        }

    # 4. Procesamiento
    resultados = df_dep.apply(_buscar_match, axis=1).dropna().tolist()
    df_fuzzy_matches = pd.DataFrame(resultados) if resultados else pd.DataFrame()

    # Mantenemos log.info en lugar de print
    log.info("Fuzzy matches encontrados: %d", len(df_fuzzy_matches))

    return df_fuzzy_matches



def update_reconciliation(
    df_conc_erp: pd.DataFrame,
    df_conc_banco: pd.DataFrame,
    df_fuzzy_matches: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Actualiza df_conc_mayor y df_conc_banco con los resultados del fuzzy matching.
    Marca las filas actualizadas con la columna 'fuzzy_match' = True.
    """

    if faltantes := set(COLS_REQUERIDAS_ERP) - set(df_conc_erp.columns):
        log.info("Columnas faltantes en reporte conciliado erp:%s",faltantes)
        raise KeyError(f"Faltan columnas en reporte erp conciliado, {faltantes}")

    if faltantes := set(COLS_REQUERIDAS_BANCO)- set(df_conc_banco.columns):
        log.info("Columnas faltantes en reprote concilado de bancos :%s",faltantes)
        raise KeyError (f"Faltan columnas en reporte banco concilia: {faltantes}")

    if not df_fuzzy_matches.empty and(
        faltantes := set(COLS_FUZZY_REQUERIDAS) - set(df_fuzzy_matches.columns)):
            log.error("Columnas faltantes en df_fuzzy_matches: %s", faltantes)
            raise KeyError(f"Faltan columnas en df_fuzzy_matches: {faltantes}")

    df_erp= df_conc_erp.copy()
    df_banco = df_conc_banco.copy()

    df_erp["fuzzy_match"]= False
    df_banco["fuzzy_match"]= False

    # 1. Retorno rápido si no hay nada que actualizar
    if df_fuzzy_matches.empty:
        log.info("No hay fuzzy matches para actualizar.")
        return df_erp, df_banco

    for _, match in df_fuzzy_matches.iterrows():
            # Actualizar mayor
            mask_mayor = df_erp['Ref_transaccion'] == match['pendiente_Ref_transaccion']
            n_mayor = mask_mayor.sum()

            if n_mayor == 0:
                log.warning(
                    "Fuzzy match sin fila correspondiente en mayor: Ref_transaccion=%s",
                    match['pendiente_Ref_transaccion']
                )
            elif n_mayor > 1:
                log.warning(
                    "Ref_transaccion duplicada en mayor (%d filas): %s — se actualizarán todas",
                    n_mayor, match['pendiente_Ref_transaccion']
                )

            df_erp.loc[mask_mayor, 'Cuenta acreditada']     = match['deposito_Cuenta bancaria']
            df_erp.loc[mask_mayor, 'Fecha de acreditacion'] = match['deposito_Fecha valor']
            df_erp.loc[mask_mayor, 'Importe acreditado']    = match['deposito_Importe']
            df_erp.loc[mask_mayor, 'Referencia_y']          = match['deposito_Referencia']
            df_erp.loc[mask_mayor, 'Banco']                 = match['deposito_Banco']
            df_erp.loc[mask_mayor, 'fuzzy_match']           = True

            # Actualizar banco
            mask_banco = df_banco['Referencia'] == match['deposito_Referencia']
            n_banco = mask_banco.sum()

            if n_banco == 0:
                log.warning(
                    "Fuzzy match sin fila correspondiente en banco: Referencia=%s",
                    match['deposito_Referencia']
                )
            elif n_banco > 1:
                log.warning(
                    "Referencia duplicada en banco (%d filas): %s — se actualizarán todas",
                    n_banco, match['deposito_Referencia']
                )

            df_banco.loc[mask_banco, 'Ref_transaccion']         = match['pendiente_Ref_transaccion']
            df_banco.loc[mask_banco, 'Clave_2']                 = match['pendiente_Clave_2']
            df_banco.loc[mask_banco, 'Importe en moneda local'] = match['deposito_Importe']
            df_banco.loc[mask_banco, 'fuzzy_match']             = True

    log.info("[Actualizar] %d registros actualizados en mayor y banco.", len(df_fuzzy_matches))

        # 4. Verificación de dtype en columnas de importe (detección, no corrección automática)
    if df_erp['Importe acreditado'].dtype == 'object':
        log.warning("Columna 'Importe acreditado' quedó con dtype object tras el fuzzy matching")

    if df_banco['Importe en moneda local'].dtype == 'object':
        log.warning("Columna 'Importe en moneda local' quedó con dtype object tras el fuzzy matching")

    return df_erp, df_banco
