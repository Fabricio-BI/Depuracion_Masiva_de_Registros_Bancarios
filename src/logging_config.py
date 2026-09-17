import logging
from logging.handlers import RotatingFileHandler

from src.project_config import LOG_DIR, LOG_FILE


def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    # 1. Formato DETALLADO para el archivo físico (.log)
    formato_archivo = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
    )
    formatter_archivo = logging.Formatter(formato_archivo, datefmt="%Y-%m-%d %H:%M:%S")

    # 2. Formato para la consola
    formato_consola = "%(asctime)s | %(levelname)-7s | %(message)s"
    formatter_consola = logging.Formatter(formato_consola, datefmt="%Y-%m-%d %H:%M:%S")

    # 3. Handler de consola
    handler_consola = logging.StreamHandler()
    handler_consola.setFormatter(formatter_consola)
    logger.addHandler(handler_consola)

    # 4. Handler de archivo (con tolerancia a fallos de permisos)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler_archivo = RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
        handler_archivo.setFormatter(formatter_archivo)
        logger.addHandler(handler_archivo)
    except (OSError, PermissionError) as e:
        logger.warning(
            f"No se pudo inicializar el archivo de logs en '{LOG_FILE}' por problemas de permisos ({e}). "
            f"La aplicación continuará registrando únicamente por consola."
        )

    # 5. Silenciar logs ruidosos de dependencias de terceros
    for lib_name in ("urllib3", "google", "google_genai", "httpcore", "httpx"):
        logging.getLogger(lib_name).setLevel(logging.WARNING)

    return logger
