# ==========================================================
# Arquivo: core/execution/execution_manager.py
# Responsabilidade: Controlador GLOBAL da execução em lote das
# tarefas selecionadas. Mantém todo o estado da execução (fila,
# progresso, tarefa atual, log, tempo decorrido) de forma
# independente da interface gráfica.
#
# A execução roda em uma thread de segundo plano e NÃO depende de
# nenhum widget do Tkinter estar vivo. As telas da interface apenas
# OBSERVAM esse estado através de listeners (padrão observer) — elas
# podem ser criadas, destruídas e recriadas livremente (ex.: ao
# navegar entre categorias na sidebar) sem afetar a execução em si.
#
# Nenhuma lógica de negócio das tarefas foi movida para cá: este
# módulo apenas chama, na ordem escolhida pelo usuário, as funções já
# existentes em core/<dominio>/ (dism.py, sfc.py, chkdsk.py etc.) —
# que permanecem exatamente como estavam em termos de COMANDO. A
# única mudança é que cada tarefa agora recebe um único TaskReporter
# (ver core/execution/reporter.py) em vez de vários callbacks soltos.
#
# CAPACIDADES: no início de cada tarefa, o gerenciador consulta
# utils/tasks.py (fonte única de verdade dos metadados de tarefa) para
# saber o que aquela tarefa É CAPAZ de fornecer (percentual real, log
# em tempo real, etc.) e notifica a UI através do evento 'capacidades'
# — a UI decide sozinha o que mostrar a partir disso, sem verificar
# tarefa por tarefa.
# ==========================================================

import threading
import time

from utils.helpers import agora
from utils.logger import LOGFILE, log
from utils.tasks import capacidades_de, CAPACIDADES_PADRAO, tarefa_por_chave
from core.execution.reporter import TaskReporter

# Estados possíveis de cada tarefa individual dentro do lote.
PENDENTE, EXECUTANDO, CONCLUIDA, ERRO = "pendente", "executando", "concluida", "erro"

# Estados possíveis da execução em lote como um todo.
OCIOSO, RODANDO, FINALIZADO = "ocioso", "rodando", "finalizado"


class ExecutionManager:
    """Dono único do estado de uma execução em lote.

    Garante, por construção, que exista no máximo UMA execução em
    andamento por vez: `iniciar()` recusa (retorna False) qualquer
    tentativa de início enquanto o status já for RODANDO.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._listeners = []
        self._resetar_estado()

    def _resetar_estado(self):
        self.status = OCIOSO
        self.titulos_por_chave = {}
        self.ordem_chaves = []
        self.estados_tarefa = {}
        self.tarefa_atual_texto = "Preparando..."
        self.concluidas = 0
        self.total = 0
        self.inicio_epoch = None
        self.fim_epoch = None
        self.log_historico = []  # lista de (texto, tag) — permite "replay" ao reabrir a tela

        # Progresso REAL dentro da tarefa atual (não simulado). None
        # significa "ainda sem valor novo" — o significado disso para a
        # UI depende do modo determinado/indeterminado (ver capacidades).
        self.percentual_tarefa_atual = None
        # Última linha de saída recebida da tarefa atual (string vazia
        # quando ainda não há nenhuma).
        self.ultima_mensagem = ""
        # O que a tarefa atual declara ser capaz de fornecer (ver
        # utils/tasks.py). Populado a cada início de tarefa dentro de
        # _executar_lote.
        self.capacidades_tarefa_atual = dict(CAPACIDADES_PADRAO)

    # -------------------- Observadores (padrão observer) --------------------
    def adicionar_listener(self, callback):
        """callback(evento: str, dados: dict) é chamado a cada mudança de
        estado, a partir da MESMA thread que gerou o evento (pode ser a
        thread de execução em segundo plano). Quem escuta e precisa
        atualizar widgets Tkinter é responsável por despachar para a
        thread principal (ex.: via `root.after(0, ...)`).

        Eventos emitidos: 'iniciado', 'log', 'progresso',
        'estado_tarefa', 'tarefa_atual', 'capacidades', 'percentual',
        'mensagem', 'finalizado'.
        """
        self._listeners.append(callback)

    def remover_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notificar(self, evento, **dados):
        for callback in list(self._listeners):
            try:
                callback(evento, dados)
            except Exception as e:
                log(f"[EXECUTION_MANAGER] Erro em listener ({evento}): {e}")

    # -------------------- Consulta de estado --------------------
    def esta_rodando(self) -> bool:
        return self.status == RODANDO

    def obter_reporter(self, chave: str) -> TaskReporter:
        """Cria o TaskReporter que será passado à função da tarefa
        `chave`. Pode ser chamado a qualquer momento — inclusive antes
        de iniciar() — pois o reporter não guarda estado, só encaminha
        chamadas para este ExecutionManager."""
        return TaskReporter(self, chave)

    def obter_snapshot(self):
        """Retorna uma cópia do estado atual. Usado por uma tela de
        execução recém-(re)aberta para se popular imediatamente com
        tudo que já aconteceu, antes de passar a receber apenas os
        eventos incrementais seguintes via listener."""
        with self._lock:
            return {
                "status": self.status,
                "titulos_por_chave": dict(self.titulos_por_chave),
                "ordem_chaves": list(self.ordem_chaves),
                "estados_tarefa": dict(self.estados_tarefa),
                "tarefa_atual_texto": self.tarefa_atual_texto,
                "concluidas": self.concluidas,
                "total": self.total,
                "inicio_epoch": self.inicio_epoch,
                "fim_epoch": self.fim_epoch,
                "log_historico": list(self.log_historico),
                "percentual_tarefa_atual": self.percentual_tarefa_atual,
                "ultima_mensagem": self.ultima_mensagem,
                "capacidades_tarefa_atual": dict(self.capacidades_tarefa_atual),
            }

    # -------------------- Início da execução --------------------
    def iniciar(self, titulos_por_chave: dict, ordem_chaves: list, mapa_funcoes: dict) -> bool:
        """Tenta iniciar uma nova execução em lote.

        Retorna True se a execução foi iniciada, ou False se já havia
        uma execução em andamento (nesse caso, nada é alterado e
        nenhuma thread nova é criada — garante uma execução por vez,
        mesmo em caso de cliques concorrentes)."""
        with self._lock:
            if self.status == RODANDO:
                return False
            self._resetar_estado()
            self.status = RODANDO
            self.titulos_por_chave = dict(titulos_por_chave)
            self.ordem_chaves = list(ordem_chaves)
            self.estados_tarefa = {chave: PENDENTE for chave in ordem_chaves}
            self.total = len(ordem_chaves)
            self.inicio_epoch = time.time()

        self._notificar("iniciado")
        self.escrever_log(f"[INFO] Log salvo em: {LOGFILE}\n", "fraco")
        threading.Thread(target=self._executar_lote, args=(mapa_funcoes,), daemon=True).start()
        return True

    # -------------------- Atualizações de estado (usadas durante a execução) --------------------
    def escrever_log(self, texto: str, tag=None):
        """Callback compatível com a assinatura `escrever(texto, tag)`
        já usada pelas rotinas existentes em core/ — chamado agora
        através de TaskReporter.log()."""
        with self._lock:
            self.log_historico.append((texto, tag))
        self._notificar("log", texto=texto, tag=tag)

    def definir_tarefa_atual(self, texto: str):
        with self._lock:
            self.tarefa_atual_texto = texto
        self._notificar("tarefa_atual", texto=texto)

    def marcar_estado_tarefa(self, chave: str, estado: str):
        with self._lock:
            self.estados_tarefa[chave] = estado
        self._notificar("estado_tarefa", chave=chave, estado=estado)

    def definir_progresso(self, concluidas: int):
        with self._lock:
            self.concluidas = concluidas
        self._notificar("progresso", concluidas=concluidas, total=self.total)

    def definir_capacidades(self, capacidades: dict):
        """Registra o que a tarefa atual declara ser capaz de fornecer
        (ver utils/tasks.py) e notifica a UI — que decide, a partir
        disso, entre barra determinada e barra indeterminada, ANTES de
        qualquer percentual chegar."""
        dados = dict(capacidades)
        with self._lock:
            self.capacidades_tarefa_atual = dados
        self._notificar("capacidades", capacidades=dict(dados))

    def definir_percentual(self, valor):
        """Progresso REAL (percentual oficial) dentro da tarefa atual.
        `valor` deve ser um número (0-100) vindo diretamente da saída
        ou do loop da própria rotina (ex.: SFC, DISM, limpeza de TEMP),
        ou None para indicar "sem valor novo no momento". Nunca é
        preenchido artificialmente."""
        with self._lock:
            self.percentual_tarefa_atual = valor
        self._notificar("percentual", valor=valor)

    def definir_mensagem(self, texto: str):
        """Última linha de saída real recebida da tarefa atual."""
        with self._lock:
            self.ultima_mensagem = texto
        self._notificar("mensagem", texto=texto)

    # -------------------- Laço principal (roda em thread própria) --------------------
    def _executar_lote(self, mapa_funcoes: dict):
        inicio = agora()
        inicio_epoch_lote = time.time()
        log(f"[SESSAO] Execução em lote iniciada em {inicio} - Tarefas: {self.ordem_chaves}")
        # Linha estruturada para a tela "Histórico" (ver utils/logger.py:
        # ler_historico) — adicional às linhas de texto livre acima, que
        # continuam existindo exatamente como antes.
        log(f"[HISTORICO] LOTE_INICIO | data={inicio} | tarefas={','.join(self.ordem_chaves)}")
        self.escrever_log(
            f"\n{'#'*60}\n### EXECUÇÃO EM LOTE - {self.total} tarefa(s) selecionada(s)\n{'#'*60}\n",
            "titulo"
        )

        try:
            for i, chave in enumerate(self.ordem_chaves, start=1):
                titulo = self.titulos_por_chave.get(chave, chave)
                self.marcar_estado_tarefa(chave, EXECUTANDO)
                self.definir_tarefa_atual(f"[{i}/{self.total}] {titulo}")

                # Declara o que ESTA tarefa é capaz de fornecer antes de
                # qualquer percentual chegar — a UI já monta a barra no
                # modo certo (determinada ou indeterminada) a partir daqui.
                self.definir_capacidades(capacidades_de(chave))

                # Cada tarefa começa "do zero" em termos de progresso
                # real e última mensagem — evita que o percentual de
                # uma tarefa anterior (ex.: SFC) apareça "vazando" na
                # tarefa seguinte (ex.: DNS), que não fornece percentual.
                self.definir_percentual(None)
                self.definir_mensagem("")
                self.escrever_log(f"\n[{i}/{self.total}] \u25B6 {titulo}\n", "titulo")

                inicio_tarefa_epoch = time.time()
                estado_final = CONCLUIDA
                try:
                    mapa_funcoes[chave]()
                except Exception as e:
                    estado_final = ERRO
                    self.escrever_log(f"[ERRO INESPERADO] {e}\n", "erro")
                    log(f"[ERRO INESPERADO] {e}")
                duracao_tarefa = time.time() - inicio_tarefa_epoch

                self.marcar_estado_tarefa(chave, estado_final)
                self.definir_progresso(i)
                log(
                    f"[HISTORICO] TAREFA | chave={chave} | titulo={titulo} "
                    f"| estado={estado_final} | duracao_s={duracao_tarefa:.1f}"
                )
        finally:
            fim = agora()
            duracao_lote = time.time() - inicio_epoch_lote

            # Lembrete de reinicialização DINÂMICO: em vez de uma frase
            # fixa citando só DISM/SFC/CHKDSK (que ficaria incompleta
            # assim que qualquer nova tarefa marcada com
            # requer_reinicializacao=True fosse adicionada — como
            # "Resetar pilha de rede" na Fase 5), verifica de fato quais
            # das tarefas EXECUTADAS neste lote pedem reinicialização,
            # usando o mesmo metadado já declarado em utils/tasks.py.
            tarefas_que_pedem_reinicio = [
                self.titulos_por_chave.get(chave, chave)
                for chave in self.ordem_chaves
                if (tarefa_por_chave(chave) and tarefa_por_chave(chave).requer_reinicializacao)
            ]
            if tarefas_que_pedem_reinicio:
                lembrete = (
                    "Lembrete: reinicie o computador — recomendado após: "
                    + ", ".join(tarefas_que_pedem_reinicio) + ".\n"
                )
            else:
                lembrete = ""

            self.escrever_log(
                f"\n{'#'*60}\n### LOTE FINALIZADO — Início: {inicio}  |  Fim: {fim}\n"
                f"{lembrete}"
                f"{'#'*60}\n", "titulo"
            )
            log(f"[SESSAO] Execução em lote finalizada em {fim}")
            log(f"[HISTORICO] LOTE_FIM | data={fim} | duracao_s={duracao_lote:.1f}")
            log("=" * 55)

            with self._lock:
                self.status = FINALIZADO
                self.fim_epoch = time.time()
                self.tarefa_atual_texto = "Execução concluída"

            self._notificar("tarefa_atual", texto="Execução concluída")
            self._notificar("finalizado")