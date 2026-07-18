# ==========================================================
# Arquivo: core/execution/reporter.py
# Responsabilidade: Camada intermediária entre os módulos de core/
# e o estado de execução (ExecutionManager). Nenhum módulo de core/
# conhece o ExecutionManager por trás, widgets do Tkinter, ou
# qualquer detalhe de interface — cada tarefa recebe apenas um
# TaskReporter e chama seus métodos para informar o que está
# REALMENTE acontecendo.
#
# TaskReporter não guarda estado algum: ele só encaminha cada chamada
# para o ExecutionManager (que continua sendo o único dono do
# estado), já identificado por sua chave de tarefa. Existe para dar
# às funções de core/ uma interface pequena e estável — um objeto só
# — em vez de cada uma receber uma lista solta e crescente de
# callbacks (escrever, definir_percentual, definir_mensagem, ...).
# ==========================================================


class TaskReporter:
    """Interface que uma tarefa usa para relatar seu progresso real.

    log(texto, tag=None)  -> escreve no console detalhado
    progress(valor)       -> percentual REAL (0-100) vindo da própria
                              ferramenta/loop, ou None para indicar
                              "sem valor novo no momento". Tarefas que
                              nunca têm percentual simplesmente nunca
                              chamam isto — a UI já sabe disso através
                              das capacidades declaradas.
    message(texto)        -> última linha de saída relevante, exibida
                              como resumo do que está acontecendo agora
    warning(texto) / error(texto) -> atalhos de log com a tag certa
    """

    def __init__(self, execution_manager, chave: str):
        self._manager = execution_manager
        self._chave = chave

    @property
    def chave(self) -> str:
        return self._chave

    def log(self, texto: str, tag=None):
        self._manager.escrever_log(texto, tag)

    def progress(self, valor):
        self._manager.definir_percentual(valor)

    def message(self, texto: str):
        self._manager.definir_mensagem(texto)

    def warning(self, texto: str):
        self._manager.escrever_log(texto, "aviso")

    def error(self, texto: str):
        self._manager.escrever_log(texto, "erro")