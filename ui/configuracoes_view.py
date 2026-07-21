# ==========================================================
# Arquivo: ui/configuracoes_view.py
# Responsabilidade: Tela da categoria Configurações — preferências
# do PRÓPRIO APLICATIVO (nada aqui altera configurações do Windows).
# Fase 8 do roadmap.
#
# Tela informativa/de preferências, sem checkbox de tarefa nem
# execução em lote — não usa TaskView, no mesmo espírito de
# ui/sistema_view.py, ui/historico_view.py e ui/ferramentas_view.py.
# Usa rolagem (canvas + scrollbar) no mesmo padrão dessas duas
# últimas.
#
# Cada alteração (checkbox, campo numérico) é salva imediatamente via
# app.atualizar_configuracao(chave, valor) — sem botão "Salvar"
# separado — que por sua vez persiste tudo através de
# utils/settings.py.
#
# Os grupos seguem a organização e o conteúdo definidos para a Fase
# 8. Duas ressalvas, para não criar opções sem efeito real na
# interface (ver core/execution/execution_manager.py e
# utils/logger.py para o porquê):
#   - "Executar automaticamente como administrador" não vira um
#     toggle: o aplicativo já SEMPRE exige elevação ao abrir
#     (ver ui/main_window.py:_inicializar) — não é uma escolha por
#     tarefa. É exibido como informação, não como opção.
#   - "Limpar histórico" e "Limpar logs" viram uma única ação: os
#     dois são o MESMO arquivo (ver utils/logger.py), então duas
#     ações separadas fariam exatamente a mesma coisa com nomes
#     diferentes.
# ==========================================================

import tkinter as tk
from tkinter import ttk

from config import APP_VERSAO
from utils.constants import (
    COR_BG, COR_BG_CARD, COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO,
)
from ui.widgets import criar_cabecalho_secao

_LARGURA_SPINBOX = 6


class ConfiguracoesView(ttk.Frame):
    def __init__(self, parent, app):
        """app: referência ao ManutencaoApp — usada para ler
        app.configuracoes (dict já carregado do disco no __init__ do
        app) e para persistir mudanças via
        app.atualizar_configuracao(chave, valor) / app.limpar_historico_logs()."""
        super().__init__(parent)
        self.app = app
        self._montar()

    # -------------------- Estrutura da tela --------------------
    def _montar(self):
        criar_cabecalho_secao(
            self, "\u2699", "Configurações",
            "Preferências do aplicativo — não altera nenhuma configuração do Windows",
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

        self._montar_grupo_geral(conteudo)
        self._montar_grupo_historico_logs(conteudo)
        self._montar_grupo_atualizacoes(conteudo)
        self._montar_grupo_interface(conteudo)

    # -------------------- Card genérico de grupo --------------------
    # Réplica local do mesmo padrão visual de card usado em todo o app
    # (fundo COR_BG_CARD, borda COR_BORDA, cabeçalho ícone+título) —
    # mesmo racional de ui/historico_view.py:_criar_card_lote: o
    # conteúdo de cada card aqui (linhas de preferência) é específico
    # demais desta tela para entrar em ui/widgets.py.
    def _criar_card_grupo(self, parent, icone, titulo, subtitulo=None):
        card = tk.Frame(parent, bg=COR_BG_CARD, highlightthickness=1, highlightbackground=COR_BORDA)
        card.pack(fill="x", pady=(0, 14))

        inner = tk.Frame(card, bg=COR_BG_CARD)
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        cabecalho = tk.Frame(inner, bg=COR_BG_CARD)
        cabecalho.pack(fill="x", anchor="w")
        tk.Label(cabecalho, text=icone, bg=COR_BG_CARD, fg=COR_TEXTO,
                  font=("Segoe UI", 13)).pack(side="left")
        tk.Label(cabecalho, text=titulo, bg=COR_BG_CARD, fg=COR_TEXTO,
                  font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 0))

        if subtitulo:
            tk.Label(inner, text=subtitulo, bg=COR_BG_CARD, fg=COR_TEXTO_FRACO,
                      font=("Segoe UI", 8), justify="left", anchor="w",
                      wraplength=520).pack(fill="x", anchor="w", pady=(2, 0))

        divisoria = tk.Frame(inner, bg=COR_BORDA, height=1)
        divisoria.pack(fill="x", pady=(10, 8))

        return inner

    def _linha_checkbox(self, parent, texto, chave, valor_atual):
        var = tk.BooleanVar(value=bool(valor_atual))
        chk = ttk.Checkbutton(
            parent, text=texto, variable=var, style="TCheckbutton",
            command=lambda: self.app.atualizar_configuracao(chave, var.get()),
        )
        chk.pack(anchor="w", pady=3)
        return var

    def _linha_informativa(self, parent, texto, valor_texto):
        linha = tk.Frame(parent, bg=COR_BG_CARD)
        linha.pack(fill="x", pady=3)
        tk.Label(linha, text=texto, bg=COR_BG_CARD, fg=COR_TEXTO,
                  font=("Segoe UI", 9), anchor="w").pack(side="left")
        tk.Label(linha, text=valor_texto, bg=COR_BG_CARD, fg=COR_TEXTO_FRACO,
                  font=("Segoe UI", 8, "italic")).pack(side="right")

    # -------------------- Geral --------------------
    def _montar_grupo_geral(self, parent):
        cfg = self.app.configuracoes
        card = self._criar_card_grupo(parent, "\u2699", "Geral")

        self._linha_checkbox(
            card, "Confirmar antes de executar tarefas",
            "confirmar_antes_executar", cfg.get("confirmar_antes_executar", True),
        )
        self._linha_checkbox(
            card, "Abrir sempre na última categoria utilizada",
            "abrir_ultima_categoria", cfg.get("abrir_ultima_categoria", False),
        )
        self._linha_informativa(
            card, "Executar automaticamente como administrador",
            "Sempre ativo (obrigatório em todo o app)",
        )

    # -------------------- Histórico e Logs --------------------
    def _montar_grupo_historico_logs(self, parent):
        cfg = self.app.configuracoes
        card = self._criar_card_grupo(
            parent, "\U0001F4DC", "Histórico e Logs",
            "Histórico e logs são gravados no mesmo arquivo — limpar um limpa o outro.",
        )

        linha_max = tk.Frame(card, bg=COR_BG_CARD)
        linha_max.pack(fill="x", pady=3)
        tk.Label(linha_max, text="Quantidade máxima de registros exibidos no Histórico",
                  bg=COR_BG_CARD, fg=COR_TEXTO, font=("Segoe UI", 9), anchor="w").pack(side="left")

        var_max = tk.StringVar(value=str(cfg.get("max_registros_historico", 50)))

        def _aplicar_max(_evento=None):
            try:
                valor = max(1, min(500, int(var_max.get())))
            except ValueError:
                valor = cfg.get("max_registros_historico", 50)
            var_max.set(str(valor))
            self.app.atualizar_configuracao("max_registros_historico", valor)

        spin = tk.Spinbox(
            linha_max, from_=1, to=500, increment=10, textvariable=var_max,
            width=_LARGURA_SPINBOX, justify="center", command=_aplicar_max,
            bg=COR_BG, fg=COR_TEXTO, buttonbackground=COR_BG_CARD,
            highlightthickness=1, highlightbackground=COR_BORDA, relief="flat",
        )
        spin.pack(side="right")
        spin.bind("<FocusOut>", _aplicar_max)
        spin.bind("<Return>", _aplicar_max)

        botoes = tk.Frame(card, bg=COR_BG_CARD)
        botoes.pack(fill="x", pady=(10, 0))
        ttk.Button(
            botoes, text="Limpar histórico e logs", style="Secundario.TButton",
            command=self.app.limpar_historico_logs,
        ).pack(anchor="w")

    # -------------------- Atualizações --------------------
    def _montar_grupo_atualizacoes(self, parent):
        card = self._criar_card_grupo(parent, "\u2B06", "Atualizações")

        self._linha_informativa(card, "Versão atual", f"v{APP_VERSAO}")

        linha_botao = tk.Frame(card, bg=COR_BG_CARD)
        linha_botao.pack(fill="x", pady=(10, 0))
        ttk.Button(
            linha_botao, text="Verificar atualizações (em breve)",
            style="Secundario.TButton", state="disabled",
        ).pack(anchor="w")

    # -------------------- Interface --------------------
    def _montar_grupo_interface(self, parent):
        card = self._criar_card_grupo(parent, "\U0001F3A8", "Interface")
        tk.Label(
            card,
            text="Nenhuma preferência visual disponível nesta versão.\n"
                 "Espaço reservado para opções futuras (ex.: temas).",
            bg=COR_BG_CARD, fg=COR_TEXTO_FRACO, font=("Segoe UI", 9),
            justify="left", anchor="w",
        ).pack(anchor="w", pady=3)