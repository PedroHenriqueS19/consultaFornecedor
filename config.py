import os
import sys
from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    # Rodando como .exe empacotado — usa a pasta do .exe, não a pasta
    # temporária que o PyInstaller cria e apaga ao fechar o programa
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Rodando normalmente via "python app.py" / "python disparo_diario.py"
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

RAW_DIR = os.path.join(BASE_DIR, "raw")
EXTRACT_DIR = os.path.join(BASE_DIR, "extracted")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
HISTORICO_DIR = os.path.join(OUTPUT_DIR, "historico")
CHECKPOINT_DIR = os.path.join(BASE_DIR, "checkpoints")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CACHE_DB_PATH = os.path.join(BASE_DIR, "cache_mec.sqlite3")

for _d in (RAW_DIR, EXTRACT_DIR, OUTPUT_DIR, HISTORICO_DIR, CHECKPOINT_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)

SITUACAO_ATIVA = "02"
SIMPLES_NACIONAL_ARQUIVO_PREFIXO = "SIMPLES"

# Configurações de Qualidade/MEC mantidas intactas
CNAES_EMEC = {"8531700", "8532500", "8533300"} 
# CNAEs que devem ser buscados no SISTEC (Ensino Técnico)
CNAES_SISTEC = {"8541400", "8542200"}
MATCH_SIMILARITY_THRESHOLD = 85
CACHE_VALIDADE_DIAS = 30
PAUSA_ENTRE_REQUISICOES_SEGUNDOS = 1.0

DOMINIOS_GENERICOS_SUSPEITOS = {"gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "bol.com.br", "uol.com.br", "live.com", "icloud.com"}
PALAVRAS_DOMINIO_TERCEIRIZADO = ("contabil", "contador", "assessoria", "escritorio", "consultoria", "advogado", "advocacia", "juridico")
PESOS_SCORE = {"tem_email_confiavel": 30, "tem_telefone": 20, "confirmado_mec": 30, "eh_matriz": 10, "porte_medio_ou_maior": 10}

CRM_PROVEDOR = ""
CRM_API_KEY = ""
CRM_SCORE_MINIMO_PARA_ENVIO = 50

# --------------------------------------------------------------------------
# Configurações de disparo de e-mail (mala direta) — stack 100% free tier
# --------------------------------------------------------------------------

# Neon Postgres — usado pela lista de supressão (compartilhado entre local e Render)
DATABASE_URL = os.environ.get("DATABASE_URL", "")  # connection string do Neon
ENVIOS_DB_PATH = os.path.join(BASE_DIR, "envios_realizados.sqlite3")  # log local de quem já recebeu


# Brevo (SMTP relay grátis — 300 e-mails/dia)
SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587
SMTP_USUARIO = os.environ.get("SMTP_USUARIO", "")   # seu login Brevo
SMTP_SENHA = os.environ.get("SMTP_SENHA", "")       # chave SMTP gerada no painel Brevo

EMAIL_REMETENTE_NOME = "Anhanguera"
EMAIL_REMETENTE_ENDERECO = "gabriel.macedo@anhangueraempresas.com.br"

BASE_URL_OPTOUT = os.environ.get("BASE_URL_OPTOUT", "")
CHAVE_SECRETA_TOKEN = os.environ.get("CHAVE_SECRETA_TOKEN", "")

LIMITE_ENVIOS_POR_DIA = 10          # comece bem abaixo do teto de 300 — warm-up gradual
PAUSA_ENTRE_ENVIOS_SEGUNDOS = 15

# Validação — falha rápido e com mensagem clara, em vez de um erro
# confuso de SMTP/Postgres na hora do envio
def _validar_config_envio():
    faltando = []
    if not DATABASE_URL: faltando.append("DATABASE_URL")
    if not SMTP_USUARIO: faltando.append("SMTP_USUARIO")
    if not SMTP_SENHA: faltando.append("SMTP_SENHA")
    if not BASE_URL_OPTOUT: faltando.append("BASE_URL_OPTOUT")
    if not CHAVE_SECRETA_TOKEN: faltando.append("CHAVE_SECRETA_TOKEN")
    if faltando:
        print(f"[AVISO] Variáveis de ambiente não configuradas: {', '.join(faltando)}."
              f"O disparo de e-mail (campanha.py) vai falhar até isso ser definido.")

_validar_config_envio()