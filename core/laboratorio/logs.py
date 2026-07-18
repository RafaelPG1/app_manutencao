# ==========================================================
# Arquivo: core/laboratorio/logs.py
# Responsabilidade: Teste de LOGS do Laboratório — gera centenas de
# linhas de log simuladas, para validar desempenho, scroll do console
# e comportamento de memória do painel de execução. Usa o mesmo CMD
# persistente do aplicativo, através do TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_muitos_logs(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). As 500 linhas de log
    continuam indo apenas para o painel interno (reporter.log), pois
    o propósito deste teste é o volume de log na UI — mandar 500
    comandos reais ao CMD gerenciado destruiria esse propósito
    (cada terminal.executar tem um custo real de ida e volta ao
    terminal). Por isso os comandos enviados ao CMD (via
    terminal.executar) são apenas `echo` inofensivos e enviados só em
    poucos marcos (início, a cada 100 arquivos e fim), só para provar
    que o mesmo terminal persistente também está sendo usado aqui."""
    reporter.log("[LAB] Teste de logs iniciado — gerando 500 linhas\n", "titulo")
    terminal.executar("echo Teste de logs iniciado")

    total = 500
    for i in range(1, total + 1):
        reporter.log(f"Arquivo {i:03d} processado\n")
        if i % 25 == 0:
            reporter.progress((i / total) * 100)
            reporter.message(f"{i}/{total} arquivos processados")
        if i % 100 == 0:
            terminal.executar(f"echo {i}/{total} arquivos processados")
        time.sleep(0.02)

    terminal.executar("echo Teste de logs concluido")
    reporter.progress(100)
    reporter.log("[SUCESSO] Teste de logs concluído.\n", "ok")