import os
import pandas as pd
from config import RAW_DIR, SIMPLES_NACIONAL_ARQUIVO_PREFIXO
from etapa1_rfb import extrair_zip
from download_utils import baixar_arquivo_resumivel, descobrir_pasta_e_arquivos_rfb
from logger_setup import log

COLUNAS_SIMPLES = [
    "cnpj_basico", "opcao_simples", "data_opcao_simples", "data_exclusao_simples",
    "opcao_mei", "data_opcao_mei", "data_exclusao_mei",
]

def gerenciar_simples_nacional(fazer_download: bool) -> list[str]:
    if fazer_download:
        url_pasta, arquivos = descobrir_pasta_e_arquivos_rfb()
        alvos = [a for a in arquivos if a.upper().startswith(SIMPLES_NACIONAL_ARQUIVO_PREFIXO)]
        for nome in alvos:
            baixar_arquivo_resumivel(url_pasta + nome, os.path.join(RAW_DIR, nome))

    arquivos_locais = os.listdir(RAW_DIR)
    return [os.path.join(RAW_DIR, a) for a in arquivos_locais if a.upper().startswith(SIMPLES_NACIONAL_ARQUIVO_PREFIXO) and a.upper().endswith(".ZIP")]

def carregar_simples(cnpjs_basicos: set[str], fazer_download: bool) -> pd.DataFrame:
    caminhos_zip = gerenciar_simples_nacional(fazer_download)
    if not caminhos_zip:
        log.warning("Arquivo do Simples Nacional não encontrado. Continuando sem dados do Simples.")
        return pd.DataFrame(columns=COLUNAS_SIMPLES)

    dfs = []
    for zpath in caminhos_zip:
        for csv_path in extrair_zip(zpath):
            for chunk in pd.read_csv(csv_path, sep=";", encoding="latin-1", header=None, names=COLUNAS_SIMPLES, dtype=str, chunksize=500_000, on_bad_lines="skip"):
                filtrado = chunk[chunk["cnpj_basico"].isin(cnpjs_basicos)]
                if not filtrado.empty: dfs.append(filtrado)

    if not dfs: return pd.DataFrame(columns=COLUNAS_SIMPLES)
    return pd.concat(dfs, ignore_index=True)

def classificar_porte_real(row) -> str:
    if row.get("opcao_mei") == "S": return "MEI"
    if row.get("opcao_simples") == "S": return "ME/EPP (Simples)"
    return {"00": "Demais (não ME/EPP)", "01": "Não informado", "03": "ME", "05": "EPP"}.get(row.get("porte_empresa"), "Não informado")

def rodar_etapa1b(df: pd.DataFrame, fazer_download: bool = False) -> pd.DataFrame:
    log.info("=== ETAPA 1b: Simples Nacional (porte real) ===")
    if df.empty: return df
    df_simples = carregar_simples(set(df["cnpj_basico"].unique()), fazer_download)
    df = df.merge(df_simples, on="cnpj_basico", how="left")
    df["porte_real"] = df.apply(classificar_porte_real, axis=1)
    return df