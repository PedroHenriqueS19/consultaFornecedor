"""
Entrypoint do disparo diário automático — chamado pelo Agendador de
Tarefas do Windows, sem interface gráfica.

Roda de segunda a sábado (pula domingo por padrão) e envia o próximo
lote da campanha ativa, respeitando LIMITE_ENVIOS_POR_DIA.
"""

from datetime import datetime

import pandas as pd

from agendamento import carregar_campanha_ativa, calcular_progresso
from etapa4_supressao import aplicar_supressao
from etapa5_envio import rodar_etapa5
from logger_setup import log

DOMINGO = 6  # datetime.weekday(): segunda=0 ... domingo=6


def main():
    if datetime.now().weekday() == DOMINGO:
        print("Hoje é domingo — disparo automático pausado (padrão: segunda a sábado).")
        log.info("Disparo diário pulado: hoje é domingo.")
        return

    campanha = carregar_campanha_ativa()
    if not campanha:
        print("Nenhuma campanha ativa. Ative pela interface (aba Disparo de Campanha) antes de agendar.")
        log.warning("Disparo diário chamado sem campanha ativa configurada.")
        return

    try:
        df = pd.read_excel(campanha["caminho_planilha"], sheet_name="Leads B2B")
    except Exception as e:
        print(f"[ERRO] Não foi possível abrir a planilha da campanha: {e}")
        log.error(f"Falha ao abrir planilha da campanha ativa: {e}")
        return

    df = df.dropna(subset=["email"])
    df = df[df["email_confiavel"] == True]
    df = aplicar_supressao(df)

    progresso = calcular_progresso(df)
    print(f"📊 Progresso da campanha: {progresso['enviados']}/{progresso['total_elegivel']} já enviados. "
          f"Restam {progresso['restantes']} — estimativa de {progresso['dias_restantes_estimado']} dia(s) útil(eis).")
    log.info(f"Progresso: {progresso}")

    if progresso["restantes"] == 0:
        print("✅ Campanha concluída — todos os e-mails elegíveis já foram enviados.")
        log.info("Campanha concluída. Nenhum envio necessário hoje.")
        return

    rodar_etapa5(df, campanha["assunto"], campanha["corpo"])


if __name__ == "__main__":
    main()