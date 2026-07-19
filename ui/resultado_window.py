# ==========================================================
# Arquivo: ui/resultado_window.py
# Responsabilidade: Janela genérica (Toplevel) para exibir o
# resultado de uma AÇÃO INSTANTÂNEA — uma consulta rápida que roda
# fora do ExecutionManager e não se encaixa numa simples
# messagebox.showinfo() de uma linha (ex.: saúde SMART de vários
# discos, lista de eventos críticos, análise de espaço por pasta).
#
# Reaproveitada por várias ações da categoria Diagnóstico (ver
# core/diagnostico/smart_disco.py, espaco_disco.py,
# eventos_criticos.py) em vez de cada uma desenhar sua própria
# janela — mesmo racional de módulo compartilhado já usado em
# core/shared/comando_terminal.py.
#
# Segue o tema escuro do restante do aplicativo (cores importadas de
# utils/constants.py) e não depende de nenhum estado do
# ExecutionManager — só recebe texto pronto para exibir.
# ==========================================================

import tkinter as tk
from tkinter import ttk

from utils.constants import (
    COR_BG, COR_BG_CARD, COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO, COR_ACCENT,
)


def exibir_resultado(parent, titulo: str, texto: str, largura=640, altura=460):
    """Abre uma janela modal simples com um bloco de texto rolável
    (monoespaçado, para preservar alinhamento de colunas) mostrando
    `texto`. Bloqueia interação com a janela principal enquanto
    aberta (grab_set), mas não bloqueia a execução em lote em si —
    ela roda independente de qualquer tela, como sempre."""
    janela = tk.Toplevel(parent)
    janela.title(titulo)
    janela.configure(bg=COR_BG)
    janela.geometry(f"{largura}x{altura}")
    janela.minsize(420, 260)

    cabecalho = ttk.Frame(janela, padding=(16, 14, 16, 8))
    cabecalho.pack(fill="x")
    ttk.Label(cabecalho, text=titulo, style="TituloSecao.TLabel").pack(anchor="w")

    corpo = tk.Frame(janela, bg=COR_BG)
    corpo.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    caixa = tk.Frame(corpo, bg=COR_BG_CARD, highlightthickness=1, highlightbackground=COR_BORDA)
    caixa.pack(fill="both", expand=True)

    txt = tk.Text(
        caixa, wrap="word", bg=COR_BG_CARD, fg=COR_TEXTO, insertbackground=COR_TEXTO,
        relief="flat", padx=12, pady=10, font=("Consolas", 9), highlightthickness=0,
    )
    scroll = ttk.Scrollbar(caixa, orient="vertical", command=txt.yview)
    txt.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    txt.pack(side="left", fill="both", expand=True)

    txt.insert("1.0", texto)
    txt.configure(state="disabled")

    rodape = ttk.Frame(janela, padding=(16, 0, 16, 14))
    rodape.pack(fill="x")
    ttk.Button(rodape, text="Fechar", style="Secundario.TButton", command=janela.destroy).pack(side="right")

    janela.transient(parent)
    janela.grab_set()
    return janela
