"""
ETAPA 1 — Receita Federal (Dados Abertos do CNPJ)
"""

import os
import zipfile
import pandas as pd
import requests
import re

from config import RAW_DIR, EXTRACT_DIR, CHECKPOINT_DIR, SITUACAO_ATIVA
from download_utils import baixar_arquivo_resumivel, descobrir_pasta_e_arquivos_rfb
from logger_setup import log
from datetime import datetime

CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "etapa1.parquet")

COLUNAS_ESTABELECIMENTO = [
    "cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial",
    "nome_fantasia", "situacao_cadastral", "data_situacao_cadastral",
    "motivo_situacao_cadastral", "nome_cidade_exterior", "pais",
    "data_inicio_atividade", "cnae_fiscal_principal", "cnae_fiscal_secundaria",
    "tipo_logradouro", "logradouro", "numero", "complemento", "bairro",
    "cep", "uf", "municipio", "ddd1", "telefone1", "ddd2", "telefone2",
    "ddd_fax", "fax", "email", "situacao_especial", "data_situacao_especial",
]

COLUNAS_EMPRESA = [
    "cnpj_basico", "razao_social", "natureza_juridica",
    "qualificacao_responsavel", "capital_social", "porte_empresa", "ente_federativo",
]
COLUNAS_MUNICIPIO = ["codigo", "nome"]

def gerenciar_bases_rfb(fazer_download: bool) -> dict:
    if fazer_download:
        url_pasta, arquivos = descobrir_pasta_e_arquivos_rfb()
        alvos = [a for a in arquivos if a.upper().startswith(("ESTABELECIMENTOS", "EMPRESAS", "MUNICIPIOS"))]
        for nome in alvos:
            baixar_arquivo_resumivel(url_pasta + nome, os.path.join(RAW_DIR, nome))

    arquivos_locais = os.listdir(RAW_DIR)
    grupos = {"estabelecimentos": [], "empresas": [], "municipios": []}
    
    for a in arquivos_locais:
        nome_up = a.upper()
        if not nome_up.endswith(".ZIP"): continue
        caminho_completo = os.path.join(RAW_DIR, a)
        
        if "MUNIC" in nome_up: grupos["municipios"].append(caminho_completo)
        elif "ESTABELECIMENTO" in nome_up: grupos["estabelecimentos"].append(caminho_completo)
        elif "EMPRESA" in nome_up: grupos["empresas"].append(caminho_completo)

    faltando = []
    if not grupos["municipios"]: faltando.append("Municipios")
    if not grupos["estabelecimentos"]: faltando.append("Estabelecimentos")
    if not grupos["empresas"]: faltando.append("Empresas")

    if faltando:
        raise RuntimeError(f"Falta arquivos na pasta 'raw': {', '.join(faltando)}. Marque a opção de download.")
    return grupos

def extrair_zip(caminho_zip: str) -> list[str]:
    with zipfile.ZipFile(caminho_zip, "r") as z:
        z.extractall(EXTRACT_DIR)
        return [os.path.join(EXTRACT_DIR, n) for n in z.namelist()]

def carregar_codigos_municipio(caminhos_municipios: list[str], nomes_alvo: list[str]) -> dict:
    nomes_alvo_norm = {n.upper().strip() for n in nomes_alvo}
    encontrados = {}
    for zpath in caminhos_municipios:
        for csv_path in extrair_zip(zpath):
            df = pd.read_csv(csv_path, sep=";", encoding="latin-1", header=None, names=COLUNAS_MUNICIPIO, dtype=str)
            match = df[df["nome"].str.upper().str.strip().isin(nomes_alvo_norm)]
            for _, row in match.iterrows():
                encontrados[row["nome"].upper().strip()] = row["codigo"]
    return encontrados

def cnae_bate(valor_principal: str, cnaes_alvo: dict) -> bool:
    # REQUISITO 3: Filtro estrito. Ignoramos a atividade secundária.
    return valor_principal in cnaes_alvo

def filtrar_estabelecimentos(caminhos_estab: list[str], codigos_municipio: list[str], 
                             cnaes_alvo: dict, apenas_ativas: bool) -> pd.DataFrame:
    dfs_filtrados = []
    codigos_set = set(codigos_municipio)

    for zpath in caminhos_estab:
        for csv_path in extrair_zip(zpath):
            log.info(f"  filtrando {os.path.basename(csv_path)}...")
            for chunk in pd.read_csv(csv_path, sep=";", encoding="latin-1", header=None,
                                     names=COLUNAS_ESTABELECIMENTO, dtype=str, chunksize=300_000, on_bad_lines="skip"):
                chunk = chunk[chunk["municipio"].isin(codigos_set)]
                if apenas_ativas: chunk = chunk[chunk["situacao_cadastral"] == SITUACAO_ATIVA]
                if chunk.empty: continue
                
                # Aplica o filtro estrito
                mask = chunk.apply(lambda row: cnae_bate(row["cnae_fiscal_principal"], cnaes_alvo), axis=1)
                filtrado = chunk[mask]
                if not filtrado.empty: dfs_filtrados.append(filtrado)

    if not dfs_filtrados: return pd.DataFrame(columns=COLUNAS_ESTABELECIMENTO)
    return pd.concat(dfs_filtrados, ignore_index=True)

def carregar_empresas(caminhos_emp: list[str]) -> pd.DataFrame:
    dfs = []
    for zpath in caminhos_emp:
        for csv_path in extrair_zip(zpath):
            df = pd.read_csv(csv_path, sep=";", encoding="latin-1", header=None, names=COLUNAS_EMPRESA, dtype=str, on_bad_lines="skip")
            dfs.append(df[["cnpj_basico", "razao_social", "porte_empresa"]])
    if not dfs: return pd.DataFrame(columns=["cnpj_basico", "razao_social", "porte_empresa"])
    return pd.concat(dfs, ignore_index=True)

def formatar_celular(ddd, telefone) -> str | None:
    """
    Verifica se o número é celular (9 dígitos, começando em 9) e,
    se for, retorna já formatado como (XX) XXXXX-XXXX.
    """
    if not isinstance(ddd, str) or not isinstance(telefone, str):
        return None

    ddd = ddd.strip()
    telefone = telefone.strip()

    if not ddd or not telefone:
        return None

    if len(telefone) == 9 and telefone.startswith("9"):
        return f"({ddd}) {telefone[:5]}-{telefone[5:]}"

    return None

def formatar_data(data_str):
    """Converte AAAAMMDD (formato bruto da RFB) para DD/MM/AAAA."""
    if not isinstance(data_str, str) or len(data_str.strip()) != 8:
        return None
    try:
        return datetime.strptime(data_str.strip(), "%Y%m%d").strftime("%d/%m/%Y")
    except ValueError:
        return None

def rodar_etapa1(cnaes_alvo: dict, municipios_alvo: list[str], usar_checkpoint: bool, apenas_ativas: bool, fazer_download: bool) -> pd.DataFrame:
    if usar_checkpoint and os.path.exists(CHECKPOINT_PATH):
        log.info("Checkpoint da Etapa 1 encontrado — pulando reprocessamento.")
        return pd.read_parquet(CHECKPOINT_PATH)

    log.info("=== ETAPA 1: Receita Federal — CNPJ ===")
    caminhos = gerenciar_bases_rfb(fazer_download)

    mapa_codigos = carregar_codigos_municipio(caminhos["municipios"], municipios_alvo)
    if not mapa_codigos:
        raise RuntimeError("Nenhum município alvo foi localizado. Verifique a ortografia.")
        
    df_estab = filtrar_estabelecimentos(caminhos["estabelecimentos"], list(mapa_codigos.values()), cnaes_alvo, apenas_ativas)
    log.info(f"  {len(df_estab)} estabelecimentos encontrados")

    if df_estab.empty: return df_estab

    df_emp = carregar_empresas(caminhos["empresas"])
    df_final = df_estab.merge(df_emp, on="cnpj_basico", how="left")
    df_final["cnpj"] = df_final["cnpj_basico"] + df_final["cnpj_ordem"] + df_final["cnpj_dv"]
    df_final["cnae_descricao"] = df_final["cnae_fiscal_principal"].map(cnaes_alvo)
    df_final["eh_matriz"] = df_final["identificador_matriz_filial"] == "1"
    
    codigo_para_nome = {v: k for k, v in mapa_codigos.items()}
    df_final["municipio_nome"] = df_final["municipio"].map(codigo_para_nome)
    df_final["data_abertura"] = df_final["data_inicio_atividade"].apply(formatar_data)

    df_final["celular1"] = df_final.apply(
        lambda r: formatar_celular(r["ddd1"], r["telefone1"]), axis=1
    )
    df_final["celular2"] = df_final.apply(
        lambda r: formatar_celular(r["ddd2"], r["telefone2"]), axis=1
    )

    celulares_por_linha = df_final[["celular1", "celular2"]].apply(
        lambda r: [c for c in r if c], axis=1
    )
    df_final["telefone_celular"] = celulares_por_linha.apply(
        lambda lst: " / ".join(dict.fromkeys(lst))
    )
    df_final["possui_celular"] = celulares_por_linha.apply(lambda lst: len(lst) > 0)

    df_final.to_parquet(CHECKPOINT_PATH, index=False)
    return df_final