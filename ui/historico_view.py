# ==========================================================
# Arquivo: ui/historico_view.py
# Responsabilidade: Tela da categoria Histórico — lista as execuções
# em lote anteriores (data, tarefas, resultado e duração de cada
# uma), lidas do MESMO log já usado pelo resto do aplicativo (ver
# utils/logger.py: ler_historico). Tela puramente informativa, sem
# checkbox nem execução em lote — não usa TaskView, no mesmo espírito
# de ui/sistema_view.py e ui/dashboard.py.
#
# A leitura do log é rápida (arquivo de texto local) e acontece de
# forma síncrona ao montar a tela, sem necessidade de thread — mesma
# escolha já usada pela ação instantânea "Ver espaço em disco".
# ==========================================================

import tkinter as tk
from tkinter import ttk

from utils.constants import (
    COR_BG, COR_BG_CARD, COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO, COR_OK, COR_ERRO,
)
from utils.logger import ler_historico
from ui.widgets import criar_cabecalho_secao, criar_painel_em_breve

_ICONE_ESTADO = {"concluida": ("\u2714", COR_OK), "erro": ("\u2716", COR_ERRO)}


def _formatar_duracao(segundos) -> str:
    if segundos is None:
        return "—"
    segundos = int(segundos)
    if segundos < 60:
        return f"{segundos}s"
    m, s = divmod(segundos, 60)
    return f"{m}min {s}s"


class HistoricoView(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._montar()

    def _montar(self):
        criar_cabecalho_secao(
            self, "\U0001F4DC", "Histórico",
            "Execuções em lote anteriores, mais recente primeiro",
        )

        lotes = ler_historico()
        if not lotes:
            criar_painel_em_breve(self, "\U0001F4DC", "Nenhuma execução registrada ainda")
            return

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(canvas_frame, bg=COR_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        lista = ttk.Frame(canvas)

        janela_id = canvas.create_window((0, 0), window=lista, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _atualizar_scrollregion(_evento=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _ajustar_largura(evento):
            canvas.itemconfig(janela_id, width=evento.width)

        lista.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura)

        def _on_scroll(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_scroll))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        canvas.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        for lote in lotes:
            self._criar_card_lote(lista, lote)

    def _criar_card_lote(self, parent, lote: dict):
        card = tk.Frame(parent, bg=COR_BG_CARD, highlightthickness=1, highlightbackground=COR_BORDA)
        card.pack(fill="x", pady=5, padx=2)
        inner = tk.Frame(card, bg=COR_BG_CARD)
        inner.pack(fill="x", padx=16, pady=12)

        total = len(lote["tarefas"])
        falhas = sum(1 for t in lote["tarefas"] if t["estado"] == "erro")
        situacao = "sem falhas" if falhas == 0 else f"{falhas} de {total} com falha"
        cabecalho = f"{lote['data_inicio']}  —  {total} tarefa(s), {situacao}"
        if not lote["completo"]:
            cabecalho += "  (execução interrompida)"

        ttk.Label(inner, text=cabecalho, style="Card.TLabel").pack(anchor="w")

        duracao_txt = _formatar_duracao(lote.get("duracao_s"))
        tk.Label(
            inner, text=f"Duração total: {duracao_txt}", bg=COR_BG_CARD,
            fg=COR_TEXTO_FRACO, font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(2, 8))

        for tarefa in lote["tarefas"]:
            linha = tk.Frame(inner, bg=COR_BG_CARD)
            linha.pack(fill="x", pady=1)
            simbolo, cor = _ICONE_ESTADO.get(tarefa["estado"], ("\u25CB", COR_TEXTO_FRACO))
            tk.Label(linha, text=simbolo, bg=COR_BG_CARD, fg=cor, font=("Segoe UI", 9, "bold"),
                     width=2).pack(side="left")
            tk.Label(linha, text=tarefa["titulo"], bg=COR_BG_CARD, fg=COR_TEXTO,
                     font=("Segoe UI", 9)).pack(side="left")
            tk.Label(linha, text=_formatar_duracao(tarefa["duracao_s"]), bg=COR_BG_CARD,
                     fg=COR_TEXTO_FRACO, font=("Segoe UI", 8)).pack(side="right")
