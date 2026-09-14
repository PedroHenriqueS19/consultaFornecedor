# criar_planilha_teste.py — rodar uma vez, só para gerar o teste
import pandas as pd

dados_teste = {
    "score_lead": [100],
    "cnpj": ["00000000000000"],
    "razao_social": ["Empresa Teste LTDA"],
    "nome_fantasia": ["Teste"],
    "porte_empresa": ["ME"],
    "porte_real": ["ME"],
    "eh_matriz": [True],
    "cnae_fiscal_principal": ["8531700"],
    "cnae_descricao": ["Educação superior"],
    "situacao_cadastral": ["02"],
    "data_abertura": ["01/01/2020"],
    "ddd1": ["11"], "telefone1": ["999999999"], "ddd2": [None], "telefone2": [None],
    "telefone_celular": ["(11) 99999-9999"], "possui_celular": [True],
    "email": ["gabriel.macedo@anhangueraempresas.com.br"],   # <-- TROQUE AQUI
    "email_confiavel": [True], "email_confiavel_motivo": ["teste"],
    "logradouro": [""], "numero": [""], "bairro": [""], "municipio_nome": ["SAO PAULO"],
    "uf": ["SP"], "cep": [""],
    "fonte": [""], "nome_encontrado": [""], "score_similaridade": [None],
    "site_institucional": [""], "situacao_mec": [""],
}

df = pd.DataFrame(dados_teste)
with pd.ExcelWriter("output/teste_campanha.xlsx", engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="Leads B2B", index=False)

print("Planilha de teste criada em output/teste_campanha.xlsx")