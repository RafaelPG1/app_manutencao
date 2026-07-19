# ==========================================================
# Arquivo: core/shared/comando_terminal.py
# Responsabilidade: Padrão comum para tarefas que executam UM ÚNICO
# comando no Prompt de Comando real e persistente do aplicativo (ver
# core/shared/terminal_manager.py) e apenas relatam início/término —
# sem interpretar a saída do comando, que já aparece nativamente no
# CMD (mesmo racional documentado em core/manutencao/dism.py e
# core/manutencao/sfc.py).
#
# HISTÓRICO: dism.py e sfc.py tinham essa mesma estrutura de log
# (mensagem de início, message() de status, try/except em torno de
# terminal.executar(), log de conclusão com o código de retorno)
# copiada uma na outra. Com a adição de novas tarefas de diagnóstico
# que também rodam um único comando no mesmo terminal (DISM
# /ScanHealth e /CheckHealth), essa duplicação deixaria de ser só
# entre 2 arquivos e passaria a ser entre 4 — por isso foi extraída
# para cá. Nenhum comportamento mudou: dism.py e sfc.py foram
# ajustados para usar esta função, mas continuam com a mesma
# assinatura pública (executar_dism(reporter), executar_sfc(reporter))
# e os mesmos textos de log de sempre.
# ==========================================================

from utils.helpers import agora
from utils.logger import log
from core.shared.terminal_manager import terminal, TerminalIndisponivelError


def executar_comando_no_terminal(
    reporter,
    *,
    comando: str,
    tag_log: str,
    mensagem_inicio: str,
    mensagem_status: str,
    mensagem_fim: str = None,
):
    """Executa `comando` no CMD gerenciado por terminal_manager e
    aplica o padrão comum de relato usado pelas tarefas que rodam num
    único comando visível (DISM, SFC e variações):

    - reporter.log() com o início (tag "titulo") e o lembrete de
      acompanhar no Prompt de Comando;
    - reporter.message(mensagem_status) como status estável durante
      toda a execução (a tarefa é sempre indeterminada aqui, pois não
      há captura de saída linha a linha — ver o cabeçalho de
      dism.py/sfc.py para o racional completo);
    - log interno (utils.logger.log) de início e término, com o
      código de retorno real do comando, marcado com `tag_log`
      (ex.: "DISM", "SFC");
    - tratamento de TerminalIndisponivelError, registrando o erro
      tanto no console da tarefa quanto no log interno, sem propagar
      a exceção (o lote continua para a próxima tarefa).

    Retorna o código de retorno real do comando (int), ou None se o
    terminal estava indisponível (erro já registrado nos dois logs).
    """
    reporter.log(f"[INFO] {mensagem_inicio}\n", "titulo")
    reporter.log("[INFO] Acompanhe a execução no Prompt de Comando do aplicativo.\n")
    reporter.message(mensagem_status)
    log(f"[{tag_log}] Iniciado em {agora()}")

    try:
        rc = terminal.executar(comando)
    except TerminalIndisponivelError as e:
        reporter.log(f"[ERRO] {e}\n", "erro")
        log(f"[{tag_log}] TERMINAL INDISPONÍVEL - {e} - {agora()}")
        return None

    texto_fim = mensagem_fim or f"{tag_log} concluído (código de retorno: {rc})."
    reporter.log(f"[INFO] {texto_fim}\n", "ok")
    log(f"[{tag_log}] Concluído - codigo {rc} - {agora()}")
    return rc
