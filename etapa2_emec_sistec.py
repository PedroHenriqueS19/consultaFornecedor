"""
ETAPA 2 — Cruzamento com bases do MEC (site institucional / contato oficial)

AVISO IMPORTANTE:
----------------------------------------------------------------------------
e-MEC e SISTEC não oferecem dado aberto em lote — só consulta web dinâmica.
As funções `buscar_emec` e `buscar_sistec` são ESQUELETOS: funcionais em
termos de estrutura (cache, matching, tratamento de erro), mas o endpoint
HTTP real precisa ser capturado por você via F12 → Network no navegador,
porque não é documentado publicamente e muda sem aviso. Ver README.md.

MELHORIAS incluídas nesta versão:
  - Cache em SQLite (cache_mec.sqlite3): cada nome já buscado fica salvo
    com timestamp. Reexecuções dentro de CACHE_VALIDADE_DIAS não batem no
    MEC de novo — importante ao rodar mensalmente.
  - Fallback por busca externa quando não há match no e-MEC/SISTEC: tenta
    inferir o domínio institucional a partir de uma busca de texto (também
    é um esqueleto a conectar num provedor de busca — ver `buscar_fallback_web`).
----------------------------------------------------------------------------
"""

import sqlite3
import time
from datetime import datetime, timedelta

import requests
import pandas as pd
from rapidfuzz import fuzz

from config import (
    CACHE_DB_PATH, MATCH_SIMILARITY_THRESHOLD, CACHE_VALIDADE_DIAS,
    PAUSA_ENTRE_REQUISICOES_SEGUNDOS, CNAES_EMEC, CNAES_SISTEC,
)
from logger_setup import log

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ProspeccaoEduBot/1.0)"}


# --------------------------------------------------------------------------
# Cache SQLite
# --------------------------------------------------------------------------
def _conectar_cache() -> sqlite3.Connection:
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_mec (
            nome_normalizado TEXT PRIMARY KEY,
            fonte TEXT,
            nome_encontrado TEXT,
            score_similaridade INTEGER,
            site_institucional TEXT,
            situacao_mec TEXT,
            codigo_ies TEXT,
            consultado_em TEXT
        )
    """)
    return conn


def _normalizar(nome: str) -> str:
    # Proteção contra valores vazios (NaN/float) que vêm da base da Receita
    if not isinstance(nome, str):
        return ""
    return " ".join(nome.upper().strip().split())


def cache_buscar(nome: str) -> dict | None:
    conn = _conectar_cache()
    try:
        cur = conn.execute(
            "SELECT * FROM cache_mec WHERE nome_normalizado = ?", (_normalizar(nome),)
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        registro = dict(zip(cols, row))

        consultado_em = datetime.fromisoformat(registro["consultado_em"])
        if datetime.now() - consultado_em > timedelta(days=CACHE_VALIDADE_DIAS):
            return None  # expirado, força nova busca

        return registro
    finally:
        conn.close()


def cache_salvar(nome: str, resultado: dict) -> None:
    conn = _conectar_cache()
    try:
        conn.execute(
            """
            INSERT INTO cache_mec
                (nome_normalizado, fonte, nome_encontrado, score_similaridade,
                 site_institucional, situacao_mec, codigo_ies, consultado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nome_normalizado) DO UPDATE SET
                fonte=excluded.fonte, nome_encontrado=excluded.nome_encontrado,
                score_similaridade=excluded.score_similaridade,
                site_institucional=excluded.site_institucional,
                situacao_mec=excluded.situacao_mec, codigo_ies=excluded.codigo_ies,
                consultado_em=excluded.consultado_em
            """,
            (
                _normalizar(nome), resultado.get("fonte"), resultado.get("nome_encontrado"),
                resultado.get("score_similaridade"), resultado.get("site_institucional"),
                resultado.get("situacao_mec"), resultado.get("codigo_ies"),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _melhor_correspondencia(nome_alvo: str, candidatos: list[dict], campo_nome: str):
    melhor, melhor_score = None, 0
    for cand in candidatos:
        score = fuzz.token_sort_ratio(nome_alvo.upper(), cand.get(campo_nome, "").upper())
        if score > melhor_score:
            melhor, melhor_score = cand, score
    if melhor_score >= MATCH_SIMILARITY_THRESHOLD:
        return melhor, melhor_score
    return None, melhor_score


# --------------------------------------------------------------------------
# e-MEC / SISTEC (esqueletos — ver aviso no topo do arquivo)
# --------------------------------------------------------------------------
def buscar_emec(nome_ies: str, municipio: str = "SAO PAULO", uf: str = "SP") -> dict | None:
    try:
        # --- AJUSTAR conforme endpoint real capturado via F12 (ver README) ---
        # resp = requests.get("https://emec.mec.gov.br/emec/api/v1/instituicoes",
        #                      params={"nome": nome_ies, "municipio": municipio, "uf": uf},
        #                      headers=HEADERS, timeout=30)
        # resp.raise_for_status()
        # candidatos = resp.json().get("resultados", [])
        candidatos = []  # placeholder até o endpoint real ser configurado
        # ------------------------------------------------------------------

        if not candidatos:
            return None
        melhor, score = _melhor_correspondencia(nome_ies, candidatos, campo_nome="nome")
        if melhor:
            return {
                "fonte": "e-MEC", "nome_encontrado": melhor.get("nome"),
                "score_similaridade": score, "site_institucional": melhor.get("site"),
                "situacao_mec": melhor.get("situacao"), "codigo_ies": melhor.get("codigo_ies"),
            }
        return None
    except requests.RequestException as e:
        log.warning(f"falha ao consultar e-MEC para '{nome_ies}': {e}")
        return None


def buscar_sistec(nome_unidade: str, municipio: str = "SAO PAULO", uf: str = "SP") -> dict | None:
    try:
        session = requests.Session()
        # --- AJUSTAR conforme formulário real capturado via F12 (ver README) ---
        # resp = session.post(SISTEC_CONSULTA_URL,
        #                      data={"nomeUnidade": nome_unidade, "municipio": municipio, "uf": uf},
        #                      headers=HEADERS, timeout=30)
        # resp.raise_for_status()
        # candidatos = _parsear_resultados_html(resp.text)
        candidatos = []  # placeholder até o formulário real ser mapeado
        # ------------------------------------------------------------------

        if not candidatos:
            return None
        melhor, score = _melhor_correspondencia(nome_unidade, candidatos, campo_nome="nome")
        if melhor:
            return {
                "fonte": "SISTEC", "nome_encontrado": melhor.get("nome"),
                "score_similaridade": score, "site_institucional": melhor.get("site"),
                "situacao_mec": melhor.get("situacao"),
            }
        return None
    except requests.RequestException as e:
        log.warning(f"falha ao consultar SISTEC para '{nome_unidade}': {e}")
        return None


def buscar_fallback_web(nome_empresa: str) -> dict | None:
    """
    Último recurso quando não há match no e-MEC/SISTEC: tenta achar o site
    institucional via um provedor de busca. Também é um esqueleto — plugue
    aqui a API de busca que sua empresa já usa/paga (Bing Search API,
    SerpAPI, Google Custom Search, etc.), pois provedores de busca em geral
    não permitem scraping direto do HTML de resultados sem violar termos
    de uso.
    """
    # --- AJUSTAR conforme provedor de busca escolhido ---
    # resp = requests.get("https://api.bing.microsoft.com/v7.0/search",
    #                      params={"q": f'"{nome_empresa}" site oficial'},
    #                      headers={"Ocp-Apim-Subscription-Key": "SUA_CHAVE"}, timeout=30)
    # primeiro_resultado = resp.json().get("webPages", {}).get("value", [{}])[0]
    # return {"fonte": "busca_web", "site_institucional": primeiro_resultado.get("url")}
    return None


# --------------------------------------------------------------------------
# Orquestração da etapa
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Orquestração da etapa
# --------------------------------------------------------------------------
def enriquecer_dataframe(df: pd.DataFrame, usar_fallback_web: bool = False) -> pd.DataFrame:
    log.info("=== ETAPA 2: Cruzamento com e-MEC / SISTEC (com cache) ===")
    print(f"\n🎓 Iniciando cruzamento de {len(df)} escolas com as bases do MEC...")
    
    resultados = []
    total = len(df)
    hits_cache = 0

    for i, row in df.iterrows():
        nome_busca = row.get("nome_fantasia") or row.get("razao_social", "")
        cnae = row.get("cnae_fiscal_principal", "")

        # Se não for escola, pula na hora
        if cnae not in CNAES_EMEC and cnae not in CNAES_SISTEC:
            resultados.append({})
            continue

        cacheado = cache_buscar(nome_busca)
        if cacheado:
            hits_cache += 1
            resultados.append(cacheado)
            continue

        enriquecido = None
        if cnae in CNAES_EMEC:
            enriquecido = buscar_emec(nome_busca)
        elif cnae in CNAES_SISTEC:
            enriquecido = buscar_sistec(nome_busca)

        if not enriquecido and usar_fallback_web:
            enriquecido = buscar_fallback_web(nome_busca)

        if enriquecido:
            cache_salvar(nome_busca, enriquecido)

        resultados.append(enriquecido or {})

        # Mostra o progresso na interface gráfica a cada 25 consultas
        if (i + 1) % 25 == 0 or (i + 1) == total:
            msg = f"  ⏳ Consultando MEC/SISTEC: {i + 1}/{total} (Cache local: {hits_cache})"
            log.info(msg)
            print(msg) # Imprime direto na telinha do seu app!

        time.sleep(PAUSA_ENTRE_REQUISICOES_SEGUNDOS)

    print(f"✅ Cruzamento MEC concluído! (Uso do cache: {hits_cache}/{total})")
    
    df_enriquecido = pd.DataFrame(resultados)
    return pd.concat([df.reset_index(drop=True), df_enriquecido.reset_index(drop=True)], axis=1)