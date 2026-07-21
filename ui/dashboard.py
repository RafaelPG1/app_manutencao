# ==========================================================
# Arquivo: ui/dashboard.py
# Responsabilidade: Tela inicial — resumo de saúde do sistema
# e atalhos rápidos. É a primeira coisa que o usuário vê ao
# abrir o aplicativo, antes de escolher uma categoria.
# ==========================================================

import tkinter as tk
from tkinter import ttk

from utils.constants import COR_BG, COR_BG_CARD, COR_BORDA, COR_TEXTO_FRACO, COR_OK, COR_AVISO
from ui.widgets import criar_cabecalho_secao, criar_card_estatistica, criar_card_consultas_rapidas

# Controla se o estilo discreto da scrollbar do Dashboard já foi
# registrado neste processo — mesmo racional de
# ui/task_view.py:_garantir_estilo_scroll (nome de estilo próprio,
# registrado uma única vez, sem sobrescrever o "TScrollbar" padrão
# nem o estilo já usado pela lista de tarefas).
_ESTILO_SCROLL_CONFIGURADO = False


def _garantir_estilo_scroll():
    global _ESTILO_SCROLL_CONFIGURADO
    if _ESTILO_SCROLL_CONFIGURADO:
        return
    try:
        style = ttk.Style()
        style.configure(
            "Dashboard.Vertical.TScrollbar",
            background=COR_BG_CARD,
            troughcolor=COR_BG,
            bordercolor=COR_BG,
            arrowcolor=COR_TEXTO_FRACO,
            relief="flat",
            borderwidth=0,
            width=10,
        )
        style.map(
            "Dashboard.Vertical.TScrollbar",
            background=[("active", COR_BORDA), ("!active", COR_BG_CARD)],
        )
    except Exception:
        # Em temas/plataformas que não aceitem alguma dessas opções,
        # mantém a scrollbar nativa padrão em vez de quebrar a tela.
        pass
    _ESTILO_SCROLL_CONFIGURADO = True


class Dashboard(ttk.Frame):
    def __init__(self, parent, app):
        """app: referência ao ManutencaoApp, usada para disparar ações
        (ex.: ir para uma categoria, consultar espaço em disco)."""
        super().__init__(parent)
        self.app = app
        self.cards_status = {}
        self._scrollbar_visivel = False
        self._montar()

    # -------------------- Área de scroll --------------------
    def _montar(self):
        """Monta o Dashboard dentro de uma área rolável — mesmo padrão
        de ui/task_view.py (canvas + scrollbar discreta que só aparece
        quando o conteúdo realmente não cabe na altura visível) e de
        ui/historico_view.py. O cabeçalho da janela (barra superior em
        ui/main_window.py) fica fora desta área e não é afetado."""
        _garantir_estilo_scroll()

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, bg=COR_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=canvas.yview,
            style="Dashboard.Vertical.TScrollbar",
        )
        conteudo = ttk.Frame(canvas)

        janela_id = canvas.create_window((0, 0), window=conteudo, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        # A scrollbar só é "packada" quando o conteúdo não cabe — ver
        # _atualizar_necessidade_scroll. Por padrão começa oculta.

        def _atualizar_necessidade_scroll():
            if not canvas.winfo_exists():
                return
            altura_conteudo = conteudo.winfo_reqheight()
            altura_visivel = canvas.winfo_height()
            precisa_scroll = altura_conteudo > altura_visivel

            if precisa_scroll and not self._scrollbar_visivel:
                scrollbar.pack(side="right", fill="y")
                self._scrollbar_visivel = True
            elif not precisa_scroll and self._scrollbar_visivel:
                scrollbar.pack_forget()
                self._scrollbar_visivel = False

            if not precisa_scroll:
                canvas.yview_moveto(0)

        def _atualizar_scrollregion(_evento=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            _atualizar_necessidade_scroll()

        def _ajustar_largura_interna(evento):
            canvas.itemconfig(janela_id, width=evento.width)
            _atualizar_necessidade_scroll()

        conteudo.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura_interna)

        # Rolagem pelo mouse só ativa enquanto o cursor está sobre o
        # Dashboard, e só tem efeito quando a scrollbar está visível
        # (ou seja, quando há de fato o que rolar) — mesmo padrão de
        # ui/task_view.py.
        def _on_scroll(event):
            if canvas.winfo_exists() and self._scrollbar_visivel:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_scroll))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        canvas.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        self._montar_conteudo(conteudo)

        # Passe final: com todo o conteúdo já montado, garante que a
        # scrollregion e a necessidade (ou não) de scrollbar reflitam
        # o estado definitivo da tela.
        self.after_idle(_atualizar_scrollregion)

    # -------------------- Conteúdo do Dashboard --------------------
    def _montar_conteudo(self, conteudo):
        """Todo o layout já existente do Dashboard, inalterado — só
        passou a ser montado dentro da área rolável (`conteudo`) em
        vez de diretamente em `self`."""
        criar_cabecalho_secao(
            conteudo, "\U0001F3E0", "Dashboard",
            "Resumo rápido do sistema — escolha uma categoria ao lado para agir",
        )

        grade = ttk.Frame(conteudo)
        grade.pack(fill="x")
        for col in range(4):
            grade.columnconfigure(col, weight=1, uniform="stat")

        self.cards_status["disco"] = criar_card_estatistica(
            grade, "\U0001F4BE", "Tipo de disco", "Detectando...")
        self.cards_status["disco"].grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        self.cards_status["espaco"] = criar_card_estatistica(
            grade, "\U0001F4CA", "Espaço livre (C:)", "Consultando...")
        self.cards_status["espaco"].grid(row=0, column=1, sticky="nsew", padx=10, pady=(0, 10))

        self.cards_status["ultima"] = criar_card_estatistica(
            grade, "\U0001F550", "Última manutenção", "Nenhuma sessão registrada ainda")
        self.cards_status["ultima"].grid(row=0, column=2, sticky="nsew", padx=10, pady=(0, 10))

        self.cards_status["status"] = criar_card_estatistica(
            grade, "\u2705", "Status geral", "Pronto", cor_valor=COR_OK)
        self.cards_status["status"].grid(row=0, column=3, sticky="nsew", padx=(10, 0), pady=(0, 10))

        # ---------- Ações rápidas ----------
        criar_cabecalho_secao(conteudo, "\u26A1", "Ações rápidas")

        acoes = ttk.Frame(conteudo)
        acoes.pack(fill="x")
        ttk.Button(acoes, text="\U0001F6E0  Ir para Manutenção", style="Secundario.TButton",
                   command=lambda: self.app.navegar_para("manutencao")).pack(side="left")
        ttk.Button(acoes, text="\U0001F9F9  Ir para Limpeza", style="Secundario.TButton",
                   command=lambda: self.app.navegar_para("limpeza")).pack(side="left", padx=8)
        ttk.Button(acoes, text="\U0001F4CA  Ver espaço em disco", style="Secundario.TButton",
                   command=self.app.ver_espaco_disco).pack(side="left")

        # ---------- Consultas rápidas ----------
        # Centraliza aqui as consultas/ações instantâneas que antes
        # ficavam espalhadas dentro de cada categoria (Manutenção,
        # Limpeza, Diagnóstico, Recuperação) — ver
        # app.consultas_rapidas_para_dashboard(). O resultado de cada
        # uma continua sendo exibido na hora (messagebox ou janela de
        # resultado), exatamente como antes; só o local do botão mudou.
        grupos = self.app.consultas_rapidas_para_dashboard()
        if grupos:
            # Separador entre "Ações rápidas" e "Consultas rápidas" — mesmo
            # padrão visual (cor e espessura) da linha usada dentro de
            # criar_cabecalho_secao, aqui reforçando a fronteira entre as
            # duas seções em vez da fronteira entre título e conteúdo.
            sep_secoes = tk.Frame(conteudo, bg=COR_BORDA, height=1)
            sep_secoes.pack(fill="x", pady=(20, 24))

            criar_cabecalho_secao(
                conteudo, "\U0001F50D", "Consultas rápidas",
                "Resultado exibido na hora — sem precisar entrar em cada categoria",
            )

            # Ícones por categoria de origem — mesma identidade visual usada
            # nos atalhos de "Ações rápidas" logo acima (\U0001F6E0 Manutenção,
            # \U0001F9F9 Limpeza), estendida às demais categorias que também
            # têm consultas instantâneas.
            icones_categoria = {
                "Manutenção": "\U0001F6E0",
                "Limpeza": "\U0001F9F9",
                "Diagnóstico": "\U0001FA7A",
                "Recuperação": "\U0001F9F0",
            }

            n_colunas = 2
            grade_consultas = ttk.Frame(conteudo)
            grade_consultas.pack(fill="x")
            for col in range(n_colunas):
                grade_consultas.columnconfigure(col, weight=1, uniform="consulta")

            for i, (titulo_categoria, acoes_categoria) in enumerate(grupos):
                linha, coluna = divmod(i, n_colunas)
                card = criar_card_consultas_rapidas(
                    grade_consultas,
                    icones_categoria.get(titulo_categoria, "\U0001F50D"),
                    titulo_categoria,
                    acoes_categoria,
                )
                card.grid(
                    row=linha, column=coluna, sticky="nsew",
                    padx=(0, 10) if coluna == 0 else (10, 0),
                    pady=(0, 12),
                )

    # -------------------- Atualização dos indicadores --------------------
    def atualizar_disco(self, tipo: str):
        self.cards_status["disco"].definir_valor(tipo)

    def atualizar_espaco(self, texto: str, cor=None):
        self.cards_status["espaco"].definir_valor(texto, cor=cor)

    def atualizar_ultima_execucao(self, texto: str):
        self.cards_status["ultima"].definir_valor(texto)

    def atualizar_status_geral(self, texto: str, cor=None):
        self.cards_status["status"].definir_valor(texto, cor=(cor or COR_OK))