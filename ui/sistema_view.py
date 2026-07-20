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
# ==========================================================

import threading
import tkinter as tk
from tkinter import ttk

from utils.constants import COR_BG_CARD, COR_BORDA, COR_TEXTO, COR_TEXTO_FRACO, COR_OK, COR_AVISO, COR_ERRO
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

        for alvo in (
            self._consultar_thread, self._consultar_seguranca_thread,
            self._consultar_rede_thread, self._consultar_hardware_thread,
            self._consultar_processos_thread,
        ):
            threading.Thread(target=alvo, daemon=True).start()

    def _ao_destruir(self, _evento=None):
        self._destruida = True

    def _apos(self, callback):
        """Agenda `callback` na thread principal, só se a view ainda
        existir — mesmo guard usado em todas as 5 consultas desta
        tela."""
        if not self._destruida and self.app and self.app.root:
            self.app.root.after(0, callback)

    # ==================== Montagem ====================
    def _montar(self):
        criar_cabecalho_secao(
            self, "\U0001F5A5", "Sistema",
            "Informações do computador — consultado via WMI/CIM/PowerShell oficial do Windows",
        )

        grade = ttk.Frame(self)
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

        criar_cabecalho_secao(self, "\U0001F4BD", "Discos instalados")
        self.frame_discos = ttk.Frame(self)
        self.frame_discos.pack(fill="x")
        self._label_status(self.frame_discos, "Consultando...")

        # -------- Fase 4 --------
        criar_cabecalho_secao(self, "\U0001F512", "Segurança")
        self.frame_seguranca = ttk.Frame(self)
        self.frame_seguranca.pack(fill="x")
        self._label_status(self.frame_seguranca, "Consultando...")

        criar_cabecalho_secao(self, "\U0001F310", "Rede")
        self.frame_rede = ttk.Frame(self)
        self.frame_rede.pack(fill="x")
        self._label_status(self.frame_rede, "Consultando...")

        criar_cabecalho_secao(self, "\U0001F4CA", "Uso de hardware")
        grade_hw = ttk.Frame(self)
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

        criar_cabecalho_secao(self, "\U0001F4C8", "Processos que mais consomem")
        self.frame_processos = ttk.Frame(self)
        self.frame_processos.pack(fill="x")
        self._label_status(self.frame_processos, "Consultando...")

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
    def _consultar_thread(self):
        info = obter_informacoes_sistema()
        self._apos(lambda: self._aplicar(info))

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
    def _consultar_seguranca_thread(self):
        info = obter_status_seguranca()
        self._apos(lambda: self._aplicar_seguranca(info))

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
    def _consultar_rede_thread(self):
        info = obter_informacoes_rede()
        self._apos(lambda: self._aplicar_rede(info))

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
    def _consultar_hardware_thread(self):
        info = obter_uso_hardware()
        self._apos(lambda: self._aplicar_hardware(info))

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
    def _consultar_processos_thread(self):
        info = obter_processos_top()
        self._apos(lambda: self._aplicar_processos(info))

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