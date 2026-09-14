"""
ETAPA 4 — Lista de supressão (opt-out), em Postgres (Neon).

Usa Postgres em vez de SQLite porque este banco precisa ser acessado tanto
pelo seu PC (antes de disparar) quanto pelo servidor de opt-out hospedado
no Render — e o disco do Render é efêmero, então SQLite local lá se perderia.
"""

import psycopg2
import pandas as pd
from datetime import datetime

from config import DATABASE_URL
from logger_setup import log


def _conectar():
    conn = psycopg2.connect(DATABASE_URL)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS supressao (
                email TEXT PRIMARY KEY,
                motivo TEXT,
                suprimido_em TIMESTAMP
            )
        """)
    conn.commit()
    return conn


def suprimir_email(email: str, motivo: str = "opt-out via link") -> None:
    if not email:
        return
    email_norm = email.strip().lower()
    conn = _conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO supressao (email, motivo, suprimido_em)
                VALUES (%s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                    motivo = EXCLUDED.motivo,
                    suprimido_em = EXCLUDED.suprimido_em
                """,
                (email_norm, motivo, datetime.now()),
            )
        conn.commit()
        log.info(f"E-mail suprimido: {email_norm} ({motivo})")
    finally:
        conn.close()


def email_suprimido(email: str) -> bool:
    if not email:
        return False
    conn = _conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM supressao WHERE email = %s", (email.strip().lower(),))
            return cur.fetchone() is not None
    finally:
        conn.close()


def carregar_todos_suprimidos() -> set[str]:
    conn = _conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM supressao")
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def aplicar_supressao(df: pd.DataFrame, coluna_email: str = "email") -> pd.DataFrame:
    suprimidos = carregar_todos_suprimidos()
    df = df.copy()
    df["elegivel_envio"] = ~df[coluna_email].str.lower().isin(suprimidos)

    n_suprimidos = (~df["elegivel_envio"]).sum()
    log.info(f"Supressão aplicada: {n_suprimidos}/{len(df)} e-mails já haviam pedido opt-out.")
    return df