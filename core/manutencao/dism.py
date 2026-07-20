# ==========================================================
# Arquivo: core/manutencao/dism.py
# Responsabilidade: Rotina de reparo da imagem do Windows via
# DISM (/Online /Cleanup-Image /RestoreHealth).
#
# O DISM roda no Prompt de Comando (cmd.exe) REAL, único e persistente
# do aplicativo, gerenciado exclusivamente por
# core/shared/terminal_manager.py — este módulo não sabe (nem precisa
# saber) como esse CMD é criado, mantido ou recriado; só chama
# terminal.executar() (através de core/shared/comando_terminal.py),
# que devolve o código de saída real do DISM somente depois que ele
# de fato terminou (nunca por suposição — ver o cabeçalho de
# terminal_manager.py).
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
# NOTA: a estrutura de log/relato (início, message() de status,
# tratamento de TerminalIndisponivelError, log de conclusão) é
# compartilhada com core/manutencao/sfc.py e com as novas tarefas de
# diagnóstico DISM (core/diagnostico/dism_diagnostico.py) através de
# core/shared/comando_terminal.py — só o comando e os textos mudam.
# A assinatura pública desta função (executar_dism(reporter)) e todo
# o texto exibido/logado permanecem exatamente os mesmos de antes.
# ==========================================================

from core.shared.comando_terminal import executar_comando_no_terminal

_MENSAGEM_STATUS = "Reparando a imagem do Windows... (acompanhe no Prompt de Comando aberto)"
_MENSAGEM_STATUS_CLEANUP = "Limpando componentes antigos do Windows... (acompanhe no Prompt de Comando aberto)"


def executar_dism(reporter):
    """reporter: TaskReporter (ver core/execution/reporter.py) — usado
    para log() de eventos de início/término e message() com um status
    estável.

    A barra de progresso da TAREFA fica no modo indeterminado (a UI
    decide isso sozinha a partir das capacidades declaradas para
    "dism"); a barra do LOTE é responsabilidade do ExecutionManager e
    não é tocada aqui — ela só avança quando esta função retorna.
    """
    executar_comando_no_terminal(
        reporter,
        comando="DISM /Online /Cleanup-Image /RestoreHealth",
        tag_log="DISM",
        mensagem_inicio="Iniciando reparo da imagem do Windows...",
        mensagem_status=_MENSAGEM_STATUS,
    )


def executar_dism_component_cleanup(reporter):
    """DISM /StartComponentCleanup (Fase 5) — remove versões antigas e
    superadas de componentes do Windows Update armazenadas no
    component store, liberando espaço em disco. Diferente de
    /RestoreHealth (que REPARA a imagem): esta operação apenas limpa
    componentes que o próprio Windows já sabe que não são mais
    necessários — segue o mesmo padrão de terminal visível e mesma
    ausência de interpretação do código de retorno."""
    executar_comando_no_terminal(
        reporter,
        comando="DISM /Online /Cleanup-Image /StartComponentCleanup",
        tag_log="DISM_CLEANUP",
        mensagem_inicio="Iniciando limpeza de componentes antigos do Windows (StartComponentCleanup)...",
        mensagem_status=_MENSAGEM_STATUS_CLEANUP,
    )