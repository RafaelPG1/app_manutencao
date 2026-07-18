# ==========================================================
# Arquivo: ui/widgets.py
# Responsabilidade: Componentes visuais reutilizáveis —
# card clicável de tarefa, cartão de estatística do dashboard,
# cabeçalho de seção e painel de "em breve".
# ==========================================================

import tkinter as tk
from tkinter import ttk

from utils.constants import (
    COR_BG, COR_BG_CARD, COR_BG_CARD_HOVER, COR_BG_CARD_SELECIONADO,
    COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO, COR_ACCENT, COR_OK,
)


def _bind_recursivo(widget, evento, callback):
    """Aplica o mesmo bind a um widget e a todos os seus descendentes,
    para que clicar em QUALQUER ponto do card (não apenas na checkbox)
    alterne a seleção."""
    widget.bind(evento, callback)
    for filho in widget.winfo_children():
        _bind_recursivo(filho, evento, callback)


def criar_card_tarefa(parent, tarefa, var: tk.BooleanVar):
    """Cria e retorna um card clicável representando uma tarefa —
    ícone, título, estado, descrição, comando técnico (quando existir)
    e tempo estimado (quando existir), com checkbox integrada.

    `tarefa` é uma utils.tasks.TaskDefinition: todos os campos
    exibidos (descricao, comando_tecnico, tempo_estimado_min) são
    lidos diretamente dela, já prontos para exibição — nenhum texto é
    interpretado ou dividido aqui.

    O card inteiro — incluindo os espaçamentos e a área de texto — é
    clicável. Quando selecionado, a borda, o fundo e o ícone mudam
    para deixar isso evidente."""
    card = tk.Frame(parent, bg=COR_BG_CARD, cursor="hand2",
                     highlightthickness=1, highlightbackground=COR_BORDA)
    card.pack(fill="x", pady=5, padx=2)

    corpo = tk.Frame(card, bg=COR_BG_CARD)
    corpo.pack(fill="x")

    chk_frame = tk.Frame(corpo, bg=COR_BG_CARD)
    chk_frame.pack(side="left", padx=(12, 6), pady=14)
    chk = ttk.Checkbutton(chk_frame, variable=var, style="TCheckbutton")
    chk.pack()

    icone_frame = tk.Frame(corpo, bg=COR_BG_CARD)
    icone_frame.pack(side="left", padx=(0, 10), pady=14)
    icone_lbl = tk.Label(icone_frame, text=tarefa.icone, bg=COR_BG_CARD, fg=COR_TEXTO,
                          font=("Segoe UI", 16))
    icone_lbl.pack()

    texto_frame = tk.Frame(corpo, bg=COR_BG_CARD)
    texto_frame.pack(side="left", fill="both", expand=True, pady=12, padx=(0, 12))

    linha_titulo = tk.Frame(texto_frame, bg=COR_BG_CARD)
    linha_titulo.pack(fill="x", anchor="w")
    titulo_lbl = ttk.Label(linha_titulo, text=tarefa.titulo, style="Card.TLabel")
    titulo_lbl.pack(side="left", anchor="w")
    estado_lbl = tk.Label(linha_titulo, text="Pronto para executar", bg=COR_BG_CARD,
                           fg=COR_OK, font=("Segoe UI", 8, "bold"))
    estado_lbl.pack(side="right", anchor="e")

    desc_lbl = None
    if tarefa.descricao:
        desc_lbl = ttk.Label(texto_frame, text=tarefa.descricao, style="CardDesc.TLabel")
        desc_lbl.pack(anchor="w", pady=(2, 0))

    rodape_frame = tk.Frame(texto_frame, bg=COR_BG_CARD)
    tecnico_lbl = None
    tempo_lbl = None
    if tarefa.comando_tecnico or tarefa.tempo_estimado_min:
        rodape_frame.pack(fill="x", anchor="w", pady=(6, 0))
        if tarefa.comando_tecnico:
            tecnico_lbl = tk.Label(rodape_frame, text=tarefa.comando_tecnico, bg=COR_BG_CARD,
                                    fg=COR_TEXTO_FRACO, font=("Consolas", 8))
            tecnico_lbl.pack(side="left")
        if tarefa.tempo_estimado_min:
            tempo_lbl = tk.Label(
                rodape_frame, text=f"\u23F1  ~{tarefa.tempo_estimado_min} min",
                bg=COR_BG_CARD, fg=COR_TEXTO_FRACO, font=("Segoe UI", 8),
            )
            tempo_lbl.pack(side="left", padx=(10, 0) if tarefa.comando_tecnico else 0)

    frames_fundo = [card, corpo, chk_frame, icone_frame, texto_frame, linha_titulo, rodape_frame]
    labels_fundo = [w for w in (desc_lbl, tecnico_lbl, tempo_lbl, estado_lbl) if w is not None]

    def _pintar(cor_fundo, cor_borda=None, cor_icone=None, espessura_borda=None):
        try:
            if cor_borda is not None:
                card.configure(highlightbackground=cor_borda)
            if espessura_borda is not None:
                card.configure(highlightthickness=espessura_borda)
            for w in frames_fundo:
                w.configure(bg=cor_fundo)
            for w in labels_fundo:
                w.configure(bg=cor_fundo)
            icone_lbl.configure(bg=cor_fundo, fg=(cor_icone or COR_TEXTO))
            titulo_lbl.configure(background=cor_fundo)
            if desc_lbl is not None:
                desc_lbl.configure(background=cor_fundo)
        except tk.TclError:
            # O card já foi destruído (ex.: usuário trocou de categoria)
            # mas a variável ainda mantinha este callback registrado —
            # ignora silenciosamente em vez de propagar o erro.
            pass

    def repintar(*_):
        if var.get():
            _pintar(COR_BG_CARD_SELECIONADO, cor_borda=COR_ACCENT,
                    cor_icone=COR_ACCENT, espessura_borda=2)
        else:
            _pintar(COR_BG_CARD, cor_borda=COR_BORDA,
                    cor_icone=COR_TEXTO, espessura_borda=1)

    def alternar(event=None):
        # Evita alternar duas vezes quando o clique já veio da própria
        # checkbox (ela alterna sozinha antes deste handler rodar).
        if event is not None and str(event.widget).endswith("!checkbutton"):
            return
        var.set(not var.get())

    def hover_on(_e=None):
        if not var.get():
            _pintar(COR_BG_CARD_HOVER)

    def hover_off(_e=None):
        repintar()

    # Uma mesma tarefa (BooleanVar) é reaproveitada entre visitas à
    # categoria — a tela é destruída e recriada a cada navegação. Antes
    # de registrar um novo callback de repintura, remove o anterior
    # (se ainda existir) para não deixar um callback "órfão" apontando
    # para widgets já destruídos.
    trace_antigo = getattr(var, "_card_trace_id", None)
    if trace_antigo:
        try:
            var.trace_remove("write", trace_antigo)
        except Exception:
            pass
    var._card_trace_id = var.trace_add("write", repintar)
    repintar()

    _bind_recursivo(card, "<Button-1>", alternar)
    _bind_recursivo(card, "<Enter>", hover_on)
    _bind_recursivo(card, "<Leave>", hover_off)

    return card


def criar_cabecalho_secao(parent, icone, titulo, subtitulo=None):
    """Cabeçalho de uma tela de categoria: ícone + título + subtítulo,
    seguido de uma linha divisória sutil."""
    wrap = ttk.Frame(parent)
    wrap.pack(fill="x", pady=(0, 16))

    ttk.Label(wrap, text=f"{icone}  {titulo}", style="TituloSecao.TLabel").pack(anchor="w")
    if subtitulo:
        ttk.Label(wrap, text=subtitulo, style="Status.TLabel").pack(anchor="w", pady=(2, 0))

    linha = tk.Frame(wrap, bg=COR_BORDA, height=1)
    linha.pack(fill="x", pady=(12, 0))
    return wrap


def _tamanho_fonte_para(texto: str) -> int:
    """Reduz o tamanho da fonte do valor conforme o texto cresce, para
    que textos mais longos (ex.: 'Nenhuma sessão registrada ainda')
    quebrem em menos linhas e não estourem o card."""
    if len(texto) > 26:
        return 11
    if len(texto) > 16:
        return 13
    return 15


def criar_card_estatistica(parent, icone, rotulo, valor, cor_valor=None):
    """Cartão compacto usado no Dashboard para mostrar um indicador
    (ex.: tipo de disco, espaço livre, status do Windows).

    O texto do rótulo e do valor quebra automaticamente de acordo com
    a largura real do card (recalculada a cada redimensionamento), e o
    valor reduz de tamanho quando o texto é mais longo — assim nenhum
    texto ultrapassa a borda do card, sem precisar aumentar a janela.
    """
    card = tk.Frame(parent, bg=COR_BG_CARD, highlightthickness=1,
                     highlightbackground=COR_BORDA)

    inner = tk.Frame(card, bg=COR_BG_CARD)
    inner.pack(fill="both", expand=True, padx=16, pady=14)

    ttk.Label(inner, text=icone, style="StatIcone.TLabel").pack(anchor="w")

    rotulo_lbl = tk.Label(inner, text=rotulo, bg=COR_BG_CARD, fg=COR_TEXTO_FRACO,
                           font=("Segoe UI", 8), justify="left", anchor="w")
    rotulo_lbl.pack(anchor="w", fill="x", pady=(6, 0))

    valor_lbl = tk.Label(inner, text=valor, bg=COR_BG_CARD, fg=(cor_valor or COR_TEXTO),
                          font=("Segoe UI", _tamanho_fonte_para(valor), "bold"),
                          justify="left", anchor="w")
    valor_lbl.pack(anchor="w", fill="x", pady=(2, 0))

    def _ajustar_wraplength(_evento=None):
        largura_util = max(inner.winfo_width() - 4, 60)
        rotulo_lbl.config(wraplength=largura_util)
        valor_lbl.config(wraplength=largura_util)

    inner.bind("<Configure>", _ajustar_wraplength)

    def definir_valor(texto: str, cor=None):
        """Atualiza o valor do card, reajustando fonte e quebra de
        linha automaticamente. Use isso (em vez de mexer direto no
        label) para manter o texto sempre dentro do card."""
        valor_lbl.config(text=texto, font=("Segoe UI", _tamanho_fonte_para(texto), "bold"))
        if cor:
            valor_lbl.config(fg=cor)
        _ajustar_wraplength()

    card.valor_label = valor_lbl  # mantido para compatibilidade
    card.definir_valor = definir_valor
    return card


def criar_painel_em_breve(parent, icone, titulo):
    """Estado vazio para categorias da sidebar que ainda não têm
    tarefas reais implementadas nesta etapa."""
    wrap = ttk.Frame(parent)
    wrap.pack(fill="both", expand=True)

    centro = ttk.Frame(wrap)
    centro.place(relx=0.5, rely=0.42, anchor="center")

    ttk.Label(centro, text=icone, font=("Segoe UI", 34)).pack()
    ttk.Label(centro, text=f"{titulo} — em breve", style="Card.TLabel").pack(pady=(10, 4))
    ttk.Label(centro, text="Esta categoria está reservada para futuras funcionalidades.",
              style="Status.TLabel").pack()
    return wrap