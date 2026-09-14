"""
Persistência da campanha ativa para disparo diário automático.
"""

import json
import os
from datetime import datetime

import pandas as pd

from config import BASE_DIR, LIMITE_ENVIOS_POR_DIA
from etapa5_envio import ja_enviado
from etapa4_supressao import carregar_todos_suprimidos

CAMPANHA_ATIVA_PATH = os.path.join(BASE_DIR, "campanha_ativa.json")


def salvar_campanha_ativa(caminho_planilha: str, assunto: str, corpo: str) -> None:
    dados = {
        "caminho_planilha": os.path.abspath(caminho_planilha),
        "assunto": assunto,
        "corpo": corpo,
        "ativada_em": datetime.now().isoformat(),
    }
    with open(CAMPANHA_ATIVA_PATH, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def carregar_campanha_ativa() -> dict | None:
    if not os.path.exists(CAMPANHA_ATIVA_PATH):
        return None
    with open(CAMPANHA_ATIVA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def desativar_campanha() -> None:
    if os.path.exists(CAMPANHA_ATIVA_PATH):
        os.remove(CAMPANHA_ATIVA_PATH)


def calcular_progresso(df: pd.DataFrame) -> dict:
    """
    Calcula quantos e-mails elegíveis já foram enviados, quantos faltam,
    e uma estimativa de dias úteis (seg-sáb) restantes para concluir.
    """
    suprimidos = carregar_todos_suprimidos()
    df_elegivel = df[~df["email"].str.lower().isin(suprimidos)].copy()

    total_elegivel = len(df_elegivel)
    ja_enviados = df_elegivel["email"].apply(ja_enviado).sum()
    restantes = total_elegivel - ja_enviados

    dias_restantes = 0
    if restantes > 0 and LIMITE_ENVIOS_POR_DIA > 0:
        dias_restantes = -(-restantes // LIMITE_ENVIOS_POR_DIA)  # arredonda pra cima

    return {
        "total_elegivel": int(total_elegivel),
        "enviados": int(ja_enviados),
        "restantes": int(restantes),
        "dias_restantes_estimado": int(dias_restantes),
    }