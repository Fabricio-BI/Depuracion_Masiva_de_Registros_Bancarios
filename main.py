import logging

from src.bank_reconciliation import (
    exact_match_reconciliation,
    fuzzy_match_reconciliation,
    get_pending_records,
    load_bank_report,
    load_erp_report,
    update_reconciliation,
)
from src.excel_exporter import export_to_excel
from src.logging_config import setup_logger
from src.project_config import ACCOUNT_FILE, BANK_FILE, PROCESSED_DIR, PROCESSED_FILE

log =logging.getLogger(__name__)



def run_conciliacion() -> tuple:
    """Ejecuta el pipeline completo de conciliación bancaria.

    Retorna:
        erp_conc, banco_conc, df_partidas_pendientes, df_depositos_sobrantes,
        df_fuzzy_matches : resultados finales del proceso
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok= True)
    log.info("Iniciando proceso de conciliacion")

    try:
        df_erp = load_erp_report(ACCOUNT_FILE)
        df_bank = load_bank_report(BANK_FILE)

        df_conc_erp, df_conc_banco = exact_match_reconciliation(df_erp, df_bank)
        df_partidas_pendientes, df_depositos_sobrantes = get_pending_records(
            df_conc_erp, df_conc_banco
        )

        df_fuzzy_matches = fuzzy_match_reconciliation(
            df_partidas_pendientes, df_depositos_sobrantes, umbral=80
        )
        df_conc_erp, df_conc_banco = update_reconciliation(
            df_conc_erp, df_conc_banco, df_fuzzy_matches
        )
        df_partidas_pendientes, df_depositos_sobrantes = get_pending_records(
            df_conc_erp, df_conc_banco
        )

        export_to_excel(
            df_conc_erp, df_conc_banco, df_partidas_pendientes,
            df_depositos_sobrantes, df_fuzzy_matches, PROCESSED_FILE
        )

        log.info("Proceso de conciliacion terminado")

        return (
            df_conc_erp, df_conc_banco,
            df_partidas_pendientes, df_depositos_sobrantes,
            df_fuzzy_matches,
        )

    except Exception:
        log.critical("El pipeline colapsó por un error no controlado", exc_info=True)
        raise


if __name__ == "__main__":
    setup_logger()
    run_conciliacion()
