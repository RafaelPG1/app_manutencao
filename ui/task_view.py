# ==========================================================
# Arquivo: ui/task_view.py
# Responsabilidade: Tela de uma categoria de tarefas — lista
# de cards clicáveis pertencentes àquela categoria, com ações
# de seleção e o botão de execução.
# ==========================================================

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

from utils.constants import COR_BG, COR_BG_CARD, COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO, CATEGORIAS
from ui.widgets import criar_cabecalho_secao, criar_card_tarefa, criar_painel_em_breve

_META_CATEGORIAS = {c[0]: c for c in CATEGORIAS}

# Controla se o estilo discreto da scrollbar já foi registrado neste
# processo — evita reconfigurar o mesmo estilo repetidamente toda vez
# que o usuário navega para uma categoria com tarefas.
_ESTILO_SCROLL_CONFIGURADO = False


def _garantir_estilo_scroll():
    """Registra, uma única vez, um estilo ttk próprio e discreto para a
    barra de rolagem da lista de tarefas (mais fina, sem relevo 3D e
    com cores alinhadas ao tema escuro). Usa um NOME de estilo novo
    ("Tarefas.Vertical.TScrollbar") — não sobrescreve o "TScrollbar"
    padrão nem qualquer outro estilo já usado no restante da
    interface, então nada fora do scroll desta tela é afetado."""
    global _ESTILO_SCROLL_CONFIGURADO
    if _ESTILO_SCROLL_CONFIGURADO:
        return
    try:
        style = ttk.Style()
        style.configure(
            "Tarefas.Vertical.TScrollbar",
            background=COR_BG_CARD,
            troughcolor=COR_BG,
            bordercolor=COR_BG,
            arrowcolor=COR_TEXTO_FRACO,
            relief="flat",
            borderwidth=0,
            width=10,
        )
        style.map(
            "Tarefas.Vertical.TScrollbar",
            background=[("active", COR_BORDA), ("!active", COR_BG_CARD)],
        )
    except Exception:
        # Em temas/plataformas que não aceitem alguma dessas opções,
        # mantém a scrollbar nativa padrão em vez de quebrar a tela.
        pass
    _ESTILO_SCROLL_CONFIGURADO = True


class TaskView(ttk.Frame):
    def __init__(self, parent, app, categoria: str, tarefas, acoes_instantaneas=None):
        """app: referência ao ManutencaoApp (fornece vars_tarefas e ações).
        categoria: chave da categoria (ex.: 'limpeza').
        tarefas: lista de utils.tasks.TaskDefinition já filtrada para
        esta categoria.
        acoes_instantaneas: lista opcional de dicts
        {"icone": str, "titulo": str, "comando": callable} — ações que
        rodam na hora (fora do lote checkbox + Executar), mostradas
        como botões secundários logo abaixo do cabeçalho. Usado hoje
        pela categoria Diagnóstico para consultas rápidas e somente
        leitura (SMART, espaço por pasta, eventos críticos) cujo
        resultado é mostrado em uma janela própria (ver
        ui/resultado_window.py) em vez de passar pelo
        ExecutionManager — ver o cabeçalho de
        core/diagnostico/espaco_disco.py para o racional completo.
        Nenhuma categoria existente passa este parâmetro, então nada
        muda para elas."""
        super().__init__(parent)
        self.app = app
        self.categoria = categoria
        self.tarefas = tarefas
        self.acoes_instantaneas = acoes_instantaneas or []
        self._scrollbar_visivel = False
        self._montar()

    def _montar(self):
        _chave, icone, titulo, subtitulo = _META_CATEGORIAS.get(
            self.categoria, (self.categoria, "\U0001F4C1", self.categoria.title(), "")
        )
        criar_cabecalho_secao(self, icone, titulo, subtitulo)

        if not self.tarefas:
            criar_painel_em_breve(self, icone, titulo)
            return

        self._montar_acoes_instantaneas()
        self._montar_resumo()

        acoes_topo = ttk.Frame(self)
        acoes_topo.pack(fill="x", pady=(0, 10))
        ttk.Button(acoes_topo, text="Selecionar tudo", style="Secundario.TButton",
                   command=self._selecionar_tudo).pack(side="left")
        ttk.Button(acoes_topo, text="Limpar seleção", style="Secundario.TButton",
                   command=self._limpar_selecao).pack(side="left", padx=6)

        self._montar_area_scroll()

        # ----- rodapé com botão de execução -----
        rodape = ttk.Frame(self)
        rodape.pack(fill="x", pady=(10, 0))
        btn_executar = ttk.Button(
            rodape, text="\u25B6  Executar selecionadas desta categoria",
            style="Accent.TButton", command=self._executar_categoria
        )
        btn_executar.pack(fill="x")

        # O texto ficava cortado em janelas mais estreitas: o botão
        # ocupa toda a largura (fill="x"), mas o ttk nunca reduz um
        # widget abaixo da largura "natural" pedida pelo texto — em vez
        # disso, alguns temas simplesmente cortam o que não cabe, sem
        # quebrar linha.
        #
        # A tentativa anterior usava btn_executar.config(wraplength=...),
        # mas wraplength é uma opção específica de ttk.Label — ttk.Button
        # não a reconhece, e isso disparava
        # "_tkinter.TclError: unknown option '-wraplength'" a cada
        # redimensionamento (ver traceback reportado). A correção mede a
        # largura real do texto com a fonte do próprio botão e quebra em
        # duas linhas manualmente quando necessário, sem depender de
        # nenhuma opção que ttk.Button não suporta.
        texto_botao_completo = "\u25B6  Executar selecionadas desta categoria"
        fonte_botao = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        def _ajustar_texto_botao(evento):
            largura_util = max(evento.width - 20, 60)
            if fonte_botao.measure(texto_botao_completo) <= largura_util:
                btn_executar.config(text=texto_botao_completo)
                return
            palavras = texto_botao_completo.split(" ")
            linhas = []
            linha_atual = ""
            for palavra in palavras:
                candidata = f"{linha_atual} {palavra}".strip()
                if not linha_atual or fonte_botao.measure(candidata) <= largura_util:
                    linha_atual = candidata
                else:
                    linhas.append(linha_atual)
                    linha_atual = palavra
            linhas.append(linha_atual)
            btn_executar.config(text="\n".join(linhas))

        btn_executar.bind("<Configure>", _ajustar_texto_botao)

    def _chaves(self):
        return [t.chave for t in self.tarefas]

    # -------------------- Ações instantâneas (opcional) --------------------
    def _montar_acoes_instantaneas(self):
        if not self.acoes_instantaneas:
            return
        bloco = ttk.Frame(self)
        bloco.pack(fill="x", pady=(0, 12))
        ttk.Label(bloco, text="Consultas rápidas (resultado exibido na hora)",
                  style="Status.TLabel").pack(anchor="w", pady=(0, 6))
        linha = ttk.Frame(bloco)
        linha.pack(fill="x")
        for acao in self.acoes_instantaneas:
            ttk.Button(
                linha, text=f"{acao['icone']}  {acao['titulo']}", style="Secundario.TButton",
                command=acao["comando"],
            ).pack(side="left", padx=(0, 8))

    # -------------------- Área de scroll dos cards --------------------
    def _montar_area_scroll(self):
        """Monta a lista rolável de cards de tarefa.

        Pontos importantes deste comportamento:
        - o primeiro card começa imediatamente abaixo dos botões
          "Selecionar tudo" / "Limpar seleção", sem espaço vazio
          reservado acima dele;
        - a scrollbar (e a rolagem pelo mouse) só aparecem quando o
          conteúdo realmente não cabe na área visível;
        - a barra usa um estilo mais discreto, coerente com o tema
          escuro do restante da interface.
        """
        _garantir_estilo_scroll()

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, bg=COR_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=canvas.yview,
            style="Tarefas.Vertical.TScrollbar",
        )
        lista = ttk.Frame(canvas)

        janela_id = canvas.create_window((0, 0), window=lista, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        # A scrollbar só é "packada" quando realmente há conteúdo
        # suficiente para rolar — por padrão começa oculta, sem
        # reservar espaço nenhum.

        def _atualizar_necessidade_scroll():
            """Decide se a rolagem é realmente necessária comparando a
            altura pedida pelo conteúdo com a altura visível do
            canvas. Quando cabe tudo, a scrollbar some e a visão é
            travada no topo; quando não cabe, a scrollbar volta."""
            if not canvas.winfo_exists():
                return
            altura_conteudo = lista.winfo_reqheight()
            altura_visivel = canvas.winfo_height()
            precisa_scroll = altura_conteudo > altura_visivel

            if precisa_scroll and not self._scrollbar_visivel:
                scrollbar.pack(side="right", fill="y")
                self._scrollbar_visivel = True
            elif not precisa_scroll and self._scrollbar_visivel:
                scrollbar.pack_forget()
                self._scrollbar_visivel = False

            if not precisa_scroll:
                # Conteúdo cabe todo: garante que não sobre nenhum
                # espaço vazio reservado acima do primeiro card.
                canvas.yview_moveto(0)

        def _atualizar_scrollregion(_evento=None):
            # A causa do espaço vazio acima do primeiro card era a
            # scrollregion ficar "presa" numa posição intermediária,
            # calculada enquanto os cards ainda estavam sendo
            # adicionados. Recalcular a scrollregion e realinhar a
            # visão ao topo sempre que o tamanho da lista muda evita
            # esse deslocamento.
            canvas.configure(scrollregion=canvas.bbox("all"))
            _atualizar_necessidade_scroll()

        def _ajustar_largura_interna(evento):
            canvas.itemconfig(janela_id, width=evento.width)
            _atualizar_necessidade_scroll()

        lista.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura_interna)

        # O rolamento do mouse só é vinculado enquanto o cursor está
        # sobre este canvas (e é removido ao sair dele ou destruir a
        # tela) — e só tem efeito quando a scrollbar está visível,
        # ou seja, quando realmente há o que rolar.
        def _on_scroll(event):
            if canvas.winfo_exists() and self._scrollbar_visivel:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _vincular_scroll(_e=None):
            canvas.bind_all("<MouseWheel>", _on_scroll)

        def _desvincular_scroll(_e=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _vincular_scroll)
        canvas.bind("<Leave>", _desvincular_scroll)
        canvas.bind("<Destroy>", _desvincular_scroll)

        for tarefa in self.tarefas:
            var = self.app.vars_tarefas[tarefa.chave]
            criar_card_tarefa(lista, tarefa, var)
            self._observar_selecao(var)

        # Passe final: com todos os cards já montados, garante que a
        # scrollregion, a necessidade (ou não) de scrollbar e a
        # posição do topo reflitam o estado definitivo da lista.
        self.after_idle(_atualizar_scrollregion)

    # -------------------- Resumo da categoria --------------------
    def _montar_resumo(self):
        """Pequeno painel acima da lista de tarefas com o total de
        ferramentas disponíveis, quantas estão selecionadas e o tempo
        estimado da seleção atual. Atualiza sozinho conforme o usuário
        marca/desmarca tarefas (ver _observar_selecao)."""
        resumo = tk.Frame(self, bg=COR_BG_CARD, highlightthickness=1, highlightbackground=COR_BORDA)
        resumo.pack(fill="x", pady=(0, 14))

        inner = tk.Frame(resumo, bg=COR_BG_CARD)
        inner.pack(fill="x", padx=18, pady=12)
        for col in range(3):
            inner.columnconfigure(col, weight=1)

        self.lbl_valor_disponiveis = self._criar_item_resumo(inner, "Ferramentas disponíveis", 0)
        self.lbl_valor_selecionadas = self._criar_item_resumo(inner, "Selecionadas", 1)
        self.lbl_valor_tempo = self._criar_item_resumo(inner, "Tempo estimado", 2)

        self._atualizar_resumo()

    @staticmethod
    def _criar_item_resumo(parent, rotulo, coluna):
        bloco = tk.Frame(parent, bg=COR_BG_CARD)
        bloco.grid(row=0, column=coluna, sticky="w", padx=(0 if coluna == 0 else 18, 0))
        tk.Label(bloco, text=rotulo, bg=COR_BG_CARD, fg=COR_TEXTO_FRACO,
                 font=("Segoe UI", 8)).pack(anchor="w")
        valor_lbl = tk.Label(bloco, text="0", bg=COR_BG_CARD, fg=COR_TEXTO,
                              font=("Segoe UI", 14, "bold"))
        valor_lbl.pack(anchor="w", pady=(2, 0))
        return valor_lbl

    def _observar_selecao(self, var: tk.BooleanVar):
        """Registra (substituindo qualquer registro anterior desta
        mesma variável, deixado por uma visita anterior a esta
        categoria já destruída) um callback que recalcula o resumo
        sempre que a seleção da tarefa mudar."""
        trace_antigo = getattr(var, "_resumo_trace_id", None)
        if trace_antigo:
            try:
                var.trace_remove("write", trace_antigo)
            except Exception:
                pass
        var._resumo_trace_id = var.trace_add("write", self._atualizar_resumo)

    def _atualizar_resumo(self, *_):
        try:
            por_chave = {t.chave: t for t in self.tarefas}
            selecionadas = [c for c in self._chaves() if self.app.vars_tarefas[c].get()]
            self.lbl_valor_disponiveis.config(text=str(len(self.tarefas)))
            self.lbl_valor_selecionadas.config(text=str(len(selecionadas)))
            if selecionadas:
                minutos = sum(por_chave[c].tempo_estimado_min or 0 for c in selecionadas)
                self.lbl_valor_tempo.config(text=f"~{minutos} min")
            else:
                self.lbl_valor_tempo.config(text="—")
        except tk.TclError:
            # Esta tela já foi destruída (usuário trocou de categoria)
            # mas a variável ainda mantinha este callback registrado.
            pass

    def _selecionar_tudo(self):
        for chave in self._chaves():
            self.app.vars_tarefas[chave].set(True)

    def _limpar_selecao(self):
        for chave in self._chaves():
            self.app.vars_tarefas[chave].set(False)

    def _executar_categoria(self):
        self.app.executar_selecionadas()