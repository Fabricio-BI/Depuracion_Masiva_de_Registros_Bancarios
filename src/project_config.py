from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT/"data"/"raw"
PROCESSED_DIR = ROOT/"data"/"processed"

BANK_FILE = RAW_DIR/"estado_cuenta.xlsx"
ACCOUNT_FILE = RAW_DIR/"mayor_contable.xlsx"
PROCESSED_FILE =PROCESSED_DIR/"conciliacion_resultado.xlsx"

LOG_DIR = ROOT/"log"
LOG_FILE = LOG_DIR /"conc.log"


# Constantes de la conciliacion

COLS_REQUERIDAS_BANCO =[
    'Banco',
    'Cuenta bancaria',
    'Referencia',
    'Fecha valor',
    'Importe'
]

COLS_REQUERIDAS_ERP=[
    'Fecha de documento',
    'Ref_transaccion',
    'Clave_2',
    'Importe en moneda local'
]


# Columnas requeridas para la Capa 2
COLS_FUZZY_BANK = ["Referencia", "Importe"]
COLS_FUZZY_ERP = ["Ref_transaccion", "Importe en moneda local"]

COLS_FUZZY_REQUERIDAS = ['pendiente_Ref_transaccion', 'deposito_Cuenta bancaria',
                          'deposito_Fecha valor', 'deposito_Importe', 'deposito_Referencia',
                          'deposito_Banco', 'pendiente_Clave_2']
