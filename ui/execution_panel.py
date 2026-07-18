# ==========================================================
# Arquivo: ui/execution_panel.py
# Responsabilidade: Painel de execução em lote — mostra de
# forma visual qual tarefa está rodando, quais já terminaram,
# progresso geral (contagem de tarefas do lote) e tempo
# decorrido. Além disso, a barra de progresso DA TAREFA em si
# opera em dois modos, decididos a partir das capacidades que
# cada tarefa declara (ver utils/tasks.py):
#
#   - DETERMINADO: a tarefa informa percentual oficial (ex.: limpeza
#     de TEMP) — a barra mostra exatamente esse valor.
#   - INDETERMINADO: a tarefa não tem percentual possível (ex.: DNS,
#     Lixeira, CHKDSK, SFC, DISM — estes dois últimos porque rodam
#     num Prompt de Comando real e visível, sem nenhuma captura de
#     saída) — a barra usa o modo "marquee" do próprio
#     ttk.Progressbar, sem jamais simular um número.
#
# A escolha do modo é decidida de DUAS formas complementares:
#   1) proativamente, pelo evento 'capacidades' emitido no início de
#      cada tarefa (via definir_capacidades) — cobre o caso comum e
#      permite entrar em modo indeterminado ANTES de qualquer valor
#      chegar, para tarefas que nunca fornecem percentual;
#   2) reativamente, pela própria chegada de um percentual real (via
#      definir_percentual_tarefa) — como só tarefas com
#      progresso_real=True chamam reporter.progress() com um número,
#      a chegada desse valor já é prova suficiente do modo determinado.
#      Isso torna a barra resiliente a uma eventual perda do evento
#      'capacidades' por condição de corrida entre o início da thread
#      de execução (ExecutionManager.iniciar) e o registro do listener
#      desta tela (ui/main_window.py) — sem exigir nenhuma mudança na
#      arquitetura de eventos do ExecutionManager.
#
# Este painel é uma VIEW pura: ele não é dono do estado da
# execução (isso vive em core/execution/execution_manager.py). Ele
# só sabe desenhar o que recebe:
#   - exibir_estado(snapshot)  -> popula tudo de uma vez (usado ao
#     abrir/reabrir a tela, inclusive com a execução já em andamento)
#   - marcar_estado / definir_progresso / definir_tarefa_atual /
#     definir_capacidades / definir_percentual_tarefa /
#     definir_ultima_mensagem / finalizar -> atualizações
#     incrementais, aplicadas pela tela conforme os eventos do
#     ExecutionManager chegam.
# Por ser só uma view, este painel pode ser destruído (ao trocar de
# categoria na sidebar) e recriado (ao voltar) sem que a execução em
# si seja afetada.
#
# SEM CONSOLE INTERNO: este painel não desenha mais um console de
# texto. Tarefas que precisam de acompanhamento visual em tempo real
# (SFC, DISM) abrem um terminal Administrador REAL do Windows (ver
# utils/helpers.py:_executar_com_terminal_real) — o Windows cuida da
# renderização dessa saída, fora deste painel. O que continua
# aparecendo aqui é só o que sempre foi responsabilidade deste
# painel: status, barras de progresso, última mensagem e lista de
# etapas. reporter.log()/ExecutionManager.escrever_log() continuam
# existindo (útil para histórico interno/depuração), só não são mais
# desenhados em nenhum widget.
# ==========================================================

import time
import tkinter as tk
from tkinter import ttk

from utils.constants import (
    COR_BG, COR_TEXTO_FRACO, COR_ACCENT, COR_OK, COR_ERRO,
)
from core.execution.execution_manager import PENDENTE, EXECUTANDO, CONCLUIDA, ERRO, RODANDO, FINALIZADO

_ICONE_ESTADO = {
    PENDENTE: ("\u25CB", COR_TEXTO_FRACO),
    EXECUTANDO: ("\u27A4", COR_ACCENT),
    CONCLUIDA: ("\u2714", COR_OK),
    ERRO: ("\u2716", COR_ERRO),
}


def _formatar_percentual(valor: float) -> str:
    """Formata o percentual real recebido, no padrão pt-BR (vírgula),
    sem casas decimais desnecessárias (ex.: 35 -> '35%', 35.5 -> '35,5%')."""
    if float(valor).is_integer():
        return f"{int(valor)}%"
    return f"{valor:.1f}%".replace(".", ",")


class ExecutionPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._linhas = {}
        self._inicio_epoch = None
        self._tick_job = None
        self._percentual_visivel = False
        self._modo_progresso = None  # None | "determinado" | "indeterminado"
        self._montar()
        # Garante que o relógio pare de se reagendar se este painel for
        # destruído (ex.: usuário navegou para outra categoria) — evita
        # um `after` pendente tentando atualizar um widget morto.
        self.bind("<Destroy>", self._ao_destruir)

    def _montar(self):
        cabecalho = ttk.Frame(self)
        cabecalho.pack(fill="x", pady=(0, 10))
        ttk.Label(cabecalho, text="\u25B6 Execução em andamento", style="TituloSecao.TLabel").pack(anchor="w")
        self.lbl_tarefa_atual = ttk.Label(cabecalho, text="Preparando...", style="Status.TLabel")
        self.lbl_tarefa_atual.pack(anchor="w", pady=(2, 0))

        # ---------- progresso do LOTE (quantas tarefas concluídas) + tempo ----------
        barra_wrap = ttk.Frame(self)
        barra_wrap.pack(fill="x", pady=(6, 4))
        self.progress = ttk.Progressbar(barra_wrap, style="Horizontal.TProgressbar", mode="determinate")
        self.progress.pack(fill="x")

        info_wrap = ttk.Frame(self)
        info_wrap.pack(fill="x", pady=(6, 6))
        self.lbl_contagem = ttk.Label(info_wrap, text="0 / 0 concluídas", style="Status.TLabel")
        self.lbl_contagem.pack(side="left")
        self.lbl_tempo = ttk.Label(info_wrap, text="00:00 decorrido", style="Status.TLabel")
        self.lbl_tempo.pack(side="right")

        # ---------- progresso da TAREFA ATUAL (determinado ou indeterminado) ----------
        # Só é "packado" (mostrado) a partir do evento 'capacidades' ou
        # da chegada do primeiro percentual real — ver
        # _mostrar_wrap_percentual().
        self.percentual_wrap = ttk.Frame(self)
        pct_topo = ttk.Frame(self.percentual_wrap)
        pct_topo.pack(fill="x")
        ttk.Label(pct_topo, text="Progresso da tarefa", style="Status.TLabel").pack(side="left")
        self.lbl_percentual_valor = ttk.Label(pct_topo, text="", style="Status.TLabel")
        self.lbl_percentual_valor.pack(side="right")
        self.progress_tarefa = ttk.Progressbar(
            self.percentual_wrap, style="Horizontal.TProgressbar",
            mode="determinate", maximum=100,
        )
        self.progress_tarefa.pack(fill="x", pady=(4, 0))
        # Não chama pack() no percentual_wrap aqui — só a partir de
        # _mostrar_wrap_percentual(), quando sabemos que uma tarefa
        # começou (por capacidades ou por percentual real chegando).

        # ---------- última mensagem recebida ----------
        ultima_wrap = ttk.Frame(self)
        ultima_wrap.pack(fill="x", pady=(10, 14))
        ttk.Label(ultima_wrap, text="Última mensagem:", style="Status.TLabel").pack(side="left")
        self.lbl_ultima_mensagem = ttk.Label(
            ultima_wrap, text="—", style="Status.TLabel",
        )
        self.lbl_ultima_mensagem.pack(side="left", padx=(6, 0))

        # ---------- lista de etapas ----------
        self.lista_etapas = tk.Frame(self, bg=COR_BG)
        self.lista_etapas.pack(fill="x")

    # -------------------- população a partir do estado do ExecutionManager --------------------
    def exibir_estado(self, snapshot: dict):
        """Popula o painel inteiro a partir de um snapshot do
        ExecutionManager. Usado sempre que esta tela é (re)aberta —
        inclusive quando a execução já começou antes desta instância
        do painel existir (ex.: usuário voltou de outra categoria)."""
        for w in self.lista_etapas.winfo_children():
            w.destroy()
        self._linhas = {}

        total = snapshot["total"]
        self.progress.config(maximum=max(total, 1), value=snapshot["concluidas"])
        self.lbl_contagem.config(text=f"{snapshot['concluidas']} / {total} concluídas")
        self.lbl_tarefa_atual.config(text=snapshot["tarefa_atual_texto"])

        titulos = snapshot["titulos_por_chave"]
        for chave in snapshot["ordem_chaves"]:
            titulo = titulos.get(chave, chave)
            self._linhas[chave] = self._criar_linha_etapa(titulo)
            estado = snapshot["estados_tarefa"].get(chave, PENDENTE)
            self.marcar_estado(chave, estado)

        if snapshot["status"] == RODANDO:
            self.definir_capacidades(snapshot.get("capacidades_tarefa_atual", {}))
            self.definir_percentual_tarefa(snapshot.get("percentual_tarefa_atual"))
        self.definir_ultima_mensagem(snapshot.get("ultima_mensagem", ""))

        self._inicio_epoch = snapshot["inicio_epoch"]
        if snapshot["status"] == FINALIZADO:
            # Execução já terminou: mostra o tempo total parado, sem
            # reagendar o relógio, e sem barra de tarefa (não há
            # tarefa "atual" mais).
            if snapshot["inicio_epoch"] and snapshot["fim_epoch"]:
                decorrido = int(snapshot["fim_epoch"] - snapshot["inicio_epoch"])
                m, s = divmod(decorrido, 60)
                self.lbl_tempo.config(text=f"{m:02d}:{s:02d} decorrido")
        else:
            self._atualizar_relogio()

    # -------------------- atualizações incrementais (via eventos) --------------------
    def marcar_estado(self, chave, estado):
        if chave not in self._linhas:
            return
        icone_lbl, _titulo_lbl = self._linhas[chave]
        simbolo, cor = _ICONE_ESTADO[estado]
        icone_lbl.config(text=simbolo, fg=cor)

    def definir_tarefa_atual(self, texto):
        self.lbl_tarefa_atual.config(text=texto)

    def definir_progresso(self, concluidas, total):
        self.progress.config(maximum=max(total, 1), value=concluidas)
        self.lbl_contagem.config(text=f"{concluidas} / {total} concluídas")

    def definir_capacidades(self, capacidades: dict):
        """Chamado no início de CADA tarefa (evento 'capacidades'),
        antes de qualquer percentual chegar. Decide, a partir do que a
        tarefa declara ser capaz de fornecer, se a barra desta tarefa
        será determinada (percentual real) ou indeterminada.

        Esse evento pode, em teoria, ser perdido por uma corrida entre
        o início da thread de execução (ExecutionManager.iniciar) e o
        registro do listener desta tela (ui/main_window.py). Por isso
        ele NÃO é a única fonte de verdade para o modo determinado —
        ver definir_percentual_tarefa, que se autocorrige a partir do
        primeiro valor real recebido, mesmo que este evento nunca
        chegue a esta instância do painel."""
        self._mostrar_wrap_percentual()

        if capacidades.get("progresso_real"):
            self._definir_modo_determinado()
        else:
            self._definir_modo_indeterminado()

    def _mostrar_wrap_percentual(self):
        if not self._percentual_visivel:
            self.percentual_wrap.pack(fill="x", pady=(4, 0), before=self.lbl_ultima_mensagem.master)
            self._percentual_visivel = True

    def _definir_modo_determinado(self):
        if self._modo_progresso == "determinado":
            return
        self._parar_marquee()
        self.progress_tarefa.config(mode="determinate", maximum=100, value=0)
        self.lbl_percentual_valor.config(text="0%")
        self._modo_progresso = "determinado"

    def _definir_modo_indeterminado(self):
        if self._modo_progresso == "indeterminado":
            return
        self._parar_marquee()
        self.progress_tarefa.config(mode="indeterminate")
        self.progress_tarefa.start(12)
        self.lbl_percentual_valor.config(text="Em andamento…")
        self._modo_progresso = "indeterminado"

    def _parar_marquee(self):
        try:
            self.progress_tarefa.stop()
        except Exception:
            pass

    def definir_percentual_tarefa(self, valor):
        """valor: percentual REAL (0-100) vindo da própria tarefa, ou
        None (nenhum valor novo no momento).

        Robustez contra perda do evento 'capacidades': em vez de
        depender exclusivamente de definir_capacidades já ter sido
        chamado antes para aceitar este valor, tratamos a própria
        chegada de um percentual numérico como evidência suficiente de
        que a tarefa é determinada — só tarefas com progresso_real=True
        chamam reporter.progress() com um número (ver
        utils/tasks.py e core/execution/reporter.py).
        Isso garante que a barra sempre acompanhe o percentual real,
        mesmo que o evento 'capacidades' desta execução tenha sido
        perdido por uma condição de corrida na inscrição do listener."""
        if valor is None:
            return
        self._mostrar_wrap_percentual()
        if self._modo_progresso != "determinado":
            self._definir_modo_determinado()
        self.progress_tarefa.config(value=valor)
        self.lbl_percentual_valor.config(text=_formatar_percentual(valor))

    def definir_ultima_mensagem(self, texto):
        self.lbl_ultima_mensagem.config(text=texto if texto else "—")

    def finalizar(self):
        self.lbl_tarefa_atual.config(text="Concluído")
        self._parar_marquee()
        if self._percentual_visivel:
            self.percentual_wrap.pack_forget()
            self._percentual_visivel = False
        self._modo_progresso = None
        if self._tick_job:
            self.after_cancel(self._tick_job)
            self._tick_job = None

    def _criar_linha_etapa(self, titulo):
        linha = tk.Frame(self.lista_etapas, bg=COR_BG)
        linha.pack(fill="x", pady=3)
        simbolo, cor = _ICONE_ESTADO[PENDENTE]
        icone_lbl = tk.Label(linha, text=simbolo, bg=COR_BG, fg=cor, font=("Segoe UI", 10, "bold"), width=2)
        icone_lbl.pack(side="left")
        titulo_lbl = tk.Label(linha, text=titulo, bg=COR_BG, fg=COR_TEXTO_FRACO, font=("Segoe UI", 9))
        titulo_lbl.pack(side="left", padx=(4, 0))
        return icone_lbl, titulo_lbl

    def _atualizar_relogio(self):
        if self._inicio_epoch is None:
            return
        decorrido = int(time.time() - self._inicio_epoch)
        m, s = divmod(decorrido, 60)
        self.lbl_tempo.config(text=f"{m:02d}:{s:02d} decorrido")
        self._tick_job = self.after(1000, self._atualizar_relogio)

    def _ao_destruir(self, _evento=None):
        self._parar_marquee()
        if self._tick_job:
            try:
                self.after_cancel(self._tick_job)
            except Exception:
                pass
            self._tick_job = None