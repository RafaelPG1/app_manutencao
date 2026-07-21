# ==========================================================
# Arquivo: ui/ferramentas_view.py
# Responsabilidade: Tela da categoria Ferramentas — central de
# acesso aos utilitários administrativos OFICIAIS do Windows
# (Gerenciador de Dispositivos, Serviços, Editor do Registro etc.),
# agrupados por área (Sistema, Diagnóstico, Configuração, Rede).
#
# Tela puramente de atalho: cada clique só ABRE a ferramenta nativa
# do Windows (ver core/ferramentas/utilitarios_windows.py) — nenhuma
# lógica de manutenção própria roda aqui, no mesmo espírito de
# ui/sistema_view.py e ui/historico_view.py (telas informativas/de
# atalho, sem checkbox nem execução em lote — não usam TaskView).
#
# Reaproveita o mesmo componente de card já usado em "Consultas
# rápidas" do Dashboard (ui/widgets.py: criar_card_consultas_rapidas)
# — cada grupo de ferramentas vira um card com uma lista de itens
# clicáveis, organizados em grade de 2 colunas, evitando uma lista
# longa de botões soltos (mesmo racional documentado em
# ui/dashboard.py). Nenhum widget novo foi criado para esta tela.
#
# A área de conteúdo usa rolagem (canvas + scrollbar) no mesmo
# padrão de ui/historico_view.py — outra tela informativa agrupada
# em cards, sem checkbox/execução em lote.
# ==========================================================

import tkinter as tk
from tkinter import ttk

from utils.constants import COR_BG
from ui.widgets import criar_cabecalho_secao, criar_card_consultas_rapidas
from core.ferramentas.utilitarios_windows import ferramentas_por_categoria

# Ícones por grupo — reaproveitam a mesma identidade visual já usada
# em outros pontos do app para os mesmos temas (ver utils/constants.py:
# CATEGORIAS e ui/dashboard.py: icones_categoria).
_ICONES_GRUPO = {
    "Sistema": "\U0001F5A5",
    "Diagnóstico": "\U0001FA7A",
    "Configuração": "\u2699",
    "Rede": "\U0001F310",
}


class FerramentasView(ttk.Frame):
    def __init__(self, parent, app):
        """app: referência ao ManutencaoApp — usada apenas para chamar
        app.abrir_ferramenta(chave), que delega a
        core/ferramentas/utilitarios_windows.py e mostra o resultado
        numa messagebox (mesmo padrão das demais ações instantâneas,
        ex.: app.restaurar_sistema)."""
        super().__init__(parent)
        self.app = app
        self._montar()

    def _montar(self):
        criar_cabecalho_secao(
            self, "\U0001F527", "Ferramentas",
            "Utilitários administrativos oficiais do Windows — cada item abre a ferramenta nativa em uma nova janela",
        )

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(canvas_frame, bg=COR_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        conteudo = ttk.Frame(canvas)

        janela_id = canvas.create_window((0, 0), window=conteudo, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _atualizar_scrollregion(_evento=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _ajustar_largura(evento):
            canvas.itemconfig(janela_id, width=evento.width)

        conteudo.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura)

        def _on_scroll(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_scroll))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        canvas.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        self._montar_grade(conteudo)

    def _montar_grade(self, parent):
        grupos = ferramentas_por_categoria()

        n_colunas = 2
        grade = ttk.Frame(parent)
        grade.pack(fill="x")
        for col in range(n_colunas):
            grade.columnconfigure(col, weight=1, uniform="ferramenta")

        for i, (titulo_grupo, ferramentas_grupo) in enumerate(grupos):
            linha, coluna = divmod(i, n_colunas)
            acoes = [
                {
                    "icone": f.icone,
                    "titulo": f.titulo,
                    "comando": lambda chave=f.chave: self.app.abrir_ferramenta(chave),
                }
                for f in ferramentas_grupo
            ]
            card = criar_card_consultas_rapidas(
                grade, _ICONES_GRUPO.get(titulo_grupo, "\U0001F527"), titulo_grupo, acoes,
            )
            card.grid(
                row=linha, column=coluna, sticky="nsew",
                padx=(0, 10) if coluna == 0 else (10, 0),
                pady=(0, 12),
            )