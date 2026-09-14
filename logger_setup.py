"""
Logging estruturado — grava em arquivo (output/logs/execucao_AAAAMMDD_HHMM.log).
Os logs técnicos foram removidos da tela da interface para não poluir a visão do usuário final.
"""

import logging
import os
from datetime import datetime
from config import LOG_DIR

def configurar_logger(nome: str = "prospeccao") -> logging.Logger:
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger  # Evita duplicar logs se importar duas vezes

    logger.setLevel(logging.INFO)

    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    caminho_log = os.path.join(LOG_DIR, f"execucao_{timestamp}.log")

    # Mantemos APENAS o FileHandler (salva no arquivo de log da pasta)
    file_handler = logging.FileHandler(caminho_log, encoding="utf-8")
    file_handler.setFormatter(formato)
    logger.addHandler(file_handler)

    # StreamHandler (que mandava pra tela) foi removido propositalmente.
    
    return logger

log = configurar_logger()