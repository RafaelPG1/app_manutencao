# ==========================================================
# Arquivo: core/laboratorio/reinicializacao.py
# Responsabilidade: Teste de REINICIALIZAÇÃO do Laboratório — executa
# alguns segundos e finaliza sinalizando "reinicialização necessária"
# apenas como aviso de texto. NÃO reinicia o computador nem chama
# nenhuma API do sistema — serve só para validar a interface. Usa o
# mesmo CMD persistente do aplicativo, através do TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_reinicializacao(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Os comandos enviados ao
    CMD gerenciado (via terminal.executar) são apenas `echo`
    inofensivos — nenhum comando real do Windows é executado e nenhum
    reinício real ocorre."""
    reporter.log("[LAB] Teste de reinicialização iniciado\n", "titulo")
    terminal.executar("echo Teste de reinicializacao iniciado")

    passos = 8
    for i in range(1, passos + 1):
        time.sleep(0.3)
        reporter.progress((i / passos) * 100)
        reporter.message(f"Etapa {i}/{passos}")
        terminal.executar(f"echo Etapa {i}/{passos}")

    reporter.log("[SUCESSO] Teste de reinicialização concluído.\n", "ok")
    reporter.warning(
        "[AVISO] Reinicialização necessária. (simulado — nenhum reinício real ocorrerá)\n"
    )
    terminal.executar("echo AVISO: reinicializacao necessaria (simulado, nenhum reinicio real ocorrera)")