# ==========================================================
# Arquivo: core/manutencao/sfc.py
# Responsabilidade: Rotina de verificação/reparo dos arquivos
# de sistema via SFC (/scannow).
#
# O SFC roda no Prompt de Comando (cmd.exe) REAL, único e persistente
# do aplicativo, gerenciado exclusivamente por
# core/shared/terminal_manager.py — este módulo não sabe (nem precisa
# saber) como esse CMD é criado, mantido ou recriado; só chama
# terminal.executar() (através de core/shared/comando_terminal.py),
# que devolve o código de saída real do SFC somente depois que ele de
# fato terminou (nunca por suposição — ver o cabeçalho de
# terminal_manager.py).
#
# Esse CMD é o console OFICIAL do aplicativo: toda a saída real do
# SFC (progresso, resultado, "nenhuma violação encontrada", "arquivos
# reparados" etc.) já aparece nativamente na tela dele. Por isso esta
# rotina NÃO interpreta o código de retorno do SFC — ela só registra
# que a execução terminou e qual foi esse código, para fins de log
# interno. Nenhuma mensagem baseada no valor de `rc` é exibida ao
# usuário aqui, para não duplicar (ou divergir d)o que o próprio
# Windows já mostrou no CMD.
#
# Como qualquer captura de saída exigiria redirecionar/alterar o que
# a tela mostra (o que contraria ter uma saída 100% nativa do
# Windows), esta tarefa não recebe texto linha a linha do SFC — só o
# código de saída real, ao final. Por isso ela é tratada como
# progresso INDETERMINADO (ver utils/tasks.py:
# sfc -> progresso_real=False), igual ao CHKDSK.
#
# NOTA: a estrutura de log/relato é compartilhada com
# core/manutencao/dism.py e com as novas tarefas de diagnóstico DISM
# através de core/shared/comando_terminal.py — ver o cabeçalho de
# dism.py para o histórico completo dessa extração. A assinatura
# pública desta função (executar_sfc(reporter)) e todo o texto
# exibido/logado permanecem exatamente os mesmos de antes.
# ==========================================================

from core.shared.comando_terminal import executar_comando_no_terminal

_MENSAGEM_STATUS = "Verificando arquivos do sistema... (acompanhe no Prompt de Comando aberto)"


def executar_sfc(reporter):
    """reporter: TaskReporter (ver core/execution/reporter.py) — usado
    para log() de eventos de início/término e message() com um status
    estável.

    A barra de progresso da TAREFA fica no modo indeterminado (a UI
    decide isso sozinha a partir das capacidades declaradas para
    "sfc"); a barra do LOTE é responsabilidade do ExecutionManager e
    não é tocada aqui — ela só avança quando esta função retorna.
    """
    executar_comando_no_terminal(
        reporter,
        comando="sfc /scannow",
        tag_log="SFC",
        mensagem_inicio="Iniciando verificação de integridade dos arquivos do sistema...",
        mensagem_status=_MENSAGEM_STATUS,
    )
