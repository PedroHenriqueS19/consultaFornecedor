"""
ETAPA 2b — Qualidade do dado: e-mail confiável, geolocalização e score de lead
"""

import time
import requests
import pandas as pd

from config import (
    DOMINIOS_GENERICOS_SUSPEITOS, PALAVRAS_DOMINIO_TERCEIRIZADO, PESOS_SCORE,
)
from logger_setup import log

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ProspeccaoB2BBot/1.0)"}

# --------------------------------------------------------------------------
# Validação heurística de e-mail
# --------------------------------------------------------------------------
def avaliar_email(email: str) -> tuple[bool, str]:
    if not isinstance(email, str) or "@" not in email:
        return False, "sem e-mail cadastrado"

    dominio = email.split("@")[-1].lower().strip()

    if dominio in DOMINIOS_GENERICOS_SUSPEITOS:
        return False, f"domínio genérico ({dominio}) — provável e-mail pessoal"

    if any(palavra in dominio for palavra in PALAVRAS_DOMINIO_TERCEIRIZADO):
        return False, f"domínio de terceiro ({dominio}) — provável assessoria"

    return True, "domínio próprio, aparenta ser institucional"

def aplicar_validacao_email(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Validando e-mails (heurística de domínio confiável)...")
    avaliacoes = df["email"].apply(avaliar_email)
    df["email_confiavel"] = avaliacoes.apply(lambda t: t[0])
    df["email_confiavel_motivo"] = avaliacoes.apply(lambda t: t[1])
    n_confiaveis = df["email_confiavel"].sum()
    log.info(f"  {n_confiaveis}/{len(df)} e-mails classificados como confiáveis")
    return df

# --------------------------------------------------------------------------
# Geolocalização via CEP
# --------------------------------------------------------------------------
def geolocalizar_cep(cep: str) -> dict | None:
    if not isinstance(cep, str) or len(cep.strip()) < 8:
        return None
    cep_limpo = "".join(filter(str.isdigit, cep))
    try:
        resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        dados = resp.json()
        if dados.get("erro"):
            return None
        return {
            "logradouro_viacep": dados.get("logradouro"),
            "bairro_viacep": dados.get("bairro"),
            "cidade_viacep": dados.get("localidade"),
            "uf_viacep": dados.get("uf"),
        }
    except requests.RequestException as e:
        log.warning(f"falha ao consultar ViaCEP para {cep}: {e}")
        return None

def aplicar_geolocalizacao(df: pd.DataFrame, pausa_segundos: float = 0.3) -> pd.DataFrame:
    log.info("Geolocalizando endereços via ViaCEP (pode demorar)...")
    resultados = []
    for i, cep in enumerate(df["cep"]):
        resultados.append(geolocalizar_cep(cep) or {})
        if (i + 1) % 50 == 0:
            log.info(f"  progresso geolocalização: {i + 1}/{len(df)}")
        time.sleep(pausa_segundos)

    df_geo = pd.DataFrame(resultados)
    return pd.concat([df.reset_index(drop=True), df_geo.reset_index(drop=True)], axis=1)

# --------------------------------------------------------------------------
# Score de qualidade do lead
# --------------------------------------------------------------------------
def calcular_score(row) -> int:
    score = 0
    if row.get("email_confiavel"):
        score += PESOS_SCORE.get("tem_email_confiavel", 0)
    if isinstance(row.get("telefone1"), str) and row.get("telefone1").strip():
        score += PESOS_SCORE.get("tem_telefone", 0)
    if row.get("fonte") in ("e-MEC", "SISTEC"):
        score += PESOS_SCORE.get("confirmado_mec", 0)
    if row.get("eh_matriz"):
        score += PESOS_SCORE.get("eh_matriz", 0)
    
    porte = str(row.get("porte_real", ""))
    if porte in ("EPP", "Demais (não ME/EPP)", "ME/EPP (Simples)"):
        score += PESOS_SCORE.get("porte_medio_ou_maior", 0)
    return score

def aplicar_score(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Calculando score de qualidade do lead (0-100)...")
    df["score_lead"] = df.apply(calcular_score, axis=1)
    df = df.sort_values("score_lead", ascending=False).reset_index(drop=True)
    
    score_medio = df['score_lead'].mean() if not df.empty else 0
    leads_quentes = (df['score_lead'] >= 70).sum() if not df.empty else 0
    
    log.info(f"  score médio: {score_medio:.1f} | leads com score >= 70: {leads_quentes}")
    return df

def rodar_etapa2b(df: pd.DataFrame, geolocalizar: bool = False) -> pd.DataFrame:
    log.info("=== ETAPA 2b: Qualidade do dado (e-mail, geo, score) ===")
    if df.empty:
        return df
    df = aplicar_validacao_email(df)
    if geolocalizar:
        df = aplicar_geolocalizacao(df)
    df = aplicar_score(df)
    return df