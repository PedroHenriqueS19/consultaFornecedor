"""
ETAPA 5 — Disparo de mala direta (SMTP), com token de descadastro,
throttling e registro de quem já recebeu (evita duplicidade).
"""

import sqlite3
import smtplib
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USUARIO, SMTP_SENHA,
    EMAIL_REMETENTE_NOME, EMAIL_REMETENTE_ENDERECO,
    BASE_URL_OPTOUT, LIMITE_ENVIOS_POR_DIA, PAUSA_ENTRE_ENVIOS_SEGUNDOS,
    ENVIOS_DB_PATH,
)
from token_utils import gerar_token
from logger_setup import log


def _conectar_envios() -> sqlite3.Connection:
    conn = sqlite3.connect(ENVIOS_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS envios (
            email TEXT PRIMARY KEY,
            enviado_em TEXT,
            assunto TEXT
        )
    """)
    return conn


def ja_enviado(email: str) -> bool:
    conn = _conectar_envios()
    try:
        cur = conn.execute("SELECT 1 FROM envios WHERE email = ?", (email.lower(),))
        return cur.fetchone() is not None
    finally:
        conn.close()


def registrar_envio(email: str, assunto: str) -> None:
    conn = _conectar_envios()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO envios (email, enviado_em, assunto) VALUES (?, ?, ?)",
            (email.lower(), datetime.now().isoformat(), assunto),
        )
        conn.commit()
    finally:
        conn.close()


def montar_corpo_html(nome_empresa: str, corpo_template: str, email_destino: str) -> str:
    token = gerar_token(email_destino)
    link_optout = f"{BASE_URL_OPTOUT}?token={token}"

    corpo = corpo_template.replace("{{nome_empresa}}", nome_empresa or "")

    return f"""
    <html><body>
        {corpo}
        <hr>
        <p style="font-size: 11px; color: #888;">
            Você recebeu este e-mail por ser uma empresa de interesse comercial legítimo.
            Se não deseja mais receber nossos contatos,
            <a href="{link_optout}">clique aqui para se descadastrar</a>.
        </p>
    </body></html>
    """


def enviar_email(destinatario: str, assunto: str, corpo_html: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = f"{EMAIL_REMETENTE_NOME} <{EMAIL_REMETENTE_ENDERECO}>"
    msg["To"] = destinatario
    msg.attach(MIMEText(corpo_html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(SMTP_USUARIO, SMTP_SENHA)
            server.sendmail(EMAIL_REMETENTE_ENDERECO, destinatario, msg.as_string())
        return True
    except smtplib.SMTPException as e:
        print(f"[ERRO SMTP] Falha ao enviar para {destinatario}: {e}")  # NOVO — visível no terminal
        log.warning(f"Falha ao enviar para {destinatario}: {e}")
        return False


def rodar_etapa5(df: pd.DataFrame, assunto: str, corpo_template: str) -> None:
    log.info("=== ETAPA 5: Disparo de mala direta ===")

    # Só quem é elegível (não suprimido) e ainda não recebeu antes
    df_alvo = df[df["elegivel_envio"] == True].copy()
    df_alvo = df_alvo[~df_alvo["email"].apply(ja_enviado)]

    df_alvo = df_alvo.head(LIMITE_ENVIOS_POR_DIA)  # respeita cota diária

    print(f"\n📧 Preparando disparo para {len(df_alvo)} empresas (limite diário: {LIMITE_ENVIOS_POR_DIA})...")

    enviados, falhas = 0, 0
    for _, row in df_alvo.iterrows():
        email = row.get("email")
        if not isinstance(email, str) or "@" not in email:
            continue

        corpo_html = montar_corpo_html(row.get("razao_social", ""), corpo_template, email)
        sucesso = enviar_email(email, assunto, corpo_html)

        if sucesso:
            registrar_envio(email, assunto)
            enviados += 1
        else:
            falhas += 1

        time.sleep(PAUSA_ENTRE_ENVIOS_SEGUNDOS)

    print(f"✅ Disparo concluído: {enviados} enviados, {falhas} falharam.")
    log.info(f"Disparo concluído: {enviados} enviados, {falhas} falhas.")