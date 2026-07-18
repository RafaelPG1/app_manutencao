# ==========================================================
# Arquivo: core/manutencao/dism.py
# Responsabilidade: Rotina de reparo da imagem do Windows via
# DISM (/Online /Cleanup-Image /RestoreHealth).
#
# O DISM roda no Prompt de Comando (cmd.exe) REAL, único e persistente
# do aplicativo, gerenciado exclusivamente por
# core/shared/terminal_manager.py — este módulo não sabe (nem precisa
# saber) como esse CMD é criado, mantido ou recriado; só chama
# terminal.executar(), que devolve o código de saída real do DISM
# somente depois que ele de fato terminou (nunca por suposição — ver
# o cabeçalho de terminal_manager.py).
#
# Esse CMD é o console OFICIAL do aplicativo: toda a saída real do
# DISM (progresso, resultado, "A operação foi concluída com êxito",
# eventuais erros etc.) já aparece nativamente na tela dele. Por isso
# esta rotina NÃO interpreta o código de retorno do DISM — ela só
# registra que a execução terminou e qual foi esse código, para fins
# de log interno. Nenhuma mensagem baseada no valor de `rc` é exibida
# ao usuário aqui, para não duplicar (ou divergir d)o que o próprio
# Windows já mostrou no CMD.
#
# Como qualquer captura de saída exigiria redirecionar/alterar o que
# a tela mostra (o que contraria ter uma saída 100% nativa do
# Windows), esta tarefa não recebe texto linha a linha do DISM — só o
# código de saída real, ao final. Por isso ela é tratada como
# progresso INDETERMINADO (ver utils/tasks.py:
# dism -> progresso_real=False), igual ao CHKDSK.
#
# Recebe um único TaskReporter (core/execution/reporter.py):
#   - message(): status fixo, definido uma vez no início da tarefa;
#   - log(): só os eventos de início e de término da tarefa em si
#     (não é um espelho da saída do DISM, que já aparece nativamente
#     no CMD).
# ==========================================================

from utils.helpers import agora
from utils.logger import log
from core.shared.terminal_manager import terminal, TerminalIndisponivelError

_MENSAGEM_STATUS = "Reparando a imagem do Windows... (acompanhe no Prompt de Comando aberto)"


def executar_dism(reporter):
    """reporter: TaskReporter (ver core/execution/reporter.py) — usado
    para log() de eventos de início/término e message() com um status
    estável.

    A barra de progresso da TAREFA fica no modo indeterminado (a UI
    decide isso sozinha a partir das capacidades declaradas para
    "dism"); a barra do LOTE é responsabilidade do ExecutionManager e
    não é tocada aqui — ela só avança quando esta função retorna.
    """
    reporter.log("[INFO] Iniciando reparo da imagem do Windows...\n", "titulo")
    reporter.log("[INFO] Acompanhe a execução no Prompt de Comando do aplicativo.\n")
    reporter.message(_MENSAGEM_STATUS)
    log(f"[DISM] Iniciado em {agora()}")

    try:
        rc = terminal.executar("DISM /Online /Cleanup-Image /RestoreHealth")
    except TerminalIndisponivelError as e:
        reporter.log(f"[ERRO] {e}\n", "erro")
        log(f"[DISM] TERMINAL INDISPONÍVEL - {e} - {agora()}")
        return

    reporter.log(f"[INFO] DISM concluído (código de retorno: {rc}).\n", "ok")
    log(f"[DISM] Concluído - codigo {rc} - {agora()}")