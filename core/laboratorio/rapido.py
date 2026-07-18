# ==========================================================
# Arquivo: core/laboratorio/rapido.py
# Responsabilidade: Teste RÁPIDO do Laboratório — simula uma tarefa
# curtíssima (~1s) que sobe de 0 a 100% quase instantaneamente e
# finaliza com sucesso. Usa a mesma interface (reporter) das tarefas
# reais e também o mesmo CMD persistente do aplicativo, através do
# TerminalManager — para validar a nova arquitetura de terminal antes
# de aplicá-la ao SFC/DISM.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_rapido(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Os comandos enviados ao
    CMD gerenciado (via terminal.executar) são apenas `echo`
    inofensivos — nenhum comando real do Windows é executado."""
    reporter.log("[LAB] Teste rápido iniciado\n", "titulo")
    terminal.executar("echo Teste rapido iniciado")

    passos = 10
    for i in range(1, passos + 1):
        time.sleep(0.1)
        reporter.progress((i / passos) * 100)
        reporter.message(f"Processando etapa {i}/{passos}")
        terminal.executar(f"echo Etapa {i}/{passos}")

    terminal.executar("echo Teste rapido concluido")
    reporter.log("[SUCESSO] Teste rápido concluído.\n", "ok")