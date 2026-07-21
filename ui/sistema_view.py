# ==========================================================
# Arquivo: ui/sistema_view.py
# Responsabilidade: Tela da categoria Sistema — informações do
# computador (CPU, RAM, SO, fabricante/modelo, BIOS, placa-mãe,
# uptime, discos, GPU — Fase 1) e, a partir da Fase 4, também
# Segurança (Defender/BitLocker/TPM/Secure Boot), Rede (IP/gateway/
# DNS/adaptadores), Hardware (uso de CPU/RAM/disco) e Processos (top
# CPU/RAM). Tela PURAMENTE INFORMATIVA, somente leitura, sem checkbox
# nem execução em lote — por isso não usa TaskView, e sim uma view
# própria, no mesmo espírito de ui/dashboard.py.
#
# Cada seção é consultada em SUA PRÓPRIA thread de segundo plano,
# independente das demais (mesmo padrão já usado pela seção original
# de informações do sistema desde a Fase 1) — assim uma consulta mais
# lenta ou instável (ex.: BitLocker ausente, Get-Counter da CPU) nunca
# atrasa nem derruba a exibição das outras seções. Todas fazem a
# mesma checagem de `winfo_exists()`/`_destruida` antes de tocar em
# qualquer widget, para o caso de o usuário trocar de categoria antes
# de a consulta terminar.
#
# O DISPARO dessas consultas (quando iniciar, e o que fazer com um
# resultado que chega atrasado) não é mais decidido pela própria tela
# — é centralizado em _EstadoConsultasSistema, logo abaixo, para que
# o histórico de consultas sobreviva a navegações entre categorias e
# nunca existam duas consultas da mesma seção em andamento ao mesmo
# tempo (ver o cabeçalho dessa classe para o racional completo).
# ==========================================================

import threading
import tkinter as tk
from tkinter import ttk

from utils.constants import (
    COR_BG, COR_BG_CARD, COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO, COR_OK, COR_AVISO, COR_ERRO,
)
from core.sistema.system_info import obter_informacoes_sistema
from core.sistema.seguranca import obter_status_seguranca
from core.sistema.rede import obter_informacoes_rede
from core.sistema.hardware import obter_uso_hardware
from core.sistema.processos import obter_processos_top
from ui.widgets import criar_cabecalho_secao, criar_card_estatistica


def _fmt_gb(valor):
    if valor is None:
        return "—"
    return f"{valor:.1f} GB".replace(".", ",")


# ==========================================================
# Estado das consultas da tela Sistema — vive no MÓDULO, fora de
# qualquer instância de SistemaView, seguindo o mesmo princípio já
# usado em core/execution/execution_manager.py: o estado é dono de
# si mesmo, e a tela (recriada a cada navegação) apenas OBSERVA.
#
# Isso resolve os três problemas relatados na navegação:
#   - a tela "esquecia" tudo e voltava a mostrar "Consultando..." a
#     cada visita -> agora o último resultado conhecido de cada
#     seção fica em cache e é aplicado IMEDIATAMENTE ao reabrir a
#     tela, antes mesmo de qualquer nova consulta terminar;
#   - visitas rápidas (entrar/sair/entrar) disparavam várias
#     consultas da MESMA seção ao mesmo tempo, competindo por CPU e
#     fazendo a tela atualizar fora de ordem -> agora existe no
#     máximo uma consulta em andamento por seção, controlada por
#     `em_andamento`;
#   - o resultado de uma consulta iniciada por uma visita anterior
#     podia chegar depois que o usuário já tinha saído e voltado ->
#     agora o resultado é sempre entregue à instância de SistemaView
#     que estiver ativa NO MOMENTO em que a consulta termina (ou
#     descartado, se a tela Sistema não estiver aberta), nunca à
#     instância antiga que a originou.
# ==========================================================
class _EstadoConsultasSistema:
    SECOES = ("sistema", "seguranca", "rede", "hardware", "processos")

    def __init__(self):
        self.cache = {chave: None for chave in self.SECOES}
        self.em_andamento = {chave: False for chave in self.SECOES}
        self._view_ativa = None

    def registrar_view_ativa(self, view):
        self._view_ativa = view

    def desregistrar_view_ativa(self, view):
        if self._view_ativa is view:
            self._view_ativa = None

    def consultar(self, chave, funcao_consulta, aplicar_callback):
        """Aplica imediatamente o último resultado conhecido (se
        houver) e, se não houver nenhuma consulta desta seção já em
        andamento, dispara uma nova em segundo plano para atualizar o
        cache. O resultado da consulta é entregue a quem quer que
        seja a view ativa quando ela terminar — nunca à view que a
        disparou, caso essa já não seja mais a atual."""
        if self.cache[chave] is not None:
            aplicar_callback(self.cache[chave])

        if self.em_andamento[chave]:
            return
        self.em_andamento[chave] = True

        def alvo():
            resultado = funcao_consulta()
            self.cache[chave] = resultado
            self.em_andamento[chave] = False
            view = self._view_ativa
            if view is not None:
                view._apos(lambda: aplicar_callback(resultado))

        threading.Thread(target=alvo, daemon=True).start()


_estado_consultas = _EstadoConsultasSistema()

# Estilo discreto da scrollbar da tela Sistema — registrado uma única
# vez por processo, mesmo princípio já usado em ui/task_view.py
# (_garantir_estilo_scroll), mas com nome de estilo próprio para não
# acoplar os dois módulos.
_ESTILO_SCROLL_CONFIGURADO = False


def _garantir_estilo_scroll():
    global _ESTILO_SCROLL_CONFIGURADO
    if _ESTILO_SCROLL_CONFIGURADO:
        return
    try:
        style = ttk.Style()
        style.configure(
            "Sistema.Vertical.TScrollbar",
            background=COR_BG_CARD,
            troughcolor=COR_BG,
            bordercolor=COR_BG,
            arrowcolor=COR_TEXTO_FRACO,
            relief="flat",
            borderwidth=0,
            width=10,
        )
        style.map(
            "Sistema.Vertical.TScrollbar",
            background=[("active", COR_BORDA), ("!active", COR_BG_CARD)],
        )
    except Exception:
        pass
    _ESTILO_SCROLL_CONFIGURADO = True


class SistemaView(ttk.Frame):
    def __init__(self, parent, app):
        """app: referência ao ManutencaoApp — usada só para agendar o
        callback na thread principal via app.root.after (mesmo padrão
        de ui/dashboard.py)."""
        super().__init__(parent)
        self.app = app
        self.cards = {}
        self._destruida = False
        self.bind("<Destroy>", self._ao_destruir)
        self._montar()

        # Esta view passa a ser a "ativa": qualquer resultado que
        # chegue de agora em diante (mesmo de uma consulta iniciada por
        # uma visita anterior já destruída) é entregue a ela.
        _estado_consultas.registrar_view_ativa(self)

        _estado_consultas.consultar("sistema", obter_informacoes_sistema, self._aplicar)
        _estado_consultas.consultar("seguranca", obter_status_seguranca, self._aplicar_seguranca)
        _estado_consultas.consultar("rede", obter_informacoes_rede, self._aplicar_rede)
        _estado_consultas.consultar("hardware", obter_uso_hardware, self._aplicar_hardware)
        _estado_consultas.consultar("processos", obter_processos_top, self._aplicar_processos)

    def _ao_destruir(self, _evento=None):
        self._destruida = True
        _estado_consultas.desregistrar_view_ativa(self)

    def _apos(self, callback):
        """Agenda `callback` na thread principal, só se a view ainda
        existir — mesmo guard usado em todas as 5 consultas desta
        tela."""
        if not self._destruida and self.app and self.app.root:
            self.app.root.after(0, callback)

    # ==================== Montagem ====================
    def _montar(self):
        self._montar_area_scroll()
        conteudo = self.conteudo  # todo o conteúdo abaixo mora dentro da área rolável

        criar_cabecalho_secao(
            conteudo, "\U0001F5A5", "Sistema",
            "Informações do computador — consultado via WMI/CIM/PowerShell oficial do Windows",
        )

        grade = ttk.Frame(conteudo)
        grade.pack(fill="x")
        for col in range(4):
            grade.columnconfigure(col, weight=1, uniform="sysstat")

        definicoes = [
            ("cpu", "\U0001F9E0", "Processador"),
            ("ram", "\U0001F4BE", "Memória RAM"),
            ("so", "\U0001FA9F", "Sistema Operacional"),
            ("uptime", "\u23F1", "Tempo ligado"),
            ("fabricante", "\U0001F3ED", "Fabricante / Modelo"),
            ("bios", "\U0001F4BF", "BIOS"),
            ("placa_mae", "\U0001F5A5", "Placa-mãe"),
            ("gpu", "\U0001F5BC", "GPU"),
        ]
        for i, (chave, icone, rotulo) in enumerate(definicoes):
            card = criar_card_estatistica(grade, icone, rotulo, "Consultando...")
            card.grid(row=i // 4, column=i % 4, sticky="nsew", padx=(0 if i % 4 == 0 else 10, 0), pady=(0, 10))
            self.cards[chave] = card

        criar_cabecalho_secao(conteudo, "\U0001F4BD", "Discos instalados")
        self.frame_discos = ttk.Frame(conteudo)
        self.frame_discos.pack(fill="x")
        self._label_status(self.frame_discos, "Consultando...")

        # -------- Fase 4 --------
        criar_cabecalho_secao(conteudo, "\U0001F512", "Segurança")
        self.frame_seguranca = ttk.Frame(conteudo)
        self.frame_seguranca.pack(fill="x")
        self._label_status(self.frame_seguranca, "Consultando...")

        criar_cabecalho_secao(conteudo, "\U0001F310", "Rede")
        self.frame_rede = ttk.Frame(conteudo)
        self.frame_rede.pack(fill="x")
        self._label_status(self.frame_rede, "Consultando...")

        criar_cabecalho_secao(conteudo, "\U0001F4CA", "Uso de hardware")
        grade_hw = ttk.Frame(conteudo)
        grade_hw.pack(fill="x")
        for col in range(3):
            grade_hw.columnconfigure(col, weight=1, uniform="hwstat")
        self.card_cpu = criar_card_estatistica(grade_hw, "\U0001F525", "Uso de CPU", "Consultando...")
        self.card_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.card_ram = criar_card_estatistica(grade_hw, "\U0001F4BE", "Uso de RAM", "Consultando...")
        self.card_ram.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        self.frame_disco_uso = tk.Frame(grade_hw, bg=COR_BG_CARD, highlightthickness=1, highlightbackground=COR_BORDA)
        self.frame_disco_uso.grid(row=0, column=2, sticky="nsew")
        inner = tk.Frame(self.frame_disco_uso, bg=COR_BG_CARD)
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        ttk.Label(inner, text="\U0001F4BD", style="StatIcone.TLabel").pack(anchor="w")
        tk.Label(inner, text="Uso de disco", bg=COR_BG_CARD, fg=COR_TEXTO_FRACO,
                 font=("Segoe UI", 8), justify="left", anchor="w").pack(anchor="w", fill="x", pady=(6, 2))
        self.frame_disco_uso_linhas = tk.Frame(inner, bg=COR_BG_CARD)
        self.frame_disco_uso_linhas.pack(anchor="w", fill="x")
        tk.Label(self.frame_disco_uso_linhas, text="Consultando...", bg=COR_BG_CARD, fg=COR_TEXTO,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        criar_cabecalho_secao(conteudo, "\U0001F4C8", "Processos que mais consomem")
        self.frame_processos = ttk.Frame(conteudo)
        self.frame_processos.pack(fill="x")
        self._label_status(self.frame_processos, "Consultando...")

    # -------------------- Área de scroll (tela inteira) --------------------
    def _montar_area_scroll(self):
        """Envolve toda a tela Sistema numa área rolável — o conteúdo é
        extenso (informações gerais, discos, segurança, rede, hardware
        e processos) e não cabe confortavelmente em resoluções
        menores. Mesma técnica de canvas + scrollbar discreta já usada
        em ui/task_view.py (_montar_area_scroll): a barra só aparece
        quando o conteúdo realmente não cabe, e a rolagem pelo mouse
        só é ativa enquanto o cursor está sobre a área."""
        _garantir_estilo_scroll()

        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, bg=COR_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=canvas.yview,
            style="Sistema.Vertical.TScrollbar",
        )
        self.conteudo = ttk.Frame(canvas)

        janela_id = canvas.create_window((0, 0), window=self.conteudo, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)

        self._scrollbar_visivel = False

        def _atualizar_necessidade_scroll():
            if not canvas.winfo_exists():
                return
            altura_conteudo = self.conteudo.winfo_reqheight()
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

        self.conteudo.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura_interna)

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

        self.after_idle(_atualizar_scrollregion)

    def _label_status(self, parent, texto, cor=None):
        lbl = ttk.Label(parent, text=texto, style="Status.TLabel")
        if cor:
            lbl.configure(foreground=cor)
        lbl.pack(anchor="w")
        return lbl

    def _limpar(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    # ==================== Seção original (Fase 1) ====================
    def _aplicar(self, info: dict):
        if self._destruida or not self.winfo_exists():
            return

        if "erro" in info:
            for card in self.cards.values():
                card.definir_valor("Erro ao consultar", cor=COR_ERRO)
            self._limpar(self.frame_discos)
            self._label_status(self.frame_discos, f"Erro: {info['erro']}", cor=COR_ERRO)
            return

        nucleos = info.get("cpu_nucleos")
        threads = info.get("cpu_threads")
        sufixo_cpu = f" ({nucleos}n/{threads}t)" if nucleos and threads else ""
        self.cards["cpu"].definir_valor(f"{info['cpu']}{sufixo_cpu}")

        ram_total = info.get("ram_total_gb")
        ram_livre = info.get("ram_livre_gb")
        if ram_total is not None:
            self.cards["ram"].definir_valor(f"{_fmt_gb(ram_livre)} livres de {_fmt_gb(ram_total)}")
        else:
            self.cards["ram"].definir_valor("Indisponível", cor=COR_AVISO)

        self.cards["so"].definir_valor(
            f"{info['sistema_operacional']} ({info['arquitetura']}) — build {info['build']}"
        )
        self.cards["uptime"].definir_valor(info.get("uptime", "Indisponível"))
        self.cards["fabricante"].definir_valor(f"{info['fabricante']} — {info['modelo']}")
        self.cards["bios"].definir_valor(f"{info['bios_versao']} ({info['bios_data']})")
        self.cards["placa_mae"].definir_valor(
            f"{info['placa_mae_fabricante']} {info['placa_mae_modelo']}"
        )
        gpus = info.get("gpu") or ["Indisponível"]
        self.cards["gpu"].definir_valor(" / ".join(gpus))

        self._montar_discos(info.get("discos") or [])

    def _montar_discos(self, discos: list):
        self._limpar(self.frame_discos)
        if not discos:
            self._label_status(self.frame_discos, "Nenhum disco encontrado.")
            return
        for disco in discos:
            linha = ttk.Frame(self.frame_discos)
            linha.pack(fill="x", pady=3)
            tamanho = _fmt_gb(disco.get("tamanho_gb"))
            texto = f"\U0001F4BD  {disco['modelo']}  —  {tamanho}  —  {disco['tipo']}"
            ttk.Label(linha, text=texto, style="Status.TLabel").pack(anchor="w")

    # ==================== Segurança (Fase 4) ====================
    def _aplicar_seguranca(self, info: dict):
        if self._destruida or not self.winfo_exists():
            return
        self._limpar(self.frame_seguranca)

        if "erro" in info:
            self._label_status(self.frame_seguranca, f"Erro: {info['erro']}", cor=COR_ERRO)
            return

        linhas = []

        if info["defender_disponivel"]:
            ativo = bool(info.get("defender_tempo_real"))
            data = info.get("defender_definicoes_data")
            detalhe = f" — definições de {data}" if data else ""
            linhas.append((
                "Windows Defender",
                "Proteção em tempo real ativada" + detalhe if ativo else "Proteção em tempo real DESATIVADA" + detalhe,
                COR_OK if ativo else COR_AVISO,
            ))
        else:
            linhas.append(("Windows Defender", "Não foi possível consultar (pode estar substituído por outro antivírus)", COR_TEXTO_FRACO))

        if info["bitlocker_disponivel"]:
            status = (info.get("bitlocker_status") or "").lower()
            ligado = "on" in status
            pct = info.get("bitlocker_percentual")
            detalhe = f" ({pct}% criptografado)" if pct is not None and not ligado else ""
            linhas.append((
                "BitLocker (unidade do sistema)",
                "Ativado" + (f" ({pct}%)" if pct is not None else "") if ligado else "Desativado" + detalhe,
                COR_OK if ligado else COR_AVISO,
            ))
        else:
            linhas.append(("BitLocker", "Não disponível nesta edição do Windows (recurso exclusivo do Pro/Enterprise/Education)", COR_TEXTO_FRACO))

        if info.get("tpm_presente"):
            habilitado = bool(info.get("tpm_habilitado"))
            linhas.append((
                "TPM (Módulo de Plataforma Confiável)",
                "Presente e habilitado" if habilitado else "Presente, mas desabilitado",
                COR_OK if habilitado else COR_AVISO,
            ))
        else:
            linhas.append(("TPM", "Nenhum chip TPM foi detectado neste computador", COR_TEXTO_FRACO))

        if info["secureboot_disponivel"]:
            ativo = bool(info.get("secureboot_ativo"))
            linhas.append(("Secure Boot", "Ativado" if ativo else "Desativado", COR_OK if ativo else COR_AVISO))
        else:
            linhas.append(("Secure Boot", "Não disponível (o computador pode estar usando BIOS legado em vez de UEFI)", COR_TEXTO_FRACO))

        for titulo, texto, cor in linhas:
            linha_frame = ttk.Frame(self.frame_seguranca)
            linha_frame.pack(fill="x", pady=3)
            ttk.Label(linha_frame, text=f"{titulo}:", style="Status.TLabel").pack(side="left")
            ttk.Label(linha_frame, text=f"  {texto}", style="Status.TLabel", foreground=cor).pack(side="left")

    # ==================== Rede (Fase 4) ====================
    def _aplicar_rede(self, info: dict):
        if self._destruida or not self.winfo_exists():
            return
        self._limpar(self.frame_rede)

        if "erro" in info:
            self._label_status(self.frame_rede, f"Erro: {info['erro']}", cor=COR_ERRO)
            return

        principal = info.get("principal")
        if principal:
            dns_txt = ", ".join(principal["dns"]) if principal["dns"] else "Não disponível"
            for rotulo, valor in [
                ("Adaptador ativo", principal["adaptador"]),
                ("Endereço IP", principal["ip"]),
                ("Gateway", principal["gateway"]),
                ("DNS", dns_txt),
            ]:
                linha = ttk.Frame(self.frame_rede)
                linha.pack(fill="x", pady=2)
                ttk.Label(linha, text=f"{rotulo}:", style="Status.TLabel").pack(side="left")
                ttk.Label(linha, text=f"  {valor}", style="Status.TLabel", foreground=COR_TEXTO).pack(side="left")
        else:
            self._label_status(self.frame_rede, "Nenhuma conexão de rede ativa foi encontrada.", cor=COR_AVISO)

        adaptadores = info.get("adaptadores") or []
        if adaptadores:
            ttk.Label(self.frame_rede, text="Adaptadores:", style="Status.TLabel").pack(anchor="w", pady=(10, 2))
            for a in adaptadores:
                cor = COR_OK if a["status"].lower() == "up" else COR_TEXTO_FRACO
                texto = f"  • {a['nome']} — {a['status']} — {a['mac']} — {a['velocidade']}"
                ttk.Label(self.frame_rede, text=texto, style="Status.TLabel", foreground=cor).pack(anchor="w")

    # ==================== Hardware (Fase 4) ====================
    def _aplicar_hardware(self, info: dict):
        if self._destruida or not self.winfo_exists():
            return

        cpu = info.get("cpu_percentual")
        self.card_cpu.definir_valor(f"{cpu}%" if cpu is not None else "Indisponível",
                                     cor=self._cor_uso(cpu))

        ram = info.get("ram_percentual")
        self.card_ram.definir_valor(f"{ram}%" if ram is not None else "Indisponível",
                                     cor=self._cor_uso(ram))

        self._limpar(self.frame_disco_uso_linhas)
        discos = info.get("discos") or []
        if not discos:
            tk.Label(self.frame_disco_uso_linhas, text="Indisponível", bg=COR_BG_CARD,
                     fg=COR_TEXTO_FRACO, font=("Segoe UI", 9)).pack(anchor="w")
            return
        for d in discos:
            if "erro" in d:
                texto = f"{d['unidade']}: erro"
                cor = COR_ERRO
            else:
                pct = round(d["pct_usado"])
                texto = f"{d['unidade']} {pct}%"
                cor = self._cor_uso(pct)
            tk.Label(self.frame_disco_uso_linhas, text=texto, bg=COR_BG_CARD, fg=cor,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")

    def _cor_uso(self, percentual):
        if percentual is None:
            return COR_TEXTO_FRACO
        if percentual >= 90:
            return COR_ERRO
        if percentual >= 70:
            return COR_AVISO
        return COR_OK

    # ==================== Processos (Fase 4) ====================
    def _aplicar_processos(self, info: dict):
        if self._destruida or not self.winfo_exists():
            return
        self._limpar(self.frame_processos)

        if "erro" in info:
            self._label_status(self.frame_processos, f"Erro: {info['erro']}", cor=COR_ERRO)
            return

        colunas = ttk.Frame(self.frame_processos)
        colunas.pack(fill="x")
        colunas.columnconfigure(0, weight=1, uniform="proc")
        colunas.columnconfigure(1, weight=1, uniform="proc")

        col_cpu = ttk.Frame(colunas)
        col_cpu.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(col_cpu, text="Mais CPU (tempo de processador)", style="Status.TLabel").pack(anchor="w", pady=(0, 4))
        top_cpu = info.get("top_cpu") or []
        if not top_cpu:
            ttk.Label(col_cpu, text="Nenhum processo encontrado.", style="Status.TLabel").pack(anchor="w")
        for p in top_cpu:
            texto = f"{p['nome']} (PID {p['pid']}) — {p['cpu_segundos']}s"
            ttk.Label(col_cpu, text=texto, style="Status.TLabel").pack(anchor="w")

        col_ram = ttk.Frame(colunas)
        col_ram.grid(row=0, column=1, sticky="nsew")
        ttk.Label(col_ram, text="Mais memória RAM", style="Status.TLabel").pack(anchor="w", pady=(0, 4))
        top_ram = info.get("top_ram") or []
        if not top_ram:
            ttk.Label(col_ram, text="Nenhum processo encontrado.", style="Status.TLabel").pack(anchor="w")
        for p in top_ram:
            texto = f"{p['nome']} (PID {p['pid']}) — {p['ram_mb']:.1f} MB".replace(".", ",", 1)
            ttk.Label(col_ram, text=texto, style="Status.TLabel").pack(anchor="w")