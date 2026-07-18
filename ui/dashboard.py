# ==========================================================
# Arquivo: ui/dashboard.py
# Responsabilidade: Tela inicial — resumo de saúde do sistema
# e atalhos rápidos. É a primeira coisa que o usuário vê ao
# abrir o aplicativo, antes de escolher uma categoria.
# ==========================================================

from tkinter import ttk

from utils.constants import COR_OK, COR_AVISO
from ui.widgets import criar_cabecalho_secao, criar_card_estatistica


class Dashboard(ttk.Frame):
    def __init__(self, parent, app):
        """app: referência ao ManutencaoApp, usada para disparar ações
        (ex.: ir para uma categoria, consultar espaço em disco)."""
        super().__init__(parent)
        self.app = app
        self.cards_status = {}
        self._montar()

    def _montar(self):
        criar_cabecalho_secao(
            self, "\U0001F3E0", "Dashboard",
            "Resumo rápido do sistema — escolha uma categoria ao lado para agir",
        )

        grade = ttk.Frame(self)
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
        criar_cabecalho_secao(self, "\u26A1", "Ações rápidas")

        acoes = ttk.Frame(self)
        acoes.pack(fill="x")
        ttk.Button(acoes, text="\U0001F6E0  Ir para Manutenção", style="Secundario.TButton",
                   command=lambda: self.app.navegar_para("manutencao")).pack(side="left")
        ttk.Button(acoes, text="\U0001F9F9  Ir para Limpeza", style="Secundario.TButton",
                   command=lambda: self.app.navegar_para("limpeza")).pack(side="left", padx=8)
        ttk.Button(acoes, text="\U0001F4CA  Ver espaço em disco", style="Secundario.TButton",
                   command=self.app.ver_espaco_disco).pack(side="left")

    # -------------------- Atualização dos indicadores --------------------
    def atualizar_disco(self, tipo: str):
        self.cards_status["disco"].definir_valor(tipo)

    def atualizar_espaco(self, texto: str, cor=None):
        self.cards_status["espaco"].definir_valor(texto, cor=cor)

    def atualizar_ultima_execucao(self, texto: str):
        self.cards_status["ultima"].definir_valor(texto)

    def atualizar_status_geral(self, texto: str, cor=None):
        self.cards_status["status"].definir_valor(texto, cor=(cor or COR_OK))