# Prospecção B2B — Setor Educacional (CNPJ + e-MEC/SISTEC)

Automação que baixa dados públicos da Receita Federal, filtra empresas do
ramo educacional pelos CNAEs abaixo, enriquece com Simples Nacional,
e-MEC/SISTEC, validação de e-mail e score de qualidade, e exporta uma
planilha pronta para prospecção — com histórico mensal e detecção de leads
novos.

| CNAE | Descrição |
|---|---|
| 8531-7/00 | Educação superior — graduação |
| 8532-5/00 | Educação superior — pós-graduação e extensão |
| 8541-4/00 | Educação profissional de nível técnico |
| 8542-2/00 | Educação profissional de nível tecnológico |

## Como rodar

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

O resultado sai em `output/empresas_educacao_sp.csv` e `.xlsx` (3 abas:
**Metadados**, **Leads Educação** e **Novidades do mês**, quando houver
snapshot anterior para comparar).

### Flags disponíveis

| Flag | O que faz |
|---|---|
| `--pular-mec` | Pula o cruzamento com e-MEC/SISTEC (etapa 2) |
| `--pular-simples` | Pula o cruzamento com o Simples Nacional (etapa 1b) |
| `--geolocalizar` | Ativa a validação/geolocalização de endereço via CEP (mais lento) |
| `--fallback-web` | Tenta achar o site institucional via busca externa quando não há match no MEC |
| `--sem-filtro-ativa` | Inclui empresas inativas/baixadas também |
| `--forcar-novo-download` | Ignora o checkpoint da etapa 1 e reprocessa a base da RFB do zero |
| `--enviar-crm` | Envia os leads com melhor score ao CRM configurado (etapa 4) |

Exemplo de execução rápida, só reaproveitando o que já foi processado:
```bash
python main.py --pular-mec --pular-simples
```

## Pipeline completo

```
Etapa 1  (etapa1_rfb.py)              RFB: download resumível + filtro por
                                       município(s) e CNAE + checkpoint Parquet
Etapa 1b (etapa1b_simples_nacional.py) Simples Nacional: porte real (MEI/ME/EPP)
Etapa 2  (etapa2_emec_sistec.py)      e-MEC / SISTEC, com cache local em SQLite
Etapa 2b (etapa2b_qualidade.py)       E-mail confiável, geolocalização, score do lead
Etapa 3  (etapa3_export.py)           CSV + XLSX (metadados, novidades do mês)
Etapa 4  (crm_integration.py)         Envio opcional ao CRM (leads de melhor score)
```

## Melhorias implementadas nesta versão

**Robustez de engenharia**
- **Download resumível** (`download_utils.py`): se a conexão cair no meio
  de um zip de vários GB, a próxima execução retoma do byte onde parou em
  vez de baixar tudo de novo (HTTP Range requests).
- **Checkpoint em Parquet** entre a Etapa 1 e as seguintes
  (`checkpoints/etapa1.parquet`): se o cruzamento com o MEC falhar no
  meio, não é preciso reprocessar a base inteira da Receita de novo. Use
  `--forcar-novo-download` para invalidar o checkpoint manualmente.
- **Logging estruturado** (`logger_setup.py`): todo `print()` solto virou
  `logging`, com arquivo em `logs/execucao_AAAAMMDD_HHMM.log` — essencial
  em processos que rodam por horas sem supervisão.
- **Testes automatizados** (`tests/test_matching.py`): valida o limiar de
  fuzzy matching com casos conhecidos (nome completo vs. sigla, etc.) e a
  heurística de e-mail confiável. Rodar com `python -m pytest tests/ -v`
  ou `python tests/test_matching.py`.

**Qualidade e enriquecimento do dado**
- **Múltiplos municípios** (`config.MUNICIPIOS_ALVO_NOMES`): aceita lista
  (ex: Grande São Paulo), não só a capital.
- **Matriz vs. filial**: coluna `eh_matriz` sinaliza duplicidade de grupo
  econômico, para não prospectar a mesma empresa várias vezes.
- **Porte real via Simples Nacional** (`etapa1b_simples_nacional.py`):
  cruza com o arquivo `Simples.zip` da RFB para saber se é MEI, ME/EPP ou
  demais — mais confiável que o campo cadastral simples.
- **Validação heurística de e-mail** (`etapa2b_qualidade.py`): sinaliza
  `email_confiavel=False` para domínios genéricos (gmail, hotmail...) ou
  de terceiros (contabilidade, assessoria jurídica), que raramente são o
  contato certo da empresa.
- **Geolocalização por CEP** (opcional, `--geolocalizar`): valida/completa
  o endereço via ViaCEP. Para lat/long de verdade, encadeie com um serviço
  de geocoding (Nominatim/OSM ou Google Geocoding) — ponto de extensão
  documentado no próprio módulo.
- **Cache local em SQLite** (`cache_mec.sqlite3`): cada nome já buscado no
  e-MEC/SISTEC fica salvo com timestamp; reexecuções dentro de
  `CACHE_VALIDADE_DIAS` (padrão 30 dias) não batem no MEC de novo — reduz
  drasticamente o tempo de execução mensal.
- **Fallback de busca externa** (`--fallback-web`): quando não há match no
  e-MEC/SISTEC, tenta achar o site institucional por busca — esqueleto
  pronto para plugar num provedor pago (Bing Search API, SerpAPI, Google
  Custom Search), já que scraping direto de páginas de busca viola termos
  de uso da maioria dos provedores.

**Prospecção**
- **Score de qualidade do lead** (0–100, coluna `score_lead`): combina
  e-mail confiável, telefone presente, confirmação no e-MEC/SISTEC, se é
  matriz e porte — a planilha final já sai ordenada do lead mais "pronto
  para contato" para o menos.
- **Aba de metadados no XLSX**: data de extração, município(s), total de
  registros, score médio, quantos e-mails são confiáveis, quantos foram
  confirmados no MEC, e a contagem por CNAE — dá rastreabilidade à lista.
- **Diff mensal / "Novidades do mês"**: cada execução salva um snapshot em
  `output/historico/snapshot_AAAA-MM.parquet`; a exportação seguinte
  compara com o snapshot do mês anterior e gera uma aba só com CNPJs que
  não existiam antes — leads recém-abertos, ainda não assediados pela
  concorrência.
- **Integração com CRM** (`crm_integration.py`, opcional): se
  `CRM_PROVEDOR` e `CRM_API_KEY` estiverem definidos como variável de
  ambiente, `--enviar-crm` envia os leads com `score_lead` acima do
  limiar (`CRM_SCORE_MINIMO_PARA_ENVIO`, padrão 50). Implementado de
  verdade para HubSpot (Companies API); Pipedrive e RD Station têm o
  esqueleto pronto para completar seguindo o mesmo padrão.

**Escala e agendamento**
- **GitHub Actions** (`.github/workflows/prospeccao_mensal.yml`): roda o
  pipeline todo dia 5 do mês automaticamente e publica o XLSX como
  artifact do job. Leia os comentários do arquivo antes de ativar — os
  arquivos da RFB são grandes e podem exigir um runner com mais disco que
  o gratuito, dependendo do recorte de municípios.

## ⚠️ Leia antes de usar — limitações importantes

**Etapa 1 e 1b (Receita Federal / Simples Nacional) — totalmente
automatizadas e confiáveis.** Usam dado aberto oficial em lote, atualizado
mensalmente. A primeira execução pode demorar e ocupar vários GB em disco,
pois a Receita não permite baixar só um município — é preciso baixar a
base nacional inteira e filtrar localmente.

**Etapa 2 (e-MEC / SISTEC) — melhor esforço, requer ajuste manual.**
Diferente da Receita, **e-MEC e SISTEC não têm dado aberto em lote** — só
telas de consulta feitas para navegador. `etapa2_emec_sistec.py` contém o
esqueleto completo da integração (cache, matching por similaridade,
tratamento de erro), mas os endpoints reais de busca **precisam ser
mapeados por você** antes do primeiro uso real:

1. Abra https://emec.mec.gov.br/ no navegador, aperte F12 → aba "Network".
2. Faça uma busca por instituição e veja qual URL/payload a página chama
   por trás dos panos (normalmente uma API JSON interna).
3. Copie esse endpoint para dentro de `buscar_emec()`.
4. Repita o processo para https://sistec.mec.gov.br/consultapublicaunidadeensino
   e preencha `buscar_sistec()`.

Isso é necessário porque esses sites são aplicações dinâmicas cujos
endpoints não são documentados publicamente e podem mudar sem aviso — um
script genérico sem esse ajuste pararia de funcionar na primeira mudança
de layout do MEC.

**Alternativa mais estável para graduação/pós:** os microdados do **Censo
da Educação Superior (INEP)** são dado aberto oficial em lote e cobrem
8531-7 e 8532-5 de forma confiável — porém não trazem telefone/e-mail de
contato, só confirmam quais CNPJs são IES credenciadas.
https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/censo-da-educacao-superior

**Etapa 4 (CRM) — implementada de verdade só para HubSpot.** Pipedrive e
RD Station têm o roteamento pronto, mas a chamada HTTP em si precisa ser
escrita seguindo a documentação de cada provedor (links nos comentários de
`crm_integration.py`).

## LGPD

CNPJ, razão social e contatos institucionais (e-mail/telefone da empresa,
não de pessoa física) são dados públicos e o uso para prospecção B2B é
permitido sob a base legal de legítimo interesse — mas:
- Use preferencialmente e-mails institucionais, não pessoais (a validação
  heurística da Etapa 2b já ajuda a identificar isso).
- Ofereça opt-out claro em qualquer contato comercial.
- Respeite `PAUSA_ENTRE_REQUISICOES_SEGUNDOS` ao consultar o MEC — não
  sobrecarregue os servidores públicos.

## Estrutura do projeto

```
config.py                        # constantes (CNAEs, municípios, limiares, CRM)
logger_setup.py                  # logging estruturado (console + arquivo)
download_utils.py                # download resumível (Range requests)
etapa1_rfb.py                    # RFB: download + filtro + checkpoint Parquet
etapa1b_simples_nacional.py      # porte real via Simples Nacional
etapa2_emec_sistec.py            # cruzamento e-MEC/SISTEC + cache SQLite
etapa2b_qualidade.py             # e-mail confiável, geolocalização, score
etapa3_export.py                 # CSV/XLSX, metadados, diff mensal
crm_integration.py                # envio opcional a CRM (HubSpot pronto)
main.py                          # orquestrador (flags de execução)
requirements.txt
tests/
  test_matching.py               # testes de fuzzy matching e validação de e-mail
.github/workflows/
  prospeccao_mensal.yml          # agendamento mensal via GitHub Actions
raw/                              # zips baixados da RFB (gerado em runtime)
extracted/                       # csvs extraídos (gerado em runtime)
checkpoints/                     # etapa1.parquet (gerado em runtime)
output/
  historico/                     # snapshots mensais (gerado em runtime)
logs/                             # logs de execução (gerado em runtime)
cache_mec.sqlite3                # cache de buscas no MEC (gerado em runtime)
```

## Próximos passos sugeridos (ainda não implementados)

- Migrar o cache/checkpoint de arquivo local para um banco compartilhado
  (Postgres/SQLite em disco de rede) se o pipeline rodar em múltiplas
  máquinas ou runners efêmeros do CI.
- Completar `_enviar_pipedrive` e `_enviar_rdstation` em
  `crm_integration.py` seguindo o mesmo padrão do HubSpot.
- Mapear os endpoints reais do e-MEC e SISTEC (passo manual descrito
  acima) para que a Etapa 2 pare de retornar vazio por padrão.
