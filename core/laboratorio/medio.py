# ==========================================================
# Arquivo: core/laboratorio/medio.py
# Responsabilidade: Teste MÉDIO do Laboratório — simula uma tarefa de
# ~15s com progresso gradual, ideal para validar barra, tempo
# decorrido, navegação entre abas e o indicador de execução. Usa o
# mesmo CMD persistente do aplicativo, através do TerminalManager.
# ==========================================================

import time

from core.shared.terminal_manager import terminal


def teste_medio(reporter):
    """reporter: TaskReporter — mesma interface usada pelas tarefas
    reais (ver core/execution/reporter.py). Os comandos enviados ao
    CMD gerenciado (via terminal.executar) são apenas `echo`
    inofensivos — nenhum comando real do Windows é executado.

    Os `echo` reais no CMD são enviados apenas nos mesmos checkpoints
    já usados para o log interno (a cada 10 itens), e não em todo
    passo, para não alongar a duração do teste com o tempo real de
    ida e volta ao terminal."""
    reporter.log("[LAB] Teste médio iniciado (~15s)\n", "titulo")
    terminal.executar("echo Teste medio iniciado")

    passos = 30
    for i in range(1, passos + 1):
        time.sleep(0.5)
        reporter.progress((i / passos) * 100)
        reporter.message(f"Item {i}/{passos} processado")
        if i % 10 == 0:
            reporter.log(f"[INFO] Checkpoint: {i}/{passos} itens processados\n")
            terminal.executar(f"echo Checkpoint: {i}/{passos} itens processados")

    terminal.executar("echo Teste medio concluido")
    reporter.log("[SUCESSO] Teste médio concluído.\n", "ok")