# ==========================================================
# Arquivo: core/laboratorio/indeterminado.py
# Responsabilidade: Teste de BARRA INDETERMINADA do Laboratório —
# nunca chama reporter.progress(), então a UI deve permanecer no modo
# indeterminado do início ao fim (decidido via capabilities, não por
# este módulo). Dura ~20s e finaliza com sucesso. Usa o mesmo CMD
# persistente do aplicativo, através do TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_indeterminado(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Nunca chama
    reporter.progress(); os comandos enviados ao CMD gerenciado (via
    terminal.executar) são apenas `echo` inofensivos — nenhum comando
    real do Windows é executado.

    Os `echo` reais no CMD são enviados a cada 5s (em vez de a cada
    1s, como a mensagem interna), para não alongar o teste com o
    tempo real de ida e volta ao terminal."""
    reporter.log("[LAB] Teste de barra indeterminada iniciado (~20s)\n", "titulo")
    terminal.executar("echo Teste de barra indeterminada iniciado")

    duracao = 20
    inicio = time.time()
    while time.time() - inicio < duracao:
        time.sleep(1)
        decorrido = int(time.time() - inicio)
        reporter.message(f"Trabalhando... {decorrido}s decorridos")
        if decorrido % 5 == 0:
            terminal.executar(f"echo Trabalhando... {decorrido}s decorridos")

    terminal.executar("echo Teste de barra indeterminada concluido")
    reporter.log("[SUCESSO] Teste de barra indeterminada concluído.\n", "ok")