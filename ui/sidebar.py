# ==========================================================
# Arquivo: ui/sidebar.py
# Responsabilidade: Barra lateral de navegação por categorias.
# Fixa em largura e altura de tela — não cresce com a
# quantidade de funcionalidades, apenas o conteúdo de cada
# categoria cresce.
# ==========================================================

import tkinter as tk
from tkinter import ttk

from config import APP_TITULO
from utils.constants import (
    CATEGORIAS, COR_BG_ELEVADO, COR_BG_CARD_HOVER, COR_ACCENT_FRACO,
    COR_ACCENT, COR_TEXTO, COR_TEXTO_FRACO, COR_BORDA,
)

LARGURA_SIDEBAR = 220


def _bind_recursivo(widget, evento, callback):
    """Aplica o mesmo bind a um widget e a todos os seus descendentes —
    usado para que o card de execução inteiro (não só o texto) seja
    clicável e reaja ao hover."""
    widget.bind(evento, callback)
    for filho in widget.winfo_children():
        _bind_recursivo(filho, evento, callback)


class Sidebar(ttk.Frame):
    def __init__(self, parent, ao_selecionar):
        """ao_selecionar: callback(chave_categoria) chamado quando o
        usuário clica em um item da navegação."""
        super().__init__(parent, style="Sidebar.TFrame", width=LARGURA_SIDEBAR)
        self.pack_propagate(False)
        self.ao_selecionar = ao_selecionar
        self.botoes = {}
        self.categoria_ativa = None

        self._montar_cabecalho()
        self._montar_itens()
        self._montar_card_execucao()

    def _montar_cabecalho(self):
        topo = tk.Frame(self, bg=COR_BG_ELEVADO)
        topo.pack(fill="x", pady=(18, 10), padx=16)
        tk.Label(topo, text="\U0001F6E1", bg=COR_BG_ELEVADO, fg=COR_ACCENT,
                  font=("Segoe UI", 20)).pack(anchor="w")
        tk.Label(topo, text="Manutenção", bg=COR_BG_ELEVADO, fg=COR_TEXTO,
                  font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(6, 0))
        tk.Label(topo, text="do Sistema", bg=COR_BG_ELEVADO, fg=COR_TEXTO_FRACO,
                  font=("Segoe UI", 9)).pack(anchor="w")

        sep = tk.Frame(self, bg=COR_BORDA, height=1)
        sep.pack(fill="x", pady=(14, 8))

    def _montar_itens(self):
        container = tk.Frame(self, bg=COR_BG_ELEVADO)
        container.pack(fill="both", expand=True, padx=10)

        for chave, icone, titulo, _sub in CATEGORIAS:
            item = self._criar_item(container, chave, icone, titulo)
            item.pack(fill="x", pady=2)
            self.botoes[chave] = item

    # -------------------- Card fixo de execução em andamento --------------------
    def _montar_card_execucao(self):
        """Indicador global de execução: um pequeno card discreto, fixo
        na parte inferior da sidebar, visível em qualquer categoria
        enquanto existir uma execução em lote em andamento.

        É criado aqui mas só é "packado" (via mostrar_card_execucao) no
        momento em que uma execução começa — por padrão fica oculto e
        não ocupa nenhum espaço."""
        self._cor_card_base = COR_ACCENT_FRACO
        self.card_execucao = tk.Frame(
            self, bg=self._cor_card_base, cursor="hand2",
            highlightthickness=1, highlightbackground=COR_ACCENT,
        )

        inner = tk.Frame(self.card_execucao, bg=self._cor_card_base)
        inner.pack(fill="x", padx=12, pady=10)

        self.lbl_card_titulo = tk.Label(
            inner, text="\u2699  Execução em andamento", bg=self._cor_card_base,
            fg=COR_TEXTO, font=("Segoe UI", 9, "bold"), anchor="w", justify="left",
        )
        self.lbl_card_titulo.pack(fill="x", anchor="w")

        self.lbl_card_sub = tk.Label(
            inner, text="Clique para acompanhar", bg=self._cor_card_base,
            fg=COR_TEXTO_FRACO, font=("Segoe UI", 8), anchor="w", justify="left",
        )
        self.lbl_card_sub.pack(fill="x", anchor="w", pady=(2, 0))

        def clicar(_e=None):
            self.ao_selecionar("execucao")

        def hover_on(_e=None):
            self._pintar_card_execucao(COR_BG_CARD_HOVER)

        def hover_off(_e=None):
            self._pintar_card_execucao(self._cor_card_base)

        _bind_recursivo(self.card_execucao, "<Button-1>", clicar)
        _bind_recursivo(self.card_execucao, "<Enter>", hover_on)
        _bind_recursivo(self.card_execucao, "<Leave>", hover_off)

        self._card_execucao_visivel = False
        # Não chama pack() aqui — o card só aparece via mostrar_card_execucao().

    def _pintar_card_execucao(self, cor):
        self.card_execucao.configure(bg=cor)
        for filho in self.card_execucao.winfo_children():
            filho.configure(bg=cor)
            for neto in filho.winfo_children():
                neto.configure(bg=cor)

    def mostrar_card_execucao(self, titulo="Execução em andamento", subtitulo="Clique para acompanhar"):
        """Exibe (ou atualiza o texto de) o card fixo de execução."""
        self.lbl_card_titulo.config(text=f"\u2699  {titulo}")
        self.lbl_card_sub.config(text=subtitulo)
        if not self._card_execucao_visivel:
            self.card_execucao.pack(side="bottom", fill="x", padx=12, pady=(0, 16))
            self._card_execucao_visivel = True

    def ocultar_card_execucao(self):
        """Remove o card por completo — a sidebar volta ao layout normal,
        sem deixar espaço vazio reservado."""
        if self._card_execucao_visivel:
            self.card_execucao.pack_forget()
            self._card_execucao_visivel = False

    def _criar_item(self, parent, chave, icone, titulo):
        item = tk.Frame(parent, bg=COR_BG_ELEVADO, cursor="hand2")
        lbl = tk.Label(item, text=f"  {icone}   {titulo}", bg=COR_BG_ELEVADO,
                        fg=COR_TEXTO_FRACO, font=("Segoe UI", 10), anchor="w")
        lbl.pack(fill="x", ipady=8, padx=4)

        def clicar(_e=None):
            self.ao_selecionar(chave)

        def hover_on(_e=None):
            if self.categoria_ativa != chave:
                item.configure(bg=COR_BG_CARD_HOVER)
                lbl.configure(bg=COR_BG_CARD_HOVER)

        def hover_off(_e=None):
            self._repintar_item(chave)

        for w in (item, lbl):
            w.bind("<Button-1>", clicar)
            w.bind("<Enter>", hover_on)
            w.bind("<Leave>", hover_off)

        item.label = lbl
        return item

    def _repintar_item(self, chave):
        item = self.botoes[chave]
        ativo = (chave == self.categoria_ativa)
        cor_fundo = COR_ACCENT_FRACO if ativo else COR_BG_ELEVADO
        cor_texto = COR_ACCENT if ativo else COR_TEXTO_FRACO
        item.configure(bg=cor_fundo)
        item.label.configure(bg=cor_fundo, fg=cor_texto,
                              font=("Segoe UI", 10, "bold" if ativo else "normal"))

    def definir_ativo(self, chave):
        anterior = self.categoria_ativa
        self.categoria_ativa = chave
        if anterior:
            self._repintar_item(anterior)
        self._repintar_item(chave)