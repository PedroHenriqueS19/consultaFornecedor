import argparse
import os

from logger_setup import log
from config import CHECKPOINT_DIR

CHECKPOINT_PATH = os.path.join(CHECKPOINT_DIR, "etapa1.parquet")

def executar_pipeline(cnaes_alvo_dict: dict, municipios_alvo_lista: list[str], configuracoes: dict):
    print("\n⏳ Iniciando automação de prospecção B2B...")
    
    if configuracoes.get("forcar_novo_download") and os.path.exists(CHECKPOINT_PATH):
        os.remove(CHECKPOINT_PATH)
        log.info("Checkpoint da Etapa 1 removido.")

    if configuracoes.get("baixar_bases"):
        print("🌐 Conectando à nuvem da Receita Federal (Pode demorar se for o primeiro download do mês)...")
    
    print("🔎 Lendo arquivos e filtrando empresas pelos CNAEs solicitados...")
    print("   (Isso costuma levar alguns minutos, não feche o aplicativo. Vá tomar um café ☕)")

    from etapa1_rfb import rodar_etapa1
    df = rodar_etapa1(
        cnaes_alvo=cnaes_alvo_dict, 
        municipios_alvo=municipios_alvo_lista,
        usar_checkpoint=not configuracoes.get("forcar_novo_download"),
        apenas_ativas=not configuracoes.get("sem_filtro_ativa"),
        fazer_download=configuracoes.get("baixar_bases")
    )

    if df.empty:
        print("\n⚠️ Nenhuma empresa encontrada com os filtros definidos. Tente outros CNAEs.")
        return

    print(f"✅ Busca concluída! {len(df)} empresas encontradas.")
    print("⚙️ Processando dados de qualidade e formatando...")

    if not configuracoes.get("pular_simples"):
        from etapa1b_simples_nacional import rodar_etapa1b
        df = rodar_etapa1b(df, fazer_download=configuracoes.get("baixar_bases"))

    if not configuracoes.get("pular_mec"):
        from etapa2_emec_sistec import enriquecer_dataframe
        df = enriquecer_dataframe(df, usar_fallback_web=configuracoes.get("fallback_web"))

    from etapa2b_qualidade import rodar_etapa2b
    df = rodar_etapa2b(df, geolocalizar=configuracoes.get("geolocalizar"))

    from etapa3_export import rodar_etapa3
    print("\n💾 Gerando planilha do Excel...")
    caminho_csv, caminho_xlsx = rodar_etapa3(df, cnaes_alvo_dict)

    # Converte o caminho relativo em um caminho absoluto para o usuário saber exatamente onde está
    caminho_absoluto = os.path.abspath(caminho_xlsx)

    print("\n🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
    print("="*65)
    print(f"📂 SUA PLANILHA ESTÁ SALVA NESTA PASTA:")
    print(f"👉 {caminho_absoluto}")
    print("="*65)