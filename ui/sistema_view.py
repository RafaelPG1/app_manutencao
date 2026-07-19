# ==========================================================
# Arquivo: ui/sistema_view.py
# Responsabilidade: Tela da categoria Sistema — informações do
# computador (CPU, RAM, SO, fabricante/modelo, BIOS, placa-mãe,
# uptime, discos, GPU). Tela PURAMENTE INFORMATIVA, sem checkbox nem
# execução em lote — por isso não usa TaskView, e sim uma view
# própria, no mesmo espírito de ui/dashboard.py (que também é
# informativo e não passa pelo ExecutionManager).
#
# A consulta ao sistema (core/sistema/system_info.py) usa PowerShell
# e pode levar alguns segundos — roda em uma thread de segundo plano,
# igual ao padrão já usado por ui/main_window.py para detectar o tipo
# de disco (_detectar_disco_thread) e consultar o espaço livre
# (_consultar_espaco_thread), incluindo a mesma checagem de
# `winfo_exists()` antes de tocar em qualquer widget, para o caso de
# o usuário trocar de categoria antes da consulta terminar.
# ==========================================================

import threading
from tkinter import ttk

from utils.constants import COR_ERRO, COR_AVISO
from core.sistema.system_info import obter_informacoes_sistema
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
        threading.Thread(target=self._consultar_thread, daemon=True).start()

    def _ao_destruir(self, _evento=None):
        self._destruida = True

    def _montar(self):
        criar_cabecalho_secao(
            self, "\U0001F5A5", "Sistema",
            "Informações do computador — consultado via WMI/CIM oficial do Windows",
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
        self.lbl_discos_status = ttk.Label(self.frame_discos, text="Consultando...", style="Status.TLabel")
        self.lbl_discos_status.pack(anchor="w")

    # -------------------- consulta em segundo plano --------------------
    def _consultar_thread(self):
        info = obter_informacoes_sistema()
        if self.app and self.app.root:
            self.app.root.after(0, lambda: self._aplicar(info))

    def _aplicar(self, info: dict):
        if self._destruida or not self.winfo_exists():
            return

        if "erro" in info:
            for card in self.cards.values():
                card.definir_valor("Erro ao consultar", cor=COR_ERRO)
            self.lbl_discos_status.config(text=f"Erro: {info['erro']}", foreground=COR_ERRO)
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
        for w in self.frame_discos.winfo_children():
            w.destroy()

        if not discos:
            ttk.Label(self.frame_discos, text="Nenhum disco encontrado.", style="Status.TLabel").pack(anchor="w")
            return

        for disco in discos:
            linha = ttk.Frame(self.frame_discos)
            linha.pack(fill="x", pady=3)
            tamanho = _fmt_gb(disco.get("tamanho_gb"))
            texto = f"\U0001F4BD  {disco['modelo']}  —  {tamanho}  —  {disco['tipo']}"
            ttk.Label(linha, text=texto, style="Status.TLabel").pack(anchor="w")
