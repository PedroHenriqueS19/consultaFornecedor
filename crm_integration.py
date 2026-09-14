"""
ETAPA 4 (opcional) — Envio direto dos melhores leads para um CRM.

Só roda se CRM_PROVEDOR e CRM_API_KEY estiverem configurados via variável
de ambiente (ver config.py). Sem isso, o pipeline principal simplesmente
ignora esta etapa e o XLSX/CSV continuam sendo a entrega.

Como cada CRM tem seu próprio formato de payload, este arquivo traz apenas
o roteamento e um exemplo funcional para HubSpot (API de Companies) —
adapte `_enviar_hubspot` ou implemente `_enviar_pipedrive` /
`_enviar_rdstation` seguindo o mesmo padrão.
"""

import requests
import pandas as pd

from config import CRM_PROVEDOR, CRM_API_KEY, CRM_SCORE_MINIMO_PARA_ENVIO
from logger_setup import log


def _enviar_hubspot(row: pd.Series) -> bool:
    url = "https://api.hubapi.com/crm/v3/objects/companies"
    headers = {"Authorization": f"Bearer {CRM_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "properties": {
            "name": row.get("razao_social"),
            "phone": row.get("telefone1"),
            "domain": row.get("site_institucional"),
            "city": row.get("municipio_nome"),
            "description": f"CNPJ {row.get('cnpj')} | CNAE {row.get('cnae_descricao')} | "
                            f"Score {row.get('score_lead')}",
        }
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log.warning(f"falha ao enviar '{row.get('razao_social')}' para HubSpot: {e}")
        return False


def _enviar_pipedrive(row: pd.Series) -> bool:
    # Esqueleto — ver docs: https://developers.pipedrive.com/docs/api/v1/Organizations
    log.warning("Integração com Pipedrive ainda não implementada — ver crm_integration.py")
    return False


def _enviar_rdstation(row: pd.Series) -> bool:
    # Esqueleto — ver docs: https://developers.rdstation.com/
    log.warning("Integração com RD Station ainda não implementada — ver crm_integration.py")
    return False


ENVIADORES = {
    "hubspot": _enviar_hubspot,
    "pipedrive": _enviar_pipedrive,
    "rdstation": _enviar_rdstation,
}


def enviar_leads_para_crm(df: pd.DataFrame) -> None:
    if not CRM_PROVEDOR:
        log.info("CRM_PROVEDOR não configurado — pulando envio ao CRM (isso é opcional).")
        return
    if CRM_PROVEDOR not in ENVIADORES:
        log.warning(f"CRM_PROVEDOR='{CRM_PROVEDOR}' desconhecido. Opções: {list(ENVIADORES)}")
        return
    if not CRM_API_KEY:
        log.warning("CRM_API_KEY não configurada — pulando envio ao CRM.")
        return

    df_alvo = df[df["score_lead"] >= CRM_SCORE_MINIMO_PARA_ENVIO]
    log.info(f"Enviando {len(df_alvo)} leads (score >= {CRM_SCORE_MINIMO_PARA_ENVIO}) "
             f"para {CRM_PROVEDOR}...")

    enviador = ENVIADORES[CRM_PROVEDOR]
    sucesso = sum(enviador(row) for _, row in df_alvo.iterrows())
    log.info(f"Envio concluído: {sucesso}/{len(df_alvo)} leads enviados com sucesso.")
