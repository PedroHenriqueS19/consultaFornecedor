import sys
import threading
import webbrowser
import customtkinter as ctk
from main import executar_pipeline

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class RedirecionadorConsole:
    """
    Redireciona print()/stderr para uma ou mais caixas de texto da interface.
    Aceita múltiplos widgets porque agora temos duas telas de log
    (Extração e Campanha) e ambas devem exibir o que está acontecendo.
    """
    def __init__(self, *widgets_texto):
        self.widgets_texto = widgets_texto

    def write(self, texto):
        for widget in self.widgets_texto:
            widget.after(0, self._inserir_texto, widget, texto)

    def _inserir_texto(self, widget, texto):
        widget.configure(state="normal")
        widget.insert("end", texto)
        widget.see("end")
        widget.configure(state="disabled")

    def flush(self):
        pass


class AppProspeccao(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Extrator B2B - Receita Federal")
        self.geometry("800x750")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # A área das abas vai expandir
        self.grid_rowconfigure(2, weight=0)  # O footer fica fixo no fundo

        # --- Título Global ---
        self.label_titulo = ctk.CTkLabel(self, text="Gerador de Leads B2B", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_titulo.grid(row=0, column=0, padx=20, pady=(20, 10))

        # --- Sistema de Abas (Tabview) ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        self.tab_extrator = self.tabview.add("Extrator de Dados")
        self.tab_campanha = self.tabview.add("Disparo de Campanha")
        self.tab_guia = self.tabview.add("Guia e Boas Práticas")

        self.tab_extrator.grid_columnconfigure(0, weight=1)
        self.tab_campanha.grid_columnconfigure(0, weight=1)
        self.tab_guia.grid_columnconfigure(0, weight=1)
        self.tab_guia.grid_rowconfigure(0, weight=1)

        self.construir_aba_extrator()
        self.construir_aba_campanha()
        self.construir_aba_guia()
        self.construir_footer()

        # Redireciona prints/erros para as duas caixas de log (extração + campanha)
        sys.stdout = RedirecionadorConsole(self.textbox_log, self.textbox_log_campanha)
        sys.stderr = RedirecionadorConsole(self.textbox_log, self.textbox_log_campanha)

    # ----------------------------------------------------------------
    # ABA 1 — Extrator de Dados
    # ----------------------------------------------------------------
    def construir_aba_extrator(self):
        # --- Frame de Inputs ---
        self.frame_inputs = ctk.CTkFrame(self.tab_extrator)
        self.frame_inputs.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.frame_inputs.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_inputs, text="Municípios:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_mun = ctk.CTkEntry(self.frame_inputs, placeholder_text="Ex: SAO PAULO, SANTOS")
        self.entry_mun.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.entry_mun.insert(0, "SAO PAULO")

        ctk.CTkLabel(self.frame_inputs, text="CNAEs Alvo:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_cnae = ctk.CTkEntry(self.frame_inputs, placeholder_text="Ex: 8630501, 8650001")
        self.entry_cnae.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # --- Frame de Opções (Checkboxes) ---
        self.frame_opcoes = ctk.CTkFrame(self.tab_extrator)
        self.frame_opcoes.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.check_baixar = ctk.CTkCheckBox(self.frame_opcoes, text="1. Baixar/Atualizar bases da Receita (Lento)")
        self.check_baixar.grid(row=0, column=0, padx=15, pady=10)
        self.check_baixar.select()

        self.check_forcar = ctk.CTkCheckBox(self.frame_opcoes, text="2. Ignorar Checkpoint (Refazer Filtros)")
        self.check_forcar.grid(row=0, column=1, padx=15, pady=10)

        self.check_pular_mec = ctk.CTkCheckBox(self.frame_opcoes, text="Pular cruzamento MEC/SISTEC")
        self.check_pular_mec.grid(row=1, column=0, padx=15, pady=10)
        self.check_pular_mec.select()

        self.check_pular_simples = ctk.CTkCheckBox(self.frame_opcoes, text="Pular Simples Nacional")
        self.check_pular_simples.grid(row=1, column=1, padx=15, pady=10)

        # --- Botão Iniciar ---
        self.btn_iniciar = ctk.CTkButton(self.tab_extrator, text="▶ Iniciar Processamento", command=self.iniciar_extracao, height=40)
        self.btn_iniciar.grid(row=2, column=0, padx=10, pady=10)

        # --- Console Visual ---
        self.textbox_log = ctk.CTkTextbox(self.tab_extrator, height=220, state="disabled", font=ctk.CTkFont(family="Consolas", size=13))
        self.textbox_log.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

    def iniciar_extracao(self):
        municipios_raw = self.entry_mun.get()
        cnaes_raw = self.entry_cnae.get()

        if not municipios_raw or not cnaes_raw:
            print("[ERRO] Preencha os Municípios e os CNAEs antes de iniciar.\n")
            return

        self.btn_iniciar.configure(state="disabled", text="Processando (Acompanhe o Log)...")
        self.textbox_log.configure(state="normal")
        self.textbox_log.delete("1.0", "end")
        self.textbox_log.configure(state="disabled")

        threading.Thread(target=self.processamento_pesado, args=(municipios_raw, cnaes_raw), daemon=True).start()

    def processamento_pesado(self, municipios_raw, cnaes_raw):
        try:
            municipios_lista = [m.strip().upper() for m in municipios_raw.split(",") if m.strip()]
            cnaes_lista = [c.strip().replace("-", "").replace("/", "") for c in cnaes_raw.split(",") if c.strip()]
            cnaes_dict = {c: f"CNAE {c}" for c in cnaes_lista}

            configuracoes = {
                "baixar_bases": self.check_baixar.get() == 1,
                "forcar_novo_download": self.check_forcar.get() == 1,
                "pular_mec": self.check_pular_mec.get() == 1,
                "pular_simples": self.check_pular_simples.get() == 1,
                "geolocalizar": False,
                "sem_filtro_ativa": False,
                "fallback_web": False,
                "enviar_crm": False
            }

            executar_pipeline(cnaes_dict, municipios_lista, configuracoes)
        except Exception as e:
            print(f"\n[ERRO CRÍTICO]: {str(e)}")
        finally:
            self.btn_iniciar.after(0, lambda: self.btn_iniciar.configure(state="normal", text="▶ Iniciar Processamento"))

    # ----------------------------------------------------------------
    # ABA 2 — Disparo de Campanha
    # ----------------------------------------------------------------
    def construir_aba_campanha(self):
        frame = ctk.CTkFrame(self.tab_campanha)
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Planilha (.xlsx):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_planilha = ctk.CTkEntry(frame, placeholder_text="Ex: output/leads_cnae_XXX.xlsx")
        self.entry_planilha.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(frame, text="Assunto:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_assunto = ctk.CTkEntry(frame, placeholder_text="Ex: Uma solução para {{nome_empresa}}")
        self.entry_assunto.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.tab_campanha, text="Corpo (HTML):").grid(row=1, column=0, padx=10, pady=(0, 0), sticky="nw")
        self.textbox_corpo = ctk.CTkTextbox(self.tab_campanha, height=150)
        self.textbox_corpo.grid(row=2, column=0, padx=10, pady=(30, 10), sticky="ew")
        self.textbox_corpo.insert(
            "1.0",
            "<p>Olá,</p>\n<p>Somos a Sua Empresa e ajudamos negócios como o <strong>{{nome_empresa}}</strong> a...</p>\n<p>Podemos conversar 15 minutos essa semana?</p>"
        )

        frame_botoes = ctk.CTkFrame(self.tab_campanha, fg_color="transparent")
        frame_botoes.grid(row=3, column=0, padx=10, pady=10)

        self.btn_disparar_agora = ctk.CTkButton(
            frame_botoes, text="📧 Disparar Lote Agora", command=self.iniciar_campanha, height=40,
            fg_color="#a83232", hover_color="#832525"
        )
        self.btn_disparar_agora.grid(row=0, column=0, padx=5)

        self.btn_ativar_diario = ctk.CTkButton(
            frame_botoes, text="🔁 Ativar Disparo Diário Automático", command=self.ativar_disparo_diario, height=40,
            fg_color="#2f6b3a", hover_color="#245229"
        )
        self.btn_ativar_diario.grid(row=0, column=1, padx=5)

        self.label_progresso = ctk.CTkLabel(self.tab_campanha, text="", font=ctk.CTkFont(size=12))
        self.label_progresso.grid(row=4, column=0, padx=10, pady=(0, 10))

        self.textbox_log_campanha = ctk.CTkTextbox(self.tab_campanha, height=180, state="disabled", font=ctk.CTkFont(family="Consolas", size=13))
        self.textbox_log_campanha.grid(row=5, column=0, padx=10, pady=10, sticky="ew")

    def _ler_campos_campanha(self):
        caminho = self.entry_planilha.get().strip().strip('"').strip("'")
        assunto = self.entry_assunto.get().strip()
        corpo = self.textbox_corpo.get("1.0", "end").strip()
        return caminho, assunto, corpo

    def iniciar_campanha(self):
        caminho, assunto, corpo = self._ler_campos_campanha()

        if not caminho or not assunto or not corpo:
            print("[ERRO] Preencha planilha, assunto e corpo antes de disparar.\n")
            return

        resposta = ctk.CTkInputDialog(
            text=f"Confirma o disparo real de e-mails usando '{caminho}'?\nDigite SIM para confirmar.",
            title="Confirmação de disparo"
        ).get_input()

        if resposta != "SIM":
            print("[CANCELADO] Disparo não confirmado pelo usuário.\n")
            return

        self.btn_disparar_agora.configure(state="disabled", text="Disparando...")
        threading.Thread(target=self._executar_campanha, args=(caminho, assunto, corpo), daemon=True).start()

    def _executar_campanha(self, caminho, assunto, corpo):
        try:
            import pandas as pd
            from etapa4_supressao import aplicar_supressao
            from etapa5_envio import rodar_etapa5

            df = pd.read_excel(caminho, sheet_name="Leads B2B")
            df = df.dropna(subset=["email"])
            df = df[df["email_confiavel"] == True]
            df = aplicar_supressao(df)

            rodar_etapa5(df, assunto, corpo)
        except Exception as e:
            print(f"\n[ERRO CRÍTICO NA CAMPANHA]: {str(e)}")
        finally:
            self.btn_disparar_agora.after(0, lambda: self.btn_disparar_agora.configure(state="normal", text="📧 Disparar Lote Agora"))

    def ativar_disparo_diario(self):
        caminho, assunto, corpo = self._ler_campos_campanha()

        if not caminho or not assunto or not corpo:
            print("[ERRO] Preencha planilha, assunto e corpo antes de ativar o disparo diário.\n")
            return

        try:
            import pandas as pd
            from agendamento import salvar_campanha_ativa, calcular_progresso

            salvar_campanha_ativa(caminho, assunto, corpo)

            df = pd.read_excel(caminho, sheet_name="Leads B2B")
            df = df.dropna(subset=["email"])
            df = df[df["email_confiavel"] == True]
            progresso = calcular_progresso(df)

            self.label_progresso.configure(
                text=f"Campanha ativada: {progresso['total_elegivel']} e-mails elegíveis, "
                     f"~{progresso['dias_restantes_estimado']} dia(s) útil(eis) para concluir."
            )
            print(
                "[OK] Campanha ativada. Configure o Agendador de Tarefas do Windows para chamar "
                "o DisparoDiario.exe diariamente (seg-sáb) para que o envio automático funcione.\n"
            )
        except Exception as e:
            print(f"\n[ERRO AO ATIVAR CAMPANHA]: {str(e)}")

    # ----------------------------------------------------------------
    # ABA 3 — Guia e Boas Práticas
    # ----------------------------------------------------------------
    def construir_aba_guia(self):
        texto_guia = """Bem-vindo ao Gerador de Leads B2B! 🚀

Este software automatiza a extração de dados públicos da Receita Federal para gerar planilhas de prospecção hiper-segmentadas, e permite disparar campanhas de e-mail para os leads qualificados.

📋 PASSO A PASSO PARA O PRIMEIRO USO:

1. Inserindo Municípios:
   • Digite o nome exato do município sem acentos (Ex: SAO PAULO, CAMPINAS).
   • Para mais de um, separe por vírgula.

2. Inserindo CNAEs (Área de atuação):
   • Digite apenas os números do CNAE, sem traços ou pontos (Ex: 8630501).
   • Separe múltiplos CNAEs por vírgula.

3. Entendendo as Opções (Caixas de Seleção):
   • [Baixar/Atualizar bases]: DEVE estar marcado no seu primeiro acesso ou na virada do mês. O robô vai baixar gigabytes de dados da Receita Federal.
   • [Ignorar Checkpoint]: Marque sempre que você mudar o CNAE ou o Município. Se deixar desmarcado, o robô vai tentar reaproveitar os dados da busca anterior para ir mais rápido.
   • [Pular MEC/SISTEC]: Deixe marcado, a menos que você esteja buscando Faculdades ou Escolas Técnicas.

📧 ABA "DISPARO DE CAMPANHA":
   • [Disparar Lote Agora]: envia imediatamente o próximo lote (respeitando o limite diário) para a planilha informada.
   • [Ativar Disparo Diário Automático]: salva a campanha para que o processo agendado (DisparoDiario.exe, via Agendador de Tarefas do Windows) continue o envio sozinho, todo dia, de segunda a sábado, até a lista acabar.

💡 BOAS PRÁTICAS E AVISOS:
   • O primeiro download (da Receita Federal) exige espaço no disco e tempo, dependendo da sua internet.
   • Quando o painel preto disser "Filtrando empresas...", pode demorar alguns minutos. O aplicativo não travou, ele está lendo milhões de linhas. Vá tomar um café! ☕
   • NUNCA abra a planilha no Excel enquanto o robô estiver rodando. Se o arquivo estiver aberto, o robô não conseguirá salvar os dados novos e dará erro.
   • Antes de disparar uma campanha real, sempre teste com uma planilha contendo só o seu próprio e-mail.
"""
        caixa_texto_guia = ctk.CTkTextbox(self.tab_guia, font=ctk.CTkFont(size=14), wrap="word")
        caixa_texto_guia.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        caixa_texto_guia.insert("1.0", texto_guia)
        caixa_texto_guia.configure(state="disabled")

    # ----------------------------------------------------------------
    # Rodapé
    # ----------------------------------------------------------------
    def construir_footer(self):
        self.frame_footer = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_footer.grid(row=2, column=0, pady=(5, 15))

        self.label_dev = ctk.CTkLabel(
            self.frame_footer,
            text="Desenvolvido por Pedro Francabandiera — ",
            font=ctk.CTkFont(size=12)
        )
        self.label_dev.grid(row=0, column=0)

        self.label_link = ctk.CTkLabel(
            self.frame_footer,
            text="FRANCABANDIERA.DEV",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#3a7ebf",
            cursor="hand2"
        )
        self.label_link.grid(row=0, column=1)

        self.label_link.bind("<Button-1>", lambda e: webbrowser.open("https://francabandiera.dev"))


if __name__ == "__main__":
    app = AppProspeccao()
    app.mainloop()