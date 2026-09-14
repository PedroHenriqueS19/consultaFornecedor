"""
Testes rápidos das funções mais sensíveis do pipeline: fuzzy matching de
nomes (Etapa 2) e heurística de e-mail confiável (Etapa 2b).

Rodar com:
    python -m pytest tests/ -v
ou, sem pytest instalado:
    python tests/test_matching.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rapidfuzz import fuzz
from config import MATCH_SIMILARITY_THRESHOLD
from etapa2b_qualidade import avaliar_email


# --------------------------------------------------------------------------
# Casos conhecidos de nomes que DEVEM (ou NÃO devem) casar acima do limiar
# --------------------------------------------------------------------------
CASOS_MATCH_ESPERADO = [
    # (nome_rfb, nome_mec, deveria_bater)
    ("UNIVERSIDADE PAULISTA SA", "UNIVERSIDADE PAULISTA - UNIP", False),  # sigla reduz score — ver nota abaixo
    ("FUNDACAO GETULIO VARGAS", "FUNDACAO GETULIO VARGAS", True),
    ("CENTRO UNIVERSITARIO SENAC", "CENTRO UNIVERSITARIO SENAC SP", True),
    ("ESCOLA TECNICA XYZ LTDA", "COLEGIO ABC LTDA", False),
]


def test_fuzzy_matching_casos_conhecidos():
    falhas = []
    for nome_rfb, nome_mec, deveria_bater in CASOS_MATCH_ESPERADO:
        score = fuzz.token_sort_ratio(nome_rfb.upper(), nome_mec.upper())
        bateu = score >= MATCH_SIMILARITY_THRESHOLD
        if bateu != deveria_bater:
            falhas.append(
                f"'{nome_rfb}' vs '{nome_mec}' -> score={score} "
                f"(esperado bater={deveria_bater}, obtido={bateu})"
            )
    assert not falhas, "\n".join(falhas)


def test_email_dominio_generico_marcado_nao_confiavel():
    confiavel, motivo = avaliar_email("diretoria@gmail.com")
    assert confiavel is False
    assert "genérico" in motivo


def test_email_dominio_contabil_marcado_nao_confiavel():
    confiavel, motivo = avaliar_email("financeiro@assessoriacontabil.com.br")
    assert confiavel is False
    assert "terceiro" in motivo


def test_email_dominio_proprio_marcado_confiavel():
    confiavel, motivo = avaliar_email("contato@faculdadeexemplo.edu.br")
    assert confiavel is True


def test_email_vazio_marcado_nao_confiavel():
    confiavel, motivo = avaliar_email(None)
    assert confiavel is False


if __name__ == "__main__":
    testes = [
        test_fuzzy_matching_casos_conhecidos,
        test_email_dominio_generico_marcado_nao_confiavel,
        test_email_dominio_contabil_marcado_nao_confiavel,
        test_email_dominio_proprio_marcado_confiavel,
        test_email_vazio_marcado_nao_confiavel,
    ]
    falhas = 0
    for teste in testes:
        try:
            teste()
            print(f"OK   - {teste.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"FALHOU - {teste.__name__}: {e}")

    print(f"\n{len(testes) - falhas}/{len(testes)} testes passaram.")
    if falhas:
        sys.exit(1)
