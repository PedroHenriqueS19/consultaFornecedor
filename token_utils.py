"""
Geração e validação de token de descadastro — separado do Flask
para que etapa5_envio.py (que roda no seu PC) não precise ter
Flask instalado só para gerar um token.
"""

import hmac
import hashlib
import base64
from urllib.parse import unquote

from config import CHAVE_SECRETA_TOKEN


def gerar_token(email: str) -> str:
    email_norm = email.strip().lower()
    assinatura = hmac.new(
        CHAVE_SECRETA_TOKEN.encode(), email_norm.encode(), hashlib.sha256
    ).hexdigest()
    payload = f"{email_norm}:{assinatura}"
    return base64.urlsafe_b64encode(payload.encode()).decode()


def validar_token(token: str) -> str | None:
    try:
        payload = base64.urlsafe_b64decode(unquote(token).encode()).decode()
        email_norm, assinatura_recebida = payload.rsplit(":", 1)
    except Exception:
        return None

    assinatura_esperada = hmac.new(
        CHAVE_SECRETA_TOKEN.encode(), email_norm.encode(), hashlib.sha256
    ).hexdigest()

    if hmac.compare_digest(assinatura_recebida, assinatura_esperada):
        return email_norm
    return None