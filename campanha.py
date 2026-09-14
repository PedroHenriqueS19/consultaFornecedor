"""
Entrypoint MANUAL para disparo de campanha. Roda separado da extração:

    python campanha.py caminho/para/leads_cnae_XXX.xlsx
"""

import sys
import pandas as pd

from etapa4_supressao import aplicar_supressao
from etapa5_envio import rodar_etapa5

ASSUNTO = "Uma solução para {{nome_empresa}}"
CORPO_TEMPLATE = """
<p>Olá,</p>
<p>Somos a Sua Empresa e ajudamos negócios como o <strong>{{nome_empresa}}</strong> a...</p>
<p>Podemos conversar 15 minutos essa semana?</p>
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python campanha.py caminho/para/planilha.xlsx")
        sys.exit(1)

    caminho_xlsx = sys.argv[1]
    df = pd.read_excel(caminho_xlsx, sheet_name="Leads B2B")

    df = df.dropna(subset=["email"])
    df = df[df["email_confiavel"] == True]  # só e-mails institucionais confiáveis
    df = aplicar_supressao(df)

    rodar_etapa5(df, ASSUNTO, CORPO_TEMPLATE)